import jwt
from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.config import settings
from app.db import Account, Ledger, User, session
from app.errors import DomainError
from app.services.credits import grant


def identity(authorization: str | None = Header(default=None), db=Depends(session)):
    cfg = settings()
    if cfg.auth_mode == "mock" and cfg.app_env == "development":
        subject = cfg.mock_user_id
    else:
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
            subject = claims["sub"]
        except (jwt.PyJWTError, ValueError):
            raise DomainError("UNAUTHENTICATED", "Session is invalid or expired.", 401) from None
    # Conflict-safe initialization: a concurrent first request cannot duplicate the development grant.
    db.execute(insert(User).values(id=subject, auth_subject=subject).on_conflict_do_nothing())
    db.execute(insert(Account).values(user_id=subject, available=0, reserved=0).on_conflict_do_nothing())
    if cfg.auth_mode == "mock" and not db.scalar(
        select(Ledger.id).where(Ledger.operation_key == f"development-grant:{subject}")
    ):
        grant(db, subject, cfg.mock_initial_credits, f"development-grant:{subject}")
    return subject
