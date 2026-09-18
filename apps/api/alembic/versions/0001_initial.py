"""Initial transactional generation schema, immutable migration definition."""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("auth_subject", sa.String, nullable=False, unique=True),
        sa.Column("email", sa.String),
    )
    op.create_table(
        "credit_accounts",
        sa.Column("user_id", sa.String, primary_key=True),
        sa.Column("available", sa.Integer, nullable=False),
        sa.Column("reserved", sa.Integer, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("available >= 0"),
        sa.CheckConstraint("reserved >= 0"),
    )
    op.create_table(
        "credit_transactions",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("user_id", sa.String, sa.ForeignKey("credit_accounts.user_id"), nullable=False),
        sa.Column("operation_key", sa.String, nullable=False, unique=True),
        sa.Column("kind", sa.String, nullable=False),
        sa.Column("available_delta", sa.Integer, nullable=False),
        sa.Column("reserved_delta", sa.Integer, nullable=False),
        sa.Column("generation_id", sa.String),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "assets",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("user_id", sa.String, nullable=False),
        sa.Column("role", sa.String, nullable=False),
        sa.Column("mime_type", sa.String, nullable=False),
        sa.Column("file_name", sa.String, nullable=False),
        sa.Column("size_bytes", sa.Integer, nullable=False),
        sa.Column("storage_key", sa.String, nullable=False, unique=True),
        sa.Column("width", sa.Integer),
        sa.Column("height", sa.Integer),
        sa.Column("duration_seconds", sa.Float),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_assets_user_id", "assets", ["user_id"])
    op.create_table(
        "prompts",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("user_id", sa.String, nullable=False),
        sa.Column("fingerprint", sa.String, nullable=False),
        sa.Column("snapshot", sa.JSON, nullable=False),
        sa.Column("text", sa.String, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_prompts_user_id", "prompts", ["user_id"])
    op.create_table(
        "credit_quotes",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("user_id", sa.String, nullable=False),
        sa.Column("fingerprint", sa.String, nullable=False),
        sa.Column("amount", sa.Integer, nullable=False),
        sa.Column("selected_model", sa.String, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted", sa.Boolean, nullable=False),
    )
    op.create_index("ix_credit_quotes_user_id", "credit_quotes", ["user_id"])
    op.create_table(
        "generations",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("user_id", sa.String, nullable=False),
        sa.Column("snapshot", sa.JSON, nullable=False),
        sa.Column("request_hash", sa.String, nullable=False),
        sa.Column("idempotency_key", sa.String, nullable=False),
        sa.Column("selected_model", sa.String, nullable=False),
        sa.Column("status", sa.String, nullable=False),
        sa.Column("progress", sa.Integer),
        sa.Column("estimated", sa.Integer, nullable=False),
        sa.Column("charged", sa.Integer, nullable=False),
        sa.Column("error", sa.JSON),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "idempotency_key"),
        sa.CheckConstraint("charged >= 0 AND charged <= estimated"),
    )
    op.create_index("ix_generations_user_id", "generations", ["user_id"])
    op.create_table(
        "generation_jobs",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("generation_id", sa.String, sa.ForeignKey("generations.id"), nullable=False, unique=True),
        sa.Column("provider_job_id", sa.String),
        sa.Column("submission_state", sa.String, nullable=False),
        sa.Column("lease_owner", sa.String),
        sa.Column("lease_until", sa.DateTime(timezone=True)),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer, nullable=False),
    )
    op.create_index("ix_runnable_jobs", "generation_jobs", ["submission_state", "next_run_at", "lease_until"])
    op.create_table(
        "generation_outputs",
        sa.Column("generation_id", sa.String, sa.ForeignKey("generations.id"), primary_key=True),
        sa.Column("asset_id", sa.String, sa.ForeignKey("assets.id"), primary_key=True),
    )
    op.create_table(
        "subscriptions",
        sa.Column("user_id", sa.String, primary_key=True),
        sa.Column("customer_id", sa.String, nullable=False, unique=True),
        sa.Column("stripe_subscription_id", sa.String, unique=True),
        sa.Column("plan", sa.String, nullable=False),
        sa.Column("status", sa.String, nullable=False),
        sa.Column("renewal_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "webhook_events",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("payload_hash", sa.String, nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
    )
    # Application services never mutate ledger history; PostgreSQL enforces this even for accidental ORM updates.
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            "CREATE FUNCTION reject_ledger_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'credit ledger is append-only'; END; $$"
        )
        op.execute(
            "CREATE TRIGGER immutable_credit_ledger BEFORE UPDATE OR DELETE ON credit_transactions FOR EACH ROW EXECUTE FUNCTION reject_ledger_mutation()"
        )


def downgrade():
    for table in [
        "webhook_events",
        "subscriptions",
        "generation_outputs",
        "generation_jobs",
        "generations",
        "credit_quotes",
        "prompts",
        "assets",
        "credit_transactions",
        "credit_accounts",
        "users",
    ]:
        op.drop_table(table)
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP FUNCTION reject_ledger_mutation()")
