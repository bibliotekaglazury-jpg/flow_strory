from sqlalchemy import select

from app.db import Account, Ledger, now
from app.errors import DomainError

TERMINAL = {"completed", "failed", "cancelled"}


def account(db, user_id):
    return db.scalar(select(Account).where(Account.user_id == user_id).with_for_update())


def change(db, user_id, available, reserved, key, kind, generation_id=None):
    a = account(db, user_id)
    if db.scalar(select(Ledger).where(Ledger.operation_key == key)):
        return
    if a.available + available < 0:
        raise DomainError("INSUFFICIENT_CREDITS", "Insufficient credits.", 409) from None
    if a.reserved + reserved < 0:
        raise RuntimeError("Reservation invariant violated")
    a.available += available
    a.reserved += reserved
    a.updated_at = now()
    db.add(
        Ledger(
            user_id=user_id,
            operation_key=key,
            kind=kind,
            available_delta=available,
            reserved_delta=reserved,
            generation_id=generation_id,
        )
    )
    db.flush()


def grant(db, user_id, amount, key):
    if amount < 0:
        raise ValueError("Invalid grant")
    change(db, user_id, amount, 0, key, "grant")


def reserve(db, g):
    change(db, g.user_id, -g.estimated, g.estimated, f"reserve:{g.id}", "generation_reserve", g.id)


def finish(db, g, status, actual=0, error=None):
    if g.status in TERMINAL:
        return
    if status not in TERMINAL or not 0 <= actual <= g.estimated:
        raise ValueError("Invalid settlement")
    if status != "completed":
        actual = 0
    change(
        db,
        g.user_id,
        g.estimated - actual,
        -g.estimated,
        f"finish:{g.id}",
        "generation_charge" if status == "completed" else "generation_refund",
        g.id,
    )
    g.status, g.charged, g.error, g.updated_at = status, actual, error, now()
    g.progress = 100 if status == "completed" else None
