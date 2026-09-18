from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from app.config import settings


def now():
    return datetime.now(UTC)


def uid():
    return str(uuid4())


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    auth_subject: Mapped[str] = mapped_column(String, unique=True)
    email: Mapped[str | None]


class Account(Base):
    __tablename__ = "credit_accounts"
    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    available: Mapped[int] = mapped_column(Integer, default=0)
    reserved: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (CheckConstraint("available >= 0"), CheckConstraint("reserved >= 0"))


class Ledger(Base):
    __tablename__ = "credit_transactions"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("credit_accounts.user_id"))
    operation_key: Mapped[str] = mapped_column(String, unique=True)
    kind: Mapped[str]
    available_delta: Mapped[int]
    reserved_delta: Mapped[int]
    generation_id: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Asset(Base):
    __tablename__ = "assets"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(String, index=True)
    role: Mapped[str]
    mime_type: Mapped[str]
    file_name: Mapped[str]
    size_bytes: Mapped[int]
    storage_key: Mapped[str] = mapped_column(String, unique=True)
    width: Mapped[int | None]
    height: Mapped[int | None]
    duration_seconds: Mapped[float | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    # Module the upload came from ("try_on"); null for everything uploaded elsewhere.
    source: Mapped[str | None] = mapped_column(String, nullable=True)


class Prompt(Base):
    __tablename__ = "prompts"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(String, index=True)
    fingerprint: Mapped[str]
    snapshot: Mapped[dict] = mapped_column(JSON)
    text: Mapped[str]
    recipe: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(String, index=True)
    provider: Mapped[str]
    provider_thread_id: Mapped[str | None]
    messages: Mapped[list] = mapped_column(JSON, default=list)
    answer: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    planning_usage: Mapped[dict] = mapped_column(JSON, default=dict)
    revision: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(default="idle")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ChatRecipeVersion(Base):
    __tablename__ = "chat_recipe_versions"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    session_id: Mapped[str] = mapped_column(ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True)
    revision: Mapped[int]
    recipe: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (UniqueConstraint("session_id", "revision"),)


class Quote(Base):
    __tablename__ = "credit_quotes"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(String, index=True)
    fingerprint: Mapped[str]
    amount: Mapped[int]
    selected_model: Mapped[str]
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    accepted: Mapped[bool] = mapped_column(default=False)


class Generation(Base):
    __tablename__ = "generations"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(String, index=True)
    snapshot: Mapped[dict] = mapped_column(JSON)
    request_hash: Mapped[str]
    idempotency_key: Mapped[str]
    selected_model: Mapped[str] = mapped_column(default="mock-video")
    status: Mapped[str] = mapped_column(default="queued")
    progress: Mapped[int | None]
    estimated: Mapped[int]
    charged: Mapped[int] = mapped_column(default=0)
    error: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key"),
        CheckConstraint("charged >= 0 AND charged <= estimated"),
    )


class Job(Base):
    __tablename__ = "generation_jobs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    generation_id: Mapped[str] = mapped_column(ForeignKey("generations.id"), unique=True)
    provider_job_id: Mapped[str | None]
    submission_state: Mapped[str] = mapped_column(default="pending")
    lease_owner: Mapped[str | None]
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    attempts: Mapped[int] = mapped_column(default=0)
    __table_args__ = (Index("ix_runnable_jobs", "submission_state", "next_run_at", "lease_until"),)


class Output(Base):
    __tablename__ = "generation_outputs"
    generation_id: Mapped[str] = mapped_column(ForeignKey("generations.id"), primary_key=True)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), primary_key=True)


class Subscription(Base):
    __tablename__ = "subscriptions"
    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    customer_id: Mapped[str] = mapped_column(String, unique=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String, unique=True)
    plan: Mapped[str] = mapped_column(default="free")
    status: Mapped[str] = mapped_column(default="inactive")
    renewal_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    payload_hash: Mapped[str]
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


engine = create_engine(settings().database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def session():
    with SessionLocal() as db, db.begin():
        yield db


class LookProject(Base):
    """One try-on generation: the model, products and settings its photos were shot with."""

    __tablename__ = "look_projects"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(String, index=True)
    input_assets: Mapped[dict] = mapped_column(JSON)
    scene: Mapped[str]
    aspect_ratio: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class LookPhoto(Base):
    __tablename__ = "look_photos"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("look_projects.id", ondelete="CASCADE"), index=True
    )
    asset_id: Mapped[str]
    label: Mapped[str]
    # Explicit order: shots of one set land within milliseconds of each other.
    position: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SubtitleProject(Base):
    """One editable timed-caption project: source video, transcript, style and revision."""

    __tablename__ = "subtitle_projects"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(String, index=True)
    source_asset_id: Mapped[str]
    status: Mapped[str] = mapped_column(default="transcribing")
    aspect_ratio: Mapped[str]
    language: Mapped[str | None]
    duration_ms: Mapped[int] = mapped_column(default=0)
    revision: Mapped[int] = mapped_column(default=0)
    cues: Mapped[list] = mapped_column(JSON, default=list)
    style: Mapped[dict] = mapped_column(JSON)
    idempotency_key: Mapped[str]
    idempotency_hash: Mapped[str]
    error: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (UniqueConstraint("user_id", "idempotency_key"),)


class SubtitleExport(Base):
    """An immutable snapshot of one project revision, rendered to an output asset."""

    __tablename__ = "subtitle_exports"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("subtitle_projects.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(String, index=True)
    source_revision: Mapped[int]
    # Frozen at creation: later edits to the live project must never change this export.
    cues: Mapped[list] = mapped_column(JSON)
    style: Mapped[dict] = mapped_column(JSON)
    aspect_ratio: Mapped[str]
    status: Mapped[str] = mapped_column(default="queued")
    progress: Mapped[int | None]
    output_asset_id: Mapped[str | None]
    idempotency_key: Mapped[str]
    idempotency_hash: Mapped[str]
    error: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # A share link is opt-in and revocable: the token exists only once the user asks to
    # share, and share_revoked_at makes revocation permanent rather than reusable.
    share_token: Mapped[str | None] = mapped_column(String, nullable=True, index=True, unique=True)
    share_revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (UniqueConstraint("user_id", "idempotency_key"),)


class SubtitleJob(Base):
    """Durable transcribe/render work, leased the same way as generation_jobs.

    kind picks which owning row is set: transcribe -> project_id, render -> export_id.
    Postgres and SQLite both treat NULL as distinct in a unique constraint, so the two
    columns can share one table without a job of one kind colliding with the other.
    """

    __tablename__ = "subtitle_jobs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    kind: Mapped[str]
    project_id: Mapped[str | None] = mapped_column(
        ForeignKey("subtitle_projects.id", ondelete="CASCADE")
    )
    export_id: Mapped[str | None] = mapped_column(
        ForeignKey("subtitle_exports.id", ondelete="CASCADE")
    )
    submission_state: Mapped[str] = mapped_column(default="pending")
    lease_owner: Mapped[str | None]
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    attempts: Mapped[int] = mapped_column(default=0)
    __table_args__ = (
        CheckConstraint(
            "(kind = 'transcribe' AND project_id IS NOT NULL AND export_id IS NULL) OR "
            "(kind = 'render' AND export_id IS NOT NULL AND project_id IS NULL)"
        ),
        UniqueConstraint("kind", "project_id"),
        UniqueConstraint("kind", "export_id"),
        Index("ix_runnable_subtitle_jobs", "submission_state", "next_run_at", "lease_until"),
    )


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class TemplateRecord(Base):
    __tablename__ = "templates"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str]
    description: Mapped[str]
    version: Mapped[int] = mapped_column(default=1)
    instructions: Mapped[str]
    scene_beats: Mapped[list] = mapped_column(JSON, default=list)
    capabilities: Mapped[dict] = mapped_column(JSON, default=dict)
    enabled: Mapped[bool] = mapped_column(default=True)


class ProviderRecord(Base):
    __tablename__ = "providers"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    enabled: Mapped[bool] = mapped_column(default=False)
    configuration: Mapped[dict] = mapped_column(JSON, default=dict)


class ModelRecord(Base):
    __tablename__ = "models"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    provider_id: Mapped[str] = mapped_column(ForeignKey("providers.id"))
    vendor_model_id: Mapped[str]
    media_type: Mapped[str] = mapped_column(default="video")
    capabilities: Mapped[dict] = mapped_column(JSON, default=dict)
    enabled: Mapped[bool] = mapped_column(default=False)
    priority: Mapped[int] = mapped_column(default=10)
    cost_rules: Mapped[dict] = mapped_column(JSON, default=dict)
