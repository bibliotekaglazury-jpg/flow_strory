"""Subtitle Studio: editable timed-caption projects, immutable exports, durable jobs."""

from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "subtitle_projects",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("user_id", sa.String, nullable=False),
        sa.Column("source_asset_id", sa.String, nullable=False),
        sa.Column("status", sa.String, nullable=False),
        sa.Column("aspect_ratio", sa.String, nullable=False),
        sa.Column("language", sa.String, nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=False),
        sa.Column("revision", sa.Integer, nullable=False),
        sa.Column("cues", sa.JSON, nullable=False),
        sa.Column("style", sa.JSON, nullable=False),
        sa.Column("idempotency_key", sa.String, nullable=False),
        sa.Column("idempotency_hash", sa.String, nullable=False),
        sa.Column("error", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "idempotency_key"),
    )
    op.create_index("ix_subtitle_projects_user_id", "subtitle_projects", ["user_id"])
    op.create_table(
        "subtitle_exports",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column(
            "project_id",
            sa.String,
            sa.ForeignKey("subtitle_projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", sa.String, nullable=False),
        sa.Column("source_revision", sa.Integer, nullable=False),
        sa.Column("cues", sa.JSON, nullable=False),
        sa.Column("style", sa.JSON, nullable=False),
        sa.Column("aspect_ratio", sa.String, nullable=False),
        sa.Column("status", sa.String, nullable=False),
        sa.Column("progress", sa.Integer, nullable=True),
        sa.Column("output_asset_id", sa.String, nullable=True),
        sa.Column("idempotency_key", sa.String, nullable=False),
        sa.Column("idempotency_hash", sa.String, nullable=False),
        sa.Column("error", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "idempotency_key"),
    )
    op.create_index("ix_subtitle_exports_project_id", "subtitle_exports", ["project_id"])
    op.create_index("ix_subtitle_exports_user_id", "subtitle_exports", ["user_id"])
    op.create_table(
        "subtitle_jobs",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("kind", sa.String, nullable=False),
        sa.Column(
            "project_id", sa.String, sa.ForeignKey("subtitle_projects.id", ondelete="CASCADE")
        ),
        sa.Column(
            "export_id", sa.String, sa.ForeignKey("subtitle_exports.id", ondelete="CASCADE")
        ),
        sa.Column("submission_state", sa.String, nullable=False),
        sa.Column("lease_owner", sa.String, nullable=True),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer, nullable=False),
        sa.CheckConstraint(
            "(kind = 'transcribe' AND project_id IS NOT NULL AND export_id IS NULL) OR "
            "(kind = 'render' AND export_id IS NOT NULL AND project_id IS NULL)"
        ),
        sa.UniqueConstraint("kind", "project_id"),
        sa.UniqueConstraint("kind", "export_id"),
    )
    op.create_index(
        "ix_runnable_subtitle_jobs",
        "subtitle_jobs",
        ["submission_state", "next_run_at", "lease_until"],
    )


def downgrade():
    op.drop_table("subtitle_jobs")
    op.drop_table("subtitle_exports")
    op.drop_table("subtitle_projects")
