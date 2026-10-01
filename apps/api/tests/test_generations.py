import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.db import Account, Base, Generation, Job, Ledger, Prompt
from app.errors import DomainError
from app.providers import ProviderError
from app.schemas import CreateGeneration, Creative, Estimate
from app.services.credits import grant
from app.services.generations import cancel, create, delete, owned_generation, quote
from app.services.prompts import fingerprint


@pytest.fixture
def setup(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("VIDEO_PROVIDER", "mock")
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Account(user_id="alice", available=0, reserved=0))
        db.flush()
        grant(db, "alice", 1000, "grant")
        creative = Creative(
            productUrl="https://example.com",
            inputAssets={},
            templateId="ugc_review",
            brief="Show product",
            duration=15,
            aspectRatio="9:16",
        )
        p = Prompt(
            user_id="alice",
            snapshot=creative.model_dump(),
            fingerprint=fingerprint(creative.model_dump()),
            text="Show the product honestly.",
        )
        db.add(p)
        db.flush()
        estimate = Estimate(**{k: v for k, v in creative.model_dump().items() if k in Estimate.model_fields}, promptId=p.id)
        q = quote(db, "alice", estimate)
        body = CreateGeneration(**creative.model_dump(), promptId=p.id, prompt=p.text, quoteId=q.id)
        yield db, body, q


def test_same_request_key_returns_job_once_and_changed_body_conflicts(setup):
    db, body, q = setup
    first = create(db, "alice", body, "key")
    again = create(db, "alice", body, "key")
    assert first.id == again.id
    assert db.get(Account, "alice").reserved == q.amount
    with pytest.raises(DomainError) as error:
        create(db, "alice", body.model_copy(update={"prompt": "Changed"}), "key")
    assert error.value.code == "IDEMPOTENCY_CONFLICT"


def test_job_ownership_and_cancel_refund(setup):
    db, body, q = setup
    g = create(db, "alice", body, "key")
    with pytest.raises(DomainError):
        owned_generation(db, "bob", g.id)
    cancel(db, "alice", g.id)
    cancel(db, "alice", g.id)
    assert g.status == "cancelled"
    assert db.get(Account, "alice").available == 1000


def test_cannot_cancel_remote_submission(setup):
    db, body, q = setup
    g = create(db, "alice", body, "key")
    job = db.scalar(select(Job).where(Job.generation_id == g.id))
    job.submission_state = "intent"
    db.flush()
    with pytest.raises(DomainError) as error:
        cancel(db, "alice", g.id)
    assert error.value.code == "CANCELLATION_UNAVAILABLE"
    assert g.status == "queued"


def test_changed_estimate_is_rejected_before_reserving(setup):
    db, body, q = setup
    body = body.model_copy(update={"quality": "720p"})
    with pytest.raises(ProviderError):
        create(db, "alice", body, "key")
    assert db.get(Account, "alice").reserved == 0


def test_an_in_progress_generation_cannot_be_deleted(setup):
    db, body, q = setup
    g = create(db, "alice", body, "key")
    with pytest.raises(DomainError) as error:
        delete(db, "alice", g.id)
    assert error.value.code == "DELETE_UNAVAILABLE"


def test_deleting_a_finished_generation_removes_it_but_keeps_the_charge(setup):
    db, body, q = setup
    g = create(db, "alice", body, "key")
    cancel(db, "alice", g.id)  # a terminal status, without needing a real render
    generation_id = g.id
    charged_balance = db.get(Account, "alice").available

    delete(db, "alice", generation_id)

    assert db.scalar(select(func.count()).select_from(Generation)) == 0
    assert db.scalar(select(func.count()).select_from(Job)) == 0
    with pytest.raises(DomainError):
        owned_generation(db, "alice", generation_id)
    # Deleting the library entry does not refund what was already spent producing it.
    assert db.get(Account, "alice").available == charged_balance


def test_bob_cannot_delete_alices_generation(setup):
    db, body, q = setup
    g = create(db, "alice", body, "key")
    cancel(db, "alice", g.id)
    with pytest.raises(DomainError):
        delete(db, "bob", g.id)
    assert owned_generation(db, "alice", g.id).id == g.id



def test_a_karma_service_start_records_its_reservation_and_reserves_no_ugc_credits(setup):
    db, body, q = setup
    before = db.get(Account, "alice").available
    g = create(db, "alice", body, "karma-key", reservation="hold-1")
    assert g.estimated == 0
    assert db.get(Account, "alice").reserved == 0
    assert db.get(Account, "alice").available == before
    claim = db.scalar(select(Ledger).where(Ledger.kind == "karma_reservation"))
    assert claim.generation_id == g.id and claim.available_delta == 0 and claim.reserved_delta == 0
    # A retry with the same request key is the same start, not a second use of the hold.
    assert create(db, "alice", body, "karma-key", reservation="hold-1").id == g.id
    # Cancelling refunds nothing in UGC: Karma releases its own hold.
    cancel(db, "alice", g.id)
    assert db.get(Account, "alice").available == before


def test_one_karma_reservation_never_pays_for_two_starts(setup):
    db, body, q = setup
    create(db, "alice", body, "karma-key", reservation="hold-1")
    fresh = quote(db, "alice", Estimate(**{k: v for k, v in body.model_dump().items() if k in Estimate.model_fields}))
    with pytest.raises(DomainError) as error:
        create(db, "alice", body.model_copy(update={"quoteId": fresh.id}), "another-key", reservation="hold-1")
    assert error.value.code == "RESERVATION_ALREADY_USED"
