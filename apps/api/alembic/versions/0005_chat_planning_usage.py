"""Durable planning expenditure, separate from generation credits."""

from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004_video_recipe"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("chat_sessions", sa.Column("planning_usage", sa.JSON, nullable=False, server_default="{}"))


def downgrade():
    op.drop_column("chat_sessions", "planning_usage")
