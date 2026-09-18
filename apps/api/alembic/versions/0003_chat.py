"""Owned local planning conversations; no credentials or raw model events."""

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("user_id", sa.String, nullable=False),
        sa.Column("provider", sa.String, nullable=False),
        sa.Column("provider_thread_id", sa.String, nullable=True),
        sa.Column("messages", sa.JSON, nullable=False),
        sa.Column("answer", sa.JSON, nullable=True),
        sa.Column("revision", sa.Integer, nullable=False),
        sa.Column("status", sa.String, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_chat_sessions_user_id", "chat_sessions", ["user_id"])


def downgrade():
    op.drop_table("chat_sessions")
