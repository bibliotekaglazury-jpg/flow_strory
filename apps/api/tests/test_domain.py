import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db import Account, Base, Generation, Ledger
from app.errors import DomainError
from app.services.credits import finish, grant, reserve


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(Account(user_id="alice", available=0, reserved=0))
        session.flush()
        yield session


def test_reservation_and_refund_are_idempotent(db):
    grant(db, "alice", 100, "grant:1")
    grant(db, "alice", 100, "grant:1")
    g = Generation(
        id="g",
        user_id="alice",
        estimated=36,
        charged=0,
        status="queued",
        snapshot={},
        request_hash="x",
        idempotency_key="k",
    )
    db.add(g)
    reserve(db, g)
    assert db.get(Account, "alice").available == 64
    finish(db, g, "failed", error={"code": "TEST", "message": "Failed", "retryable": False})
    finish(db, g, "failed")
    assert db.get(Account, "alice").available == 100
    assert db.get(Account, "alice").reserved == 0
    assert len(list(db.scalars(select(Ledger)))) == 3


def test_settlement_cannot_charge_cancelled_job(db):
    grant(db, "alice", 100, "grant")
    g = Generation(
        id="g",
        user_id="alice",
        estimated=36,
        charged=0,
        status="queued",
        snapshot={},
        request_hash="x",
        idempotency_key="k",
    )
    db.add(g)
    reserve(db, g)
    finish(db, g, "cancelled")
    finish(db, g, "completed", actual=36)
    assert g.status == "cancelled"
    assert g.charged == 0
    assert db.get(Account, "alice").available == 100


def test_insufficient_credits_does_not_reserve(db):
    g = Generation(
        id="g",
        user_id="alice",
        estimated=36,
        charged=0,
        status="queued",
        snapshot={},
        request_hash="x",
        idempotency_key="k",
    )
    with pytest.raises(DomainError, match="credits"):
        reserve(db, g)
    assert db.get(Account, "alice").reserved == 0
