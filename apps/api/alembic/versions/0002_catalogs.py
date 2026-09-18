"""Versioned product catalogs and minimal project ownership containers."""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "projects",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("user_id", sa.String, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_projects_user_id", "projects", ["user_id"])
    templates = op.create_table(
        "templates",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("description", sa.String, nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("instructions", sa.String, nullable=False),
        sa.Column("scene_beats", sa.JSON, nullable=False),
        sa.Column("capabilities", sa.JSON, nullable=False),
        sa.Column("enabled", sa.Boolean, nullable=False),
    )
    specs = [
        (
            "ugc_review",
            "UGC Review",
            "A natural product review.",
            "Hook, introduce the product, demonstrate, close with a call to action.",
        ),
        (
            "product_unboxing",
            "Product Unboxing",
            "Reveal the product step by step.",
            "Introduce the package, reveal the product, show details, close.",
        ),
        (
            "problem_solution",
            "Problem → Solution",
            "Connect a problem to your product.",
            "State a relevant problem without invented claims, demonstrate the product, close.",
        ),
        (
            "product_demo",
            "Product Demo",
            "Show the product in use.",
            "Introduce the use case, demonstrate key actions, close.",
        ),
        (
            "testimonial",
            "Testimonial",
            "Tell a personal product story.",
            "Use an explicitly scripted narrator; never invent a real customer endorsement.",
        ),
        (
            "trending_style",
            "Trending Style",
            "A fast, contemporary product story.",
            "Open with a strong visual hook, show product use, close.",
        ),
        (
            "hook_cta",
            "Hook → CTA",
            "Lead with a hook, finish with action.",
            "Open with a clear hook, show the product, deliver a call to action.",
        ),
        (
            "before_after",
            "Before / After",
            "Show a truthful product comparison.",
            "Compare only substantiated conditions; do not fabricate product results.",
        ),
    ]
    op.bulk_insert(
        templates,
        [
            dict(
                id=i,
                name=n,
                description=d,
                version=1,
                instructions=s,
                scene_beats=[s],
                capabilities={},
                enabled=True,
            )
            for i, n, d, s in specs
        ],
    )
    providers = op.create_table(
        "providers",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("enabled", sa.Boolean, nullable=False),
        sa.Column("configuration", sa.JSON, nullable=False),
    )
    op.bulk_insert(
        providers,
        [
            {"id": "mock", "enabled": False, "configuration": {"developmentOnly": True}},
            {"id": "muapi", "enabled": False, "configuration": {"credentials": "environment"}},
        ],
    )
    models = op.create_table(
        "models",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("provider_id", sa.String, sa.ForeignKey("providers.id"), nullable=False),
        sa.Column("vendor_model_id", sa.String, nullable=False),
        sa.Column("media_type", sa.String, nullable=False),
        sa.Column("capabilities", sa.JSON, nullable=False),
        sa.Column("enabled", sa.Boolean, nullable=False),
        sa.Column("priority", sa.Integer, nullable=False),
        sa.Column("cost_rules", sa.JSON, nullable=False),
    )
    op.bulk_insert(
        models,
        [
            {
                "id": "simulation-video",
                "provider_id": "mock",
                "vendor_model_id": "simulation",
                "media_type": "video",
                "capabilities": {"durations": [15, 20, 30], "aspectRatios": ["9:16", "1:1", "16:9"]},
                "enabled": False,
                "priority": 10,
                "cost_rules": {"nonmonetary": True},
            },
            {
                "id": "studio-video",
                "provider_id": "muapi",
                "vendor_model_id": "seedance-2.5",
                "media_type": "video",
                "capabilities": {"source": "server provider registry"},
                "enabled": False,
                "priority": 10,
                "cost_rules": {"source": "VIDEO_CREDITS_PER_SECOND"},
            },
        ],
    )


def downgrade():
    for table in ["models", "providers", "templates", "projects"]:
        op.drop_table(table)
