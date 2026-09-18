"""Persist validated recipe revisions and applied generation recipes."""

from alembic import op
import sqlalchemy as sa

revision = "0004_video_recipe"
down_revision = "0003"
branch_labels = depends_on = None


def upgrade():
    op.add_column("prompts", sa.Column("recipe", sa.JSON(), nullable=True))
    op.create_table(
        "chat_recipe_versions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "session_id", sa.String(), sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("recipe", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("session_id", "revision"),
    )
    op.create_index("ix_chat_recipe_versions_session_id", "chat_recipe_versions", ["session_id"])


def downgrade():
    op.drop_table("chat_recipe_versions")
    op.drop_column("prompts", "recipe")
