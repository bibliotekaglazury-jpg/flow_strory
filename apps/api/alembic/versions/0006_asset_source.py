"""Where an asset was uploaded, so a module can list only its own uploads."""

from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("assets", sa.Column("source", sa.String, nullable=True))


def downgrade():
    op.drop_column("assets", "source")
