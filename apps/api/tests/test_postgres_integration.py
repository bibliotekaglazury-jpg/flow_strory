"""Run against a migrated isolated PostgreSQL database with RUN_POSTGRES_TESTS=1."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
import json
import hashlib
import hmac
import os
import time
from uuid import uuid4
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from app.config import settings
from app.db import SessionLocal, Job, Account, Subscription, Ledger, now
from app.main import app
from app.worker import process

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_TESTS") != "1", reason="Requires an explicitly configured isolated PostgreSQL DB"
)


@pytest.fixture
def client(monkeypatch):
    user = "integration-" + str(uuid4())
    monkeypatch.setenv("MOCK_USER_ID", user)
    monkeypatch.setenv("VIDEO_PROVIDER", "mock")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_integration")
    monkeypatch.setenv(
        "STRIPE_CATALOG_JSON",
        json.dumps({"test-plan": {"stripePriceId": "price_test", "credits": 70, "mode": "subscription"}}),
    )
    settings.cache_clear()
    with TestClient(app) as client:
        yield client, user
    settings.cache_clear()


def prepared(client):
    c, user = client
    data = BytesIO()
    Image.new("RGB", (16, 16), "blue").save(data, format="PNG")
    upload = c.post(
        "/api/assets", files={"file": ("product.png", data.getvalue(), "image/png")}, data={"role": "product"}
    )
    assert upload.status_code == 201, upload.text
    asset = upload.json()["asset"]
    creative = {
        "inputAssets": {"productImageId": asset["id"]},
        "templateId": "ugc_review",
        "brief": "Demonstrate this product honestly.",
        "duration": 15,
        "aspectRatio": "9:16",
    }
    prompt = c.post("/api/prompts/generate", json=creative)
    assert prompt.status_code == 200, prompt.text
    p = prompt.json()
    estimate = {k: v for k, v in creative.items() if k != "brief"} | {
        "promptId": p["promptId"],
        "model": "auto",
        "voice": "auto",
        "quality": "auto",
    }
    quote = c.get("/api/credits", params={"estimate": json.dumps(estimate)})
    assert quote.status_code == 200, quote.text
    body = creative | {
        "promptId": p["promptId"],
        "prompt": p["prompt"],
        "quoteId": quote.json()["quote"]["id"],
        "model": "auto",
        "voice": "auto",
        "quality": "auto",
    }
    return body


def test_api_worker_output_and_concurrent_idempotency(client):
    c, user = client
    body = prepared(client)

    def submit(_):
        return c.post("/api/generations", json=body, headers={"Idempotency-Key": "concurrent"})

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(submit, range(2)))
    assert [r.status_code for r in results] == [202, 202], [r.text for r in results]
    generation_id = results[0].json()["generation"]["id"]
    assert results[1].json()["generation"]["id"] == generation_id
    with SessionLocal.begin() as db:
        job = db.scalar(select(Job).where(Job.generation_id == generation_id).with_for_update())
        job.provider_job_id = f"simulation:{int(time.time()) - 20}:test"
        job.submission_state = "submitted"
        job.lease_owner = "test"
        job.lease_until = now()
        job_id = job.id
    asyncio.run(process(job_id, "test"))
    poll = c.get("/api/generations/" + generation_id)
    assert poll.status_code == 200, poll.text
    g = poll.json()["generation"]
    assert g["status"] == "completed", g
    assert poll.json()["pollAfterMs"] is None
    assert g["creditsCharged"] == 15
    assert g["outputAssets"][0]["durationSeconds"] == pytest.approx(15, abs=0.2)
    assert g["outputAssets"][0]["width"] == 360 and g["outputAssets"][0]["height"] == 640
    assert c.get("/api/generations").json()["generations"][0]["id"] == generation_id
    with SessionLocal.begin() as db:
        a = db.get(Account, user)
        assert a.available == 985 and a.reserved == 0
        operations = list(db.scalars(select(Ledger).where(Ledger.user_id == user)))
        assert sum(t.available_delta for t in operations) == a.available
        assert len(operations) == 3


def test_cancel_releases_and_signed_duplicate_invoice_grants_once(client):
    c, user = client
    body = prepared(client)
    accepted = c.post("/api/generations", json=body, headers={"Idempotency-Key": "cancel"})
    generation_id = accepted.json()["generation"]["id"]
    assert (
        c.post("/api/generations/" + generation_id + "/cancel", json={}).json()["generation"]["status"]
        == "cancelled"
    )
    assert c.post("/api/generations/" + generation_id + "/cancel", json={}).status_code == 200
    customer = "cus_" + str(uuid4())
    with SessionLocal.begin() as db:
        db.add(Subscription(user_id=user, customer_id=customer))
    event = {
        "id": "evt_" + str(uuid4()),
        "type": "invoice.paid",
        "data": {
            "object": {
                "id": "in_" + str(uuid4()),
                "customer": customer,
                "paid": True,
                "lines": {"data": [{"price": {"id": "price_test"}, "proration": False}]},
            }
        },
    }
    body = json.dumps(event).encode()
    timestamp = int(time.time())
    signature = hmac.new(
        b"whsec_integration", str(timestamp).encode() + b"." + body, hashlib.sha256
    ).hexdigest()
    for _ in range(2):
        response = c.post(
            "/api/webhooks/stripe",
            content=body,
            headers={"Stripe-Signature": f"t={timestamp},v1={signature}"},
        )
        assert response.status_code == 200, response.text
    assert c.get("/api/credits").json()["balance"] == 1070


def test_postgres_ledger_rejects_mutation(client):
    c, user = client
    c.get("/api/credits")
    from sqlalchemy.exc import DBAPIError

    with pytest.raises(DBAPIError):
        with SessionLocal.begin() as db:
            db.execute(
                text("UPDATE credit_transactions SET available_delta=99999 WHERE user_id=:id"), {"id": user}
            )


def test_concurrent_first_checkout_creates_one_customer_mapping(client, monkeypatch):
    from types import SimpleNamespace
    from app.services import billing

    c, user = client
    c.get("/api/credits")
    created = []

    def customer_create(params, options):
        created.append(options["idempotency_key"])
        return SimpleNamespace(id="cus_concurrent_" + user)

    sdk = SimpleNamespace(
        v1=SimpleNamespace(
            customers=SimpleNamespace(create=customer_create),
            checkout=SimpleNamespace(
                sessions=SimpleNamespace(
                    create=lambda params: SimpleNamespace(
                        id="cs_test",
                        url="https://checkout.stripe.com/test",
                        expires_at=int(time.time()) + 1000,
                    )
                )
            ),
        )
    )
    monkeypatch.setattr(billing, "client", lambda: sdk)

    def checkout(_):
        return c.post("/api/billing/checkout", json={"priceId": "test-plan"})

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(checkout, range(2)))
    assert [r.status_code for r in results] == [201, 201], [r.text for r in results]
    assert len(created) == 1
    with SessionLocal.begin() as db:
        assert db.get(Subscription, user).customer_id == "cus_concurrent_" + user


@pytest.mark.parametrize("definitive_failure", [True, False])
def test_worker_failure_refunds_but_unknown_poll_retains_reservation(client, monkeypatch, definitive_failure):
    from dataclasses import replace
    from app import worker
    from app.providers import ProviderError, ProviderResult
    from app.providers.mock import MockVideoProvider

    c, user = client
    body = prepared(client)
    accepted = c.post("/api/generations", json=body, headers={"Idempotency-Key": "failure"})
    generation_id = accepted.json()["generation"]["id"]

    class FailingProvider(MockVideoProvider):
        async def get_status(self, job_id):
            if definitive_failure:
                return ProviderResult(
                    "failed", error=ProviderError("GENERATION_FAILED", "Generation failed.")
                )
            raise ProviderError("GENERATION_STATUS_UNAVAILABLE", "Status unavailable.", retryable=True)

        async def generate(self, request, idempotency_key):
            raise AssertionError("Polling must not recreate remote work")

    selected = replace(worker.registry()[0], provider=FailingProvider())
    monkeypatch.setattr(worker, "registry", lambda: (selected,))
    with SessionLocal.begin() as db:
        job = db.scalar(select(Job).where(Job.generation_id == generation_id).with_for_update())
        job.provider_job_id = "known-remote"
        job.submission_state = "submitted"
        job.lease_owner = "test-failure"
        job_id = job.id
    asyncio.run(process(job_id, "test-failure"))
    g = c.get("/api/generations/" + generation_id).json()["generation"]
    assert g["status"] == ("failed" if definitive_failure else "generating")
    with SessionLocal.begin() as db:
        account = db.get(Account, user)
        assert account.available == (1000 if definitive_failure else 985)
        assert account.reserved == (0 if definitive_failure else 15)


def test_remotion_real_worker_storage_and_history(client):
    from app.db import Generation
    from app.services.templates import records, input_types

    c, user = client
    available = [
        t
        for t in records()
        if t["templateType"] == "remotion" and t["enabled"] and input_types(t) == {"text-only"}
    ]
    assert available, "An enabled compiled Remotion manifest is required"
    template = available[0]
    inputs = {
        k: v.get("default", "A real local template render")
        for k, v in template["inputSchema"].get("properties", {}).items()
        if k in template["inputSchema"].get("required", [])
    }
    request = dict(
        templateId=template["id"], duration=15, aspectRatio="9:16", inputAssets={}, normalizedInputs=inputs
    )
    q = c.get("/api/credits", params={"estimate": json.dumps(request)})
    assert q.status_code == 200, q.text
    quote = q.json()["quote"]
    body = request | {"quoteId": quote["id"]}
    response = c.post("/api/generations", json=body, headers={"Idempotency-Key": "real-remotion"})
    assert response.status_code == 202, response.text
    generation_id = response.json()["generation"]["id"]
    with SessionLocal.begin() as db:
        assert db.get(Generation, generation_id).selected_model == "render_only"
        job = db.scalar(select(Job).where(Job.generation_id == generation_id).with_for_update())
        job.lease_owner = "real-remotion-test"
        job.lease_until = now()
        job_id = job.id
    asyncio.run(process(job_id, "real-remotion-test"))
    result = c.get("/api/generations/" + generation_id).json()["generation"]
    assert result["status"] == "completed", result
    output = next(a for a in result["outputAssets"] if a["role"] == "output_video")
    assert output["mimeType"] == "video/mp4" and output["durationSeconds"] == pytest.approx(15, abs=0.2)
    assert output["width"] > 0 and output["height"] > output["width"]
    assert any(a["role"] == "thumbnail" for a in result["outputAssets"])
    assert c.get(output["url"]).status_code == 200
    assert c.get("/api/generations").json()["generations"][0]["id"] == generation_id
    with SessionLocal.begin() as db:
        account = db.get(Account, user)
        assert account.reserved == 0 and account.available == 1000 - quote["creditsEstimated"]
        rows = list(db.scalars(select(Ledger).where(Ledger.generation_id == generation_id)))
        assert len(rows) == 2 and sum(r.reserved_delta for r in rows) == 0


@pytest.mark.parametrize("outcome", ["failed", "cancelled", "stale-owner", "changed-definition"])
def test_render_worker_failure_cancel_and_stale_owner(client, monkeypatch, outcome):
    from app.services import templates, rendering
    from app.db import Output

    c, user = client
    spec = dict(
        id="rve_race_test",
        name="Test",
        templateType="remotion",
        enabled=True,
        supportedDurations=[15],
        supportedAspectRatios=["9:16"],
        inputSchema={"properties": {}, "required": []},
    )
    monkeypatch.setattr(templates, "records", lambda: [spec])
    request = dict(templateId=spec["id"], duration=15, aspectRatio="9:16", inputAssets={})
    q = c.get("/api/credits", params={"estimate": json.dumps(request)})
    assert q.status_code == 200, q.text
    response = c.post(
        "/api/generations",
        json=request | {"quoteId": q.json()["quote"]["id"]},
        headers={"Idempotency-Key": "race"},
    )
    assert response.status_code == 202, response.text
    generation_id = response.json()["generation"]["id"]
    with SessionLocal.begin() as db:
        job = db.scalar(select(Job).where(Job.generation_id == generation_id).with_for_update())
        job.lease_owner = "race-owner"
        job_id = job.id

    async def render(snapshot, assets, storage):
        if outcome == "failed":
            raise TimeoutError("Bounded renderer failure")
        if outcome == "cancelled":
            response = c.post("/api/generations/" + generation_id + "/cancel", json={})
            assert response.status_code == 200, response.text
        else:
            with SessionLocal.begin() as db:
                job = db.get(Job, job_id)
                job.lease_owner = "replacement-owner"
        # Invalid bytes deliberately prove terminal/lease checks happen before storage/validation.
        return b"late output", b"late thumbnail"

    monkeypatch.setattr(rendering, "render", render)
    if outcome == "changed-definition":
        spec["version"] = "changed-after-admission"
        spec["inputSchema"] = {"properties": {"newRequired": {"type": "string"}}, "required": ["newRequired"]}
    asyncio.run(process(job_id, "race-owner"))
    result = c.get("/api/generations/" + generation_id).json()["generation"]
    assert result["status"] == (
        "generating" if outcome == "stale-owner" else "failed" if outcome == "changed-definition" else outcome
    )
    assert result["outputAssets"] == [] and result["creditsCharged"] == 0
    assert c.get("/api/generations").status_code == 200
    with SessionLocal.begin() as db:
        account = db.get(Account, user)
        assert account.reserved == (15 if outcome == "stale-owner" else 0)
        assert not list(db.scalars(select(Output).where(Output.generation_id == generation_id)))
    if outcome == "stale-owner":
        assert c.post("/api/generations/" + generation_id + "/cancel", json={}).status_code == 200


def test_director_to_existing_worker_storage_ledger_history(client, monkeypatch):
    from app.services import chat
    from app.providers.chat import MockChatProvider
    from app.db import Generation

    monkeypatch.setattr(chat, "provider", lambda: MockChatProvider())
    c, user = client
    original = prepared(client)
    s = c.post("/api/chat/sessions").json()
    response = c.post(
        f"/api/chat/sessions/{s['id']}/messages",
        json={
            "text": "Zrób naturalny UGC kremu po polsku",
            "context": {
                "templateId": "auto",
                "inputAssets": original["inputAssets"],
                "duration": 15,
                "aspectRatio": "9:16",
            },
        },
    )
    assert response.status_code == 200, response.text
    answer = response.json()
    assert answer["answer"]["creativePlan"]["spokenLanguage"] == "pl"
    applied = c.post(
        f"/api/chat/sessions/{s['id']}/apply",
        json={
            "revision": answer["revision"],
            "creative": {
                "templateId": "auto",
                "inputAssets": original["inputAssets"],
                "duration": 15,
                "aspectRatio": "9:16",
                "brief": "Krem",
            },
        },
    )
    assert applied.status_code == 200, applied.text
    data = applied.json()
    creative = data["creative"]
    estimate = {k: v for k, v in creative.items() if k not in ("brief", "language")}
    estimate.update(promptId=data["prompt"]["promptId"], model="auto", voice="auto", quality="auto")
    quote = c.get("/api/credits", params={"estimate": json.dumps(estimate)})
    assert quote.status_code == 200, quote.text
    body = {
        **creative,
        "promptId": data["prompt"]["promptId"],
        "prompt": data["prompt"]["prompt"],
        "model": "auto",
        "voice": "auto",
        "quality": "auto",
        "quoteId": quote.json()["quote"]["id"],
    }
    submitted = c.post("/api/generations", json=body, headers={"Idempotency-Key": "director-pipeline"})
    assert submitted.status_code == 202, submitted.text
    gid = submitted.json()["generation"]["id"]

    # Lease this specific test job only; never claim another user's queued work.
    def lease():
        with SessionLocal.begin() as db:
            job = db.scalar(select(Job).where(Job.generation_id == gid).with_for_update())
            job.lease_owner = "director-test"
            job.lease_until = now()
            return job.id

    asyncio.run(process(lease(), "director-test"))
    assert c.get("/api/generations/" + gid).json()["generation"]["status"] == "generating"
    with SessionLocal.begin() as db:
        job = db.scalar(select(Job).where(Job.generation_id == gid))
        job.provider_job_id = f"simulation:{int(time.time()) - 20}:test"
    asyncio.run(process(lease(), "director-test"))
    result = c.get("/api/generations/" + gid).json()["generation"]
    assert result["status"] == "completed", result
    assert result["outputAssets"][0]["durationSeconds"] == pytest.approx(15, abs=0.2)
    assert c.get("/api/generations").json()["generations"][0]["id"] == gid
    with SessionLocal() as db:
        g = db.get(Generation, gid)
        assert g.snapshot["creativePlanning"]["videoPlan"]["clips"][0]["end"] == 15
        assert g.snapshot["videoRecipe"]["spokenContent"]["language"] == "pl"
        assert g.snapshot["providerRequestMetadata"]["duration"] == 15
        assert db.get(Account, user).reserved == 0
        assert g.charged == g.estimated


def test_subtitle_export_real_render_storage_and_poll(client):
    """Mock transcription, real Remotion render of the registered SubtitleStudio composition."""
    from pathlib import Path

    from app.subtitles import jobs
    from app.subtitles.providers import MockTranscriptionProvider

    c, _ = client
    sample = Path(__file__).resolve().parents[2] / "web/public/media/create-preview.mp4"
    upload = c.post(
        "/api/assets",
        files={"file": ("clip.mp4", sample.read_bytes(), "video/mp4")},
        data={"role": "source_video"},
    )
    assert upload.status_code == 201, upload.text
    created = c.post(
        "/api/subtitle-projects",
        json={"sourceAssetId": upload.json()["asset"]["id"], "aspectRatio": "9:16"},
        headers={"Idempotency-Key": "real-subtitles"},
    )
    assert created.status_code == 202, created.text
    project_id = created.json()["project"]["id"]
    provider = MockTranscriptionProvider()
    assert asyncio.run(jobs.run_next("real-subtitle-test", provider))
    ready = c.get(f"/api/subtitle-projects/{project_id}").json()["project"]
    assert ready["status"] == "ready" and ready["cues"], ready
    queued = c.post(
        f"/api/subtitle-projects/{project_id}/exports",
        json={"revision": ready["revision"]},
        headers={"Idempotency-Key": "real-subtitles-export"},
    )
    assert queued.status_code == 202, queued.text
    export_id = queued.json()["export"]["id"]
    assert asyncio.run(jobs.run_next("real-subtitle-test", provider))
    polled = c.get(f"/api/subtitle-projects/{project_id}/exports/{export_id}").json()
    assert polled["export"]["status"] == "completed", polled
    assert polled["pollAfterMs"] is None
    output = polled["export"]["outputAsset"]
    assert output["mimeType"] == "video/mp4" and output["height"] > output["width"]
    assert c.get(output["url"]).status_code == 200


def test_try_on_concurrent_same_key_calls_the_provider_once(client, monkeypatch):
    """The account row lock in try_on.preview() serializes same-user requests, so a
    genuine concurrent double-submit with the same idempotencyKey never reaches the paid
    provider twice - only the DB-level unique constraint was proven before this fix.

    Driven directly through try_on.preview() with two independent sessions via
    asyncio.gather, not TestClient + threads: two OS threads sharing one TestClient's
    internal event-loop portal serialize in ways that don't reflect two real concurrent
    HTTP requests (verified separately - it isn't an app-level deadlock, just an artifact
    of that specific harness), so it can't tell real request-level concurrency apart from
    a single blocked thread. Real concurrent request handling in production runs each
    request with its own session on the shared engine's connection pool, which is what
    this reproduces.
    """
    from app.db import SessionLocal
    from app.schemas import TryOn
    from app.services import try_on

    monkeypatch.setenv("IMAGE_PROVIDER", "mock")
    monkeypatch.setenv("IMAGE_CREDITS_PER_GENERATION", "5")
    settings.cache_clear()
    c, user = client
    person = Image.new("RGB", (16, 16), "blue")
    product = Image.new("RGB", (16, 16), "red")
    person_data, product_data = BytesIO(), BytesIO()
    person.save(person_data, format="PNG")
    product.save(product_data, format="PNG")
    person_asset = c.post(
        "/api/assets",
        files={"file": ("model.png", person_data.getvalue(), "image/png")},
        data={"role": "person"},
    ).json()["asset"]
    product_asset = c.post(
        "/api/assets",
        files={"file": ("shirt.png", product_data.getvalue(), "image/png")},
        data={"role": "product"},
    ).json()["asset"]
    body = TryOn(
        inputAssets={"productImageId": product_asset["id"], "personImageId": person_asset["id"]},
        aspectRatio="9:16",
        idempotencyKey="concurrent-preview",
    )

    async def submit():
        with SessionLocal() as db, db.begin():
            return await try_on.preview(db, user, body)

    async def run_both():
        return await asyncio.gather(submit(), submit())

    results = asyncio.run(run_both())
    asset_ids = {r["asset"]["id"] for r in results}
    assert len(asset_ids) == 1
    # Only one of the two calls actually paid the provider; the other returned the cached result.
    assert sorted(r["creditsCharged"] for r in results) == [0, 5]
