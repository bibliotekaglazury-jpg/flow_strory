"""Karma service mode: Karma reserves the allowance before forwarding a paid start, so UGC
records which reservation paid for it and never debits its own credits for that subject.

Every record is a zero-delta ledger row keyed by subject and reservation, so no schema change
is needed. The claim row is `karma-reservation:<subject>:<reservation>`; markers append a
`#` suffix, which a reservation id cannot contain, so one reservation can never forge
another's marker.
"""

import re

from sqlalchemy import select

from app.db import Generation, Ledger
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


def _key(user_id, reservation):
    return f"karma-reservation:{user_id}:{reservation}"


def _marker(db, user_id, key, kind, generation_id=None):
    db.add(
        Ledger(
            user_id=user_id,
            operation_key=key,
            kind=kind,
            available_delta=0,
            reserved_delta=0,
            generation_id=generation_id,
        )
    )
    db.flush()


def claim(db, user_id, reservation, generation_id=None):
    """One reservation pays for exactly one start. A zero-delta ledger row records it, so
    the subject's history shows what each Karma reservation was spent on."""
    key = _key(user_id, reservation)
    if db.scalar(select(Ledger.id).where(Ledger.operation_key == key)):
        raise DomainError(
            "RESERVATION_ALREADY_USED", "This reservation has already started a generation.", 409
        ) from None
    _marker(db, user_id, key, "karma_reservation", generation_id)


def photo_result(db, user_id, reservation, asset_id):
    """Links a service try-on's reservation to the photo it produced (same transaction)."""
    _marker(db, user_id, f"{_key(user_id, reservation)}#asset:{asset_id}", "karma_reservation_result")


def photo_failed(db, user_id, reservation):
    """A service try-on whose provider call failed: nothing was delivered for the reservation."""
    _marker(db, user_id, f"{_key(user_id, reservation)}#failed", "karma_reservation_failed")


def generation_deleted(db, g):
    """Keeps the outcome of a reservation-paid video after its library entry is deleted, so
    reconciliation still reads succeeded/failed instead of losing the record."""
    claimed = db.scalar(
        select(Ledger.id).where(
            Ledger.user_id == g.user_id, Ledger.generation_id == g.id, Ledger.kind == "karma_reservation"
        )
    )
    if claimed:
        outcome = "succeeded" if g.status == "completed" else "failed"
        _marker(db, g.user_id, f"karma-generation:{g.id}#{outcome}", f"karma_reservation_{outcome}", g.id)


def foreign(db, user_id, reservation):
    """True when another subject claimed this reservation id; such an id is refused (404)
    instead of being reported as unknown to the wrong workspace."""
    keys = db.scalars(
        select(Ledger.operation_key).where(
            Ledger.kind == "karma_reservation",
            Ledger.user_id != user_id,
            Ledger.operation_key.endswith(f":{reservation}", autoescape=True),
        )
    )
    return any(key == f"karma-reservation:{key.split(':')[1]}:{reservation}" for key in keys)


GENERATION_STATUS = {"completed": "succeeded", "failed": "failed", "cancelled": "failed"}


def status(db, user_id, reservation):
    """Read-only reconciliation view of one reservation for this subject.

    unknown: UGC has no record (never seen, or a try-on that has not committed yet).
    pending: seen, its job not finished. succeeded / failed: final. Another subject's
    reservation is a 404.
    """
    unknown = {"status": "unknown", "kind": None}
    if not RESERVATION.match(reservation or ""):
        return unknown
    key = _key(user_id, reservation)
    row = db.scalar(select(Ledger).where(Ledger.user_id == user_id, Ledger.operation_key == key))
    if not row:
        if foreign(db, user_id, reservation):
            raise DomainError("NOT_FOUND", "Reservation is unavailable.", 404) from None
        return unknown
    if row.generation_id:
        g = db.scalar(
            select(Generation).where(Generation.id == row.generation_id, Generation.user_id == user_id)
        )
        result = {"generationId": row.generation_id}
        if g:
            return {"status": GENERATION_STATUS.get(g.status, "pending"), "kind": "video", "result": result}
        kept = db.scalar(
            select(Ledger.kind).where(
                Ledger.user_id == user_id,
                Ledger.generation_id == row.generation_id,
                Ledger.kind.in_(["karma_reservation_succeeded", "karma_reservation_failed"]),
            )
        )
        outcome = "succeeded" if kept == "karma_reservation_succeeded" else "failed" if kept else "unknown"
        return {"status": outcome, "kind": "video", "result": result}
    markers = list(
        db.scalars(
            select(Ledger.operation_key).where(
                Ledger.user_id == user_id, Ledger.operation_key.startswith(f"{key}#", autoescape=True)
            )
        )
    )
    if f"{key}#failed" in markers:
        return {"status": "failed", "kind": "photo"}
    prefix = f"{key}#asset:"
    for marker in markers:
        if marker.startswith(prefix):
            # Deleting the photo later does not undo the delivery Karma paid for.
            return {"status": "succeeded", "kind": "photo", "result": {"assetId": marker[len(prefix) :]}}
    return {"status": "pending", "kind": "photo"}
