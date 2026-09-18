from datetime import timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base, Generation, Job, now
from app.worker import claim


def test_expired_lease_recovers_without_redis():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(
            Generation(
                id="g",
                user_id="alice",
                snapshot={},
                request_hash="x",
                idempotency_key="k",
                estimated=1,
                charged=0,
                status="queued",
            )
        )
        job = Job(
            generation_id="g",
            submission_state="submitted",
            provider_job_id="remote",
            lease_owner="dead-worker",
            lease_until=now() - timedelta(seconds=1),
            next_run_at=now() - timedelta(seconds=1),
        )
        db.add(job)
        db.flush()
        assert claim(db, "new-worker") == job.id
        assert job.provider_job_id == "remote"
        assert job.lease_owner == "new-worker"
        assert claim(db, "other-worker") is None
