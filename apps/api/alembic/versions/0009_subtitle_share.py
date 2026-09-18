"""Subtitle Studio: revocable public share links on an export."""

from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("subtitle_exports", sa.Column("share_token", sa.String, nullable=True))
    op.add_column(
        "subtitle_exports", sa.Column("share_revoked_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index(
        "ix_subtitle_exports_share_token", "subtitle_exports", ["share_token"], unique=True
    )


def downgrade():
    op.drop_index("ix_subtitle_exports_share_token", table_name="subtitle_exports")
    op.drop_column("subtitle_exports", "share_revoked_at")
    op.drop_column("subtitle_exports", "share_token")
