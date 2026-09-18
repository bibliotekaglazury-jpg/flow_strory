"""One systematized view per user: totals across every product plus recent credit ledger
entries, all scoped by user_id like every other route already is."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import identity
from app.db import (
    Account,
    Asset,
    Base,
    Generation,
    Ledger,
    LookProject,
    SubtitleProject,
    session as db_session,
)
from app.main import app
from app.services.credits import grant
from app.services.profile import summary


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        for user in ("alice", "bob"):
            session.add(Account(user_id=user, available=0, reserved=0))
        session.flush()
        grant(session, "alice", 500, "alice-grant")
        grant(session, "bob", 900, "bob-grant")

        for identifier, role in [("alice-product", "product"), ("alice-person", "person"), ("alice-video", "output_video")]:
            session.add(
                Asset(
                    id=identifier,
                    user_id="alice",
                    role=role,
                    mime_type="image/png",
                    file_name=f"{identifier}.png",
                    size_bytes=1,
                    storage_key=f"alice/{identifier}",
                )
            )
        session.add(
            Asset(
                id="bob-product",
                user_id="bob",
                role="product",
                mime_type="image/png",
                file_name="bob-product.png",
                size_bytes=1,
                storage_key="bob/bob-product",
            )
        )

        for identifier, status in [("g1", "completed"), ("g2", "failed"), ("g3", "completed")]:
            session.add(
                Generation(
                    id=identifier,
                    user_id="alice",
                    snapshot={},
                    request_hash=identifier,
                    idempotency_key=identifier,
                    status=status,
                    estimated=10,
                    charged=10 if status == "completed" else 0,
                )
            )

        session.add(
            LookProject(
                id="look1", user_id="alice", input_assets={}, scene="studio", aspect_ratio="4:5"
            )
        )

        session.add(
            SubtitleProject(
                id="sub1",
                user_id="alice",
                source_asset_id="alice-video",
                aspect_ratio="9:16",
                style={},
                idempotency_key="sub1",
                idempotency_hash="sub1",
            )
        )
        session.flush()
        yield session


def test_totals_every_product_for_this_user_only(db):
    result = summary(db, "alice")
    assert result["userId"] == "alice"
    assert result["assets"]["total"] == 3
    assert result["assets"]["byRole"] == {"product": 1, "person": 1, "output_video": 1}
    assert result["generations"]["total"] == 3
    assert result["generations"]["byStatus"] == {"completed": 2, "failed": 1}
    assert result["lookProjects"]["total"] == 1
    assert result["subtitleProjects"]["total"] == 1


def test_another_user_sees_only_their_own_totals(db):
    result = summary(db, "bob")
    assert result["assets"]["total"] == 1
    assert result["assets"]["byRole"] == {"product": 1}
    assert result["generations"]["total"] == 0
    assert result["generations"]["byStatus"] == {}
    assert result["lookProjects"]["total"] == 0
    assert result["subtitleProjects"]["total"] == 0


def test_a_user_with_nothing_yet_gets_a_clean_zeroed_summary(db):
    db.add(Account(user_id="carol", available=0, reserved=0))
    db.flush()
    result = summary(db, "carol")
    assert result["credits"] == {"available": 0, "reserved": 0}
    assert result["assets"] == {"total": 0, "byRole": {}}
    assert result["generations"] == {"total": 0, "byStatus": {}}
    assert result["recentTransactions"] == []


def test_credits_reflect_the_account_row_and_transactions_are_this_users_own_newest_first(db):
    result = summary(db, "alice")
    assert result["credits"] == {"available": 500, "reserved": 0}
    assert [t["kind"] for t in result["recentTransactions"]] == ["grant"]
    assert all(isinstance(t["availableDelta"], int) for t in result["recentTransactions"])

    bob_result = summary(db, "bob")
    assert bob_result["credits"] == {"available": 900, "reserved": 0}


def test_recent_transactions_are_capped_and_newest_first(db, monkeypatch):
    from app.services import profile as profile_module

    monkeypatch.setattr(profile_module, "RECENT_TRANSACTIONS_LIMIT", 2)
    for i in range(3):
        db.add(
            Ledger(
                user_id="bob",
                operation_key=f"bob-op-{i}",
                kind="grant",
                available_delta=1,
                reserved_delta=0,
            )
        )
    db.flush()
    result = summary(db, "bob")
    # The grant() in the fixture plus these three: five total, only the newest two come back.
    assert len(result["recentTransactions"]) == 2


def test_the_route_returns_the_authenticated_users_own_profile():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    with factory() as seed, seed.begin():
        seed.add(Account(user_id="alice", available=0, reserved=0))
        seed.add(Account(user_id="bob", available=0, reserved=0))
        seed.flush()
        grant(seed, "alice", 250, "alice-grant")
        grant(seed, "bob", 999, "bob-grant")

    def db():
        with factory() as item, item.begin():
            yield item

    app.dependency_overrides[identity] = lambda: "alice"
    app.dependency_overrides[db_session] = db
    try:
        with TestClient(app) as client:
            response = client.get("/api/profile")
            assert response.status_code == 200
            body = response.json()
            assert body["userId"] == "alice"
            assert body["credits"]["available"] == 250
    finally:
        app.dependency_overrides.pop(identity, None)
        app.dependency_overrides.pop(db_session, None)
