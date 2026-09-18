"""Assets: optional idempotency key for retry-safe paid provider calls (try-on preview)."""

from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade():
    # Batch mode: SQLite cannot ALTER TABLE to add a constraint directly, only Postgres can;
    # batch mode does a copy-and-move on SQLite and a plain ALTER TABLE on Postgres.
    with op.batch_alter_table("assets") as batch_op:
        batch_op.add_column(sa.Column("idempotency_key", sa.String, nullable=True))
        batch_op.create_unique_constraint(
            "uq_assets_user_id_idempotency_key", ["user_id", "idempotency_key"]
        )


def downgrade():
    with op.batch_alter_table("assets") as batch_op:
        batch_op.drop_constraint("uq_assets_user_id_idempotency_key", type_="unique")
        batch_op.drop_column("idempotency_key")
