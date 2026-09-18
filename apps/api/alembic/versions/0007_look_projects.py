"""Try-on projects: one generation's inputs and every photo it produced survive a reload."""

from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "look_projects",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("user_id", sa.String, nullable=False),
        sa.Column("input_assets", sa.JSON, nullable=False),
        sa.Column("scene", sa.String, nullable=False),
        sa.Column("aspect_ratio", sa.String, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_look_projects_user_id", "look_projects", ["user_id"])
    op.create_table(
        "look_photos",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column(
            "project_id",
            sa.String,
            sa.ForeignKey("look_projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("asset_id", sa.String, nullable=False),
        sa.Column("label", sa.String, nullable=False),
        sa.Column("position", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_look_photos_project_id", "look_photos", ["project_id"])


def downgrade():
    op.drop_table("look_photos")
    op.drop_table("look_projects")
