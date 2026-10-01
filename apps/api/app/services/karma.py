"""Karma service mode: Karma reserves the allowance before forwarding a paid start, so UGC
records which reservation paid for it and never debits its own credits for that subject."""

import re

from sqlalchemy import select

from app.db import Ledger
from app.errors import DomainError

RESERVATION = re.compile(r"^[A-Za-z0-9_.:-]{1,200}$")


def required_reservation(service, reservation):
    """None for an ordinary user; for a service request, the validated X-Karma-Reservation."""
    if not service:
        return None
    if not reservation or not RESERVATION.match(reservation):
        raise DomainError(
            "RESERVATION_REQUIRED", "A paid start from Karma must carry its reservation.", 403
        ) from None
    return reservation


def claim(db, user_id, reservation, generation_id=None):
    """One reservation pays for exactly one start. A zero-delta ledger row records it, so
    the subject's history shows what each Karma reservation was spent on."""
    key = f"karma-reservation:{user_id}:{reservation}"
    if db.scalar(select(Ledger.id).where(Ledger.operation_key == key)):
        raise DomainError(
            "RESERVATION_ALREADY_USED", "This reservation has already started a generation.", 409
        ) from None
    db.add(
        Ledger(
            user_id=user_id,
            operation_key=key,
            kind="karma_reservation",
            available_delta=0,
            reserved_delta=0,
            generation_id=generation_id,
        )
    )
    db.flush()
