"""Actual director adapter and generation services with injected offline provider transport."""

from pathlib import Path
import shutil

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import sessionmaker

from app import config, worker
from app.chat_api import ApplyRecipe, ChatContext, SendMessage
from app.config import Settings
from app.db import Account, Asset, Base, ChatSession, Generation, Job, Ledger, Output, Prompt, now
from app.providers.claude import ClaudeCreativeDirectorAdapter
from app.providers.mock import MockVideoProvider
from app.providers.registry import RegisteredModel
from app.schemas import Creative, CreateGeneration, Estimate
from app.services import chat, generations
from app.services.credits import grant
from app.services.storage import Storage
from test_claude_adapter import Client, preparation, response
from test_creative_audit import payload as audit_payload


@pytest.mark.asyncio
@pytest.mark.parametrize("ratio", ["9:16", "1:1", "16:9"])
async def test_director_apply_quote_mock_generation_history_and_ledger(tmp_path, monkeypatch, ratio):
    cfg = Settings(
        claude_skip_preparation_without_url=False,
        _env_file=None,
        anthropic_api_key="offline-fixture",
        storage_path=str(tmp_path),
        storage_mode="local",
        video_provider="mock",
    )
    probe = shutil.which("ffprobe")
    if not probe:
        binaries = sorted(
            Path(__file__)
            .resolve()
            .parents[3]
            .glob("node_modules/.pnpm/@remotion+compositor-*/node_modules/@remotion/compositor-*/ffprobe")
        )
        if not binaries:
            pytest.skip("A local ffprobe is required to verify stored video media")
        probe = str(binaries[0])
        monkeypatch.setenv("DYLD_LIBRARY_PATH", str(binaries[0].parent))
    cfg.ffprobe_path = probe
    monkeypatch.setattr(config, "settings", lambda: cfg)
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(chat, "SessionLocal", factory)
    monkeypatch.setattr(worker, "SessionLocal", factory)
    monkeypatch.setattr(chat, "settings", lambda: cfg)
    storage = Storage(cfg)
    monkeypatch.setattr(worker, "Storage", lambda: storage)
    monkeypatch.setattr(generations, "Storage", lambda: storage)
    registry = (RegisteredModel("offline-video", "Offline simulation", MockVideoProvider()),)
    monkeypatch.setattr(worker, "registry", lambda: registry)
    monkeypatch.setattr(generations, "registry", lambda: registry)
    envelope = audit_payload.__wrapped__()
    envelope["answer"]["videoPlan"]["aspectRatio"] = ratio
    adapter = ClaudeCreativeDirectorAdapter(cfg, client=Client([response(preparation()), response(envelope)]))
    monkeypatch.setattr(chat, "provider", lambda: adapter)
    with factory.begin() as db:
        db.add(Account(user_id="alice", available=0, reserved=0))
        db.flush()
        grant(db, "alice", 100, "initial-offline-grant")
    session = await chat.create("alice")
    planned = await chat.send(
        "alice",
        session["id"],
        SendMessage(
            text="Show how the first language lesson helps someone start speaking.",
            context=ChatContext(
                templateId="product_demo",
                inputAssets={},
                duration=15,
                aspectRatio=ratio,
                brief="Language lessons for adult beginners.",
            ),
        ),
    )
    applied = chat.apply(
        "alice",
        session["id"],
        ApplyRecipe(
            revision=planned["revision"],
            creative=Creative(
                templateId="product_demo",
                inputAssets={},
                brief="Language lessons",
                duration=15,
                aspectRatio=ratio,
            ),
        ),
    )
    with factory.begin() as db:
        # Planning expenditure is independent of video-credit transactions.
        assert db.get(Account, "alice").available == 100
        assert len(list(db.scalars(select(Ledger)))) == 1
        assert db.get(ChatSession, session["id"]).planning_usage["spentCents"] > 0
        prompt = db.get(Prompt, applied["prompt"]["promptId"])
        assert prompt.snapshot["creativePlanning"]["creativeAudit"]["creative"]["selectedId"] == "c0"
        estimate = Estimate.model_validate(
            {
                **{k: v for k, v in applied["creative"].items() if k in Estimate.model_fields},
                "promptId": prompt.id,
            }
        )
        quoted = generations.quote(db, "alice", estimate)
        request = CreateGeneration(
            **applied["creative"], promptId=prompt.id, prompt=prompt.text, quoteId=quoted.id
        )
        generated = generations.create(db, "alice", request, "offline-workflow")
        generation_id = generated.id
        assert generations.create(db, "alice", request, "offline-workflow").id == generation_id
        assert quoted.amount == 15 and db.get(Account, "alice").reserved == 15
        job_id = worker.claim(db, "fixture-worker")
    await worker.process(job_id, "fixture-worker")
    with factory.begin() as db:
        job = db.get(Job, job_id)
        assert job.submission_state == "submitted"
        job.provider_job_id = "simulation:0:offline-fixture"
        job.lease_owner = "fixture-worker"
    await worker.process(job_id, "fixture-worker")
    with factory.begin() as db:
        completed = db.get(Generation, generation_id)
        assert completed.status == "completed"
        assert completed.snapshot["videoRecipe"]["aspectRatio"] == ratio
        assert completed.snapshot["providerRequestMetadata"]["aspectRatio"] == ratio
        assert completed.charged == completed.estimated == 15
        assert db.get(Account, "alice").available == 85
        assert db.get(Account, "alice").reserved == 0
        assert len(list(db.scalars(select(Ledger)))) == 3
        output = db.scalar(select(Asset).join(Output, Asset.id == Output.asset_id))
        assert storage.path(output.storage_key).is_file()
        assert output.duration_seconds == pytest.approx(15, abs=0.1)
        width, height = map(int, ratio.split(":"))
        assert output.width / output.height == pytest.approx(width / height, rel=0.02)
        history = generations.history(db, "alice", 10, None)
        assert history["generations"][0]["outputAssets"][0]["id"] == output.id
        assert history["generations"][0]["aspectRatio"] == ratio
        assert generations.history(db, "bob", 10, None)["generations"] == []
        # Replaying a completed job never settles twice.
        db.get(Job, job_id).lease_owner = "fixture-worker"
    await worker.process(job_id, "fixture-worker")
    with factory() as db:
        assert len(list(db.scalars(select(Ledger)))) == 3
        assert len(list(db.scalars(select(Output)))) == 1


def test_planning_usage_migration_upgrade_downgrade_reupgrade_isolated(tmp_path, monkeypatch):
    database = tmp_path / "migration-test.sqlite"
    cfg = Settings(_env_file=None, database_url=f"sqlite:///{database}")
    monkeypatch.setattr(config, "settings", lambda: cfg)
    alembic = Config()
    alembic.set_main_option("script_location", str(Path(__file__).resolve().parents[1] / "alembic"))
    command.upgrade(alembic, "0004_video_recipe")
    engine = create_engine(cfg.database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO chat_sessions (id,user_id,provider,messages,revision,status,created_at,updated_at) VALUES ('existing','alice','mock','[]',0,'idle',:stamp,:stamp)"
            ),
            {"stamp": now().isoformat()},
        )
    # Pinned to 0005 rather than head, so later migrations do not change what this checks.
    command.upgrade(alembic, "0005")
    assert "planning_usage" in {column["name"] for column in inspect(engine).get_columns("chat_sessions")}
    with engine.connect() as connection:
        assert (
            connection.execute(text("SELECT planning_usage FROM chat_sessions WHERE id='existing'")).scalar()
            == "{}"
        )
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar() == "0005"
    command.downgrade(alembic, "0004_video_recipe")
    assert "planning_usage" not in {column["name"] for column in inspect(engine).get_columns("chat_sessions")}
    command.upgrade(alembic, "0005")
    with engine.connect() as connection:
        assert (
            connection.execute(text("SELECT planning_usage FROM chat_sessions WHERE id='existing'")).scalar()
            == "{}"
        )
    engine.dispose()


def test_try_on_migrations_upgrade_downgrade_reupgrade_isolated(tmp_path, monkeypatch):
    database = tmp_path / "try-on-migration.sqlite"
    cfg = Settings(_env_file=None, database_url=f"sqlite:///{database}")
    monkeypatch.setattr(config, "settings", lambda: cfg)
    alembic = Config()
    alembic.set_main_option("script_location", str(Path(__file__).resolve().parents[1] / "alembic"))
    command.upgrade(alembic, "head")
    engine = create_engine(cfg.database_url)
    assert {"look_projects", "look_photos"} <= set(inspect(engine).get_table_names())
    assert "source" in {column["name"] for column in inspect(engine).get_columns("assets")}
    command.downgrade(alembic, "0005")
    assert not {"look_projects", "look_photos"} & set(inspect(engine).get_table_names())
    assert "source" not in {column["name"] for column in inspect(engine).get_columns("assets")}
    command.upgrade(alembic, "head")
    assert {"look_projects", "look_photos"} <= set(inspect(engine).get_table_names())
    engine.dispose()
