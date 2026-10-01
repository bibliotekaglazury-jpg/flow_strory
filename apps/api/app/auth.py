import hmac
import re

import jwt
from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.config import settings
from app.db import Account, Ledger, User, session
from app.errors import DomainError
from app.services.credits import grant

# A Karma workspace subject is a UUIDv5 (src/lib/studio/subject.ts in Karma). Supabase user
# ids are UUIDv4, so requiring version 5 keeps the two subject spaces disjoint.
KARMA_SUBJECT = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-5[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


def is_service(request: Request) -> bool:
    """True only when identity() admitted this request with the Karma service credential."""
    return bool(getattr(request.state, "karma_service", False))


def service_subject(authorization, subject):
    """The Karma subject when the bearer is the configured service token, else None.

    Service mode is off while KARMA_SERVICE_TOKEN is unset; X-Karma-Subject is then ignored
    and the request takes the ordinary Supabase path.
    """
    token = settings().karma_service_token.get_secret_value()
    if not token or not authorization or not authorization.startswith("Bearer "):
        return None
    if not hmac.compare_digest(authorization[7:].encode(), token.encode()):
        return None
    if not subject or not KARMA_SUBJECT.match(subject):
        raise DomainError("UNAUTHENTICATED", "Service request is missing a valid subject.", 401) from None
    return subject


def user_subject(cfg, authorization):
    """The ordinary end-user path: the development mock user or a verified Supabase JWT."""
    if cfg.auth_mode == "mock" and cfg.app_env == "development":
        return cfg.mock_user_id
    if not authorization or not authorization.startswith("Bearer "):
        raise DomainError("UNAUTHENTICATED", "Sign in to continue.", 401) from None
    token = authorization[7:]
    try:
        issuer = cfg.supabase_url.rstrip("/") + "/auth/v1"
        key = jwt.PyJWKClient(
            issuer + "/.well-known/jwks.json", cache_keys=True
        ).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            key.key,
            algorithms=["ES256", "RS256"],
            audience=cfg.supabase_jwt_audience,
            issuer=issuer,
            options={"require": ["exp", "sub", "iss", "aud"]},
        )
        return claims["sub"]
    except (jwt.PyJWTError, ValueError):
        raise DomainError("UNAUTHENTICATED", "Session is invalid or expired.", 401) from None


def identity(
    request: Request,
    authorization: str | None = Header(default=None),
    x_karma_subject: str | None = Header(default=None),
    db=Depends(session),
):
    cfg = settings()
    subject = service_subject(authorization, x_karma_subject)
    service = subject is not None
    if not service:
        subject = user_subject(cfg, authorization)
    request.state.karma_service = service
    # Conflict-safe initialization: a concurrent first request cannot duplicate the development grant.
    db.execute(insert(User).values(id=subject, auth_subject=subject).on_conflict_do_nothing())
    db.execute(insert(Account).values(user_id=subject, available=0, reserved=0).on_conflict_do_nothing())
    # Karma keeps the allowance for its workspaces; a service subject never gets UGC credits.
    if (
        not service
        and cfg.auth_mode == "mock"
        and not db.scalar(select(Ledger.id).where(Ledger.operation_key == f"development-grant:{subject}"))
    ):
        grant(db, subject, cfg.mock_initial_credits, f"development-grant:{subject}")
    return subject
