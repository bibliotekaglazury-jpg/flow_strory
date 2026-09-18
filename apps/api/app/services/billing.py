import hashlib
import json
from datetime import UTC, datetime, timedelta

import stripe
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.config import settings
from app.db import Subscription, WebhookEvent, now
from app.errors import DomainError
from app.services.credits import account, grant


def catalog():
    data = json.loads(settings().stripe_catalog_json)
    for entry in data.values():
        if (
            not isinstance(entry.get("credits"), int)
            or entry["credits"] < 0
            or not str(entry.get("stripePriceId", "")).startswith("price_")
        ):
            raise DomainError("BILLING_UNAVAILABLE", "Billing catalog is not configured.", 503) from None
    return data


def client():
    if not settings().stripe_secret_key:
        raise DomainError("BILLING_UNAVAILABLE", "Billing is not configured.", 503) from None
    return stripe.StripeClient(settings().stripe_secret_key)


def checkout(db, user_id, price_id):
    entry = catalog().get(price_id)
    if not entry:
        raise DomainError("INVALID_PRICE", "Plan is unavailable.", 422) from None
    sdk = client()
    # Serialize first customer creation before reading the mapping, so a waiter sees the committed row.
    account(db, user_id)
    sub = db.get(Subscription, user_id)
    if not sub:
        customer = sdk.v1.customers.create(
            {"metadata": {"user_id": user_id}}, options={"idempotency_key": f"customer:{user_id}"}
        )
        sub = Subscription(user_id=user_id, customer_id=customer.id)
        db.add(sub)
        db.flush()
    result = sdk.v1.checkout.sessions.create(
        {
            "customer": sub.customer_id,
            "mode": entry.get("mode", "payment"),
            "line_items": [{"price": entry["stripePriceId"], "quantity": 1}],
            "success_url": settings().frontend_origin + "/billing?checkout=success",
            "cancel_url": settings().frontend_origin + "/billing",
            "client_reference_id": user_id,
            "metadata": {"catalog_id": price_id, "user_id": user_id},
        }
    )
    return {
        "sessionId": result.id,
        "checkoutUrl": result.url,
        "expiresAt": datetime.fromtimestamp(result.expires_at, UTC).isoformat(),
    }


def portal(db, user_id):
    sub = db.get(Subscription, user_id)
    if not sub:
        raise DomainError("BILLING_CUSTOMER_UNAVAILABLE", "No billing customer exists yet.", 409) from None
    result = client().v1.billing_portal.sessions.create(
        {"customer": sub.customer_id, "return_url": settings().frontend_origin + "/billing"}
    )
    return {"portalUrl": result.url, "expiresAt": (now() + timedelta(minutes=5)).isoformat()}


def verify_event(body, signature):
    secret = settings().stripe_webhook_secret
    if not secret:
        raise DomainError("BILLING_UNAVAILABLE", "Webhook is not configured.", 503) from None
    try:
        return stripe.Webhook.construct_event(body, signature or "", secret)
    except (ValueError, stripe.SignatureVerificationError):
        raise DomainError("INVALID_SIGNATURE", "Webhook signature is invalid.", 400) from None


def apply_event(db, event, body):
    inserted = db.execute(
        insert(WebhookEvent)
        .values(id=event["id"], payload_hash=hashlib.sha256(body).hexdigest())
        .on_conflict_do_nothing()
        .returning(WebhookEvent.id)
    ).scalar_one_or_none()
    if inserted is None:
        return
    obj = event["data"]["object"]
    kind = event["type"]
    customer_id = obj.get("customer")
    sub = (
        db.scalar(select(Subscription).where(Subscription.customer_id == customer_id).with_for_update())
        if customer_id
        else None
    )
    if (
        kind in {"checkout.session.completed", "checkout.session.async_payment_succeeded"}
        and obj.get("payment_status") == "paid"
        and obj.get("mode") == "payment"
    ):
        if not sub:
            raise DomainError(
                "BILLING_MAPPING_UNAVAILABLE", "Customer mapping unavailable.", 503, True
            ) from None
        public_id = obj.get("metadata", {}).get("catalog_id")
        entry = catalog().get(public_id)
        if not entry or obj.get("metadata", {}).get("user_id") != sub.user_id:
            raise DomainError(
                "BILLING_MAPPING_UNAVAILABLE", "Payment mapping unavailable.", 503, True
            ) from None
        # Fetch Stripe's line items: signed metadata alone does not prove which price was paid.
        lines = client().v1.checkout.sessions.line_items.list(obj["id"], {"limit": 100})
        if (
            len(lines.data) != 1
            or lines.data[0].price.id != entry["stripePriceId"]
            or lines.data[0].quantity != 1
        ):
            raise DomainError("BILLING_MAPPING_UNAVAILABLE", "Payment price mismatch.", 503) from None
        grant(db, sub.user_id, entry["credits"], f"stripe-checkout:{obj['id']}")
    elif kind == "invoice.paid":
        if not sub:
            raise DomainError(
                "BILLING_MAPPING_UNAVAILABLE", "Customer mapping unavailable.", 503, True
            ) from None
        # Only a single configured recurring price is granted; ambiguous/prorated invoices need review.
        lines = obj.get("lines", {}).get("data", [])
        if len(lines) != 1 or lines[0].get("proration"):
            return
        price_id = (lines[0].get("price") or {}).get("id") or (lines[0].get("pricing") or {}).get(
            "price_details", {}
        ).get("price")
        selected = next(
            (
                (k, v)
                for k, v in catalog().items()
                if v["stripePriceId"] == price_id and v.get("mode") == "subscription"
            ),
            None,
        )
        if selected and obj.get("paid"):
            grant(db, sub.user_id, selected[1]["credits"], f"stripe-invoice:{obj['id']}")
            sub.plan = selected[0]
    elif (
        kind
        in {"customer.subscription.created", "customer.subscription.updated", "customer.subscription.deleted"}
        and sub
    ):
        sub.stripe_subscription_id = obj["id"]
        sub.status = obj["status"]
        expiry = obj.get("current_period_end")
        sub.renewal_at = datetime.fromtimestamp(expiry, UTC) if expiry else None
