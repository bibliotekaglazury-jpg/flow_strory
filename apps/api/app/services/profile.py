"""Aggregated per-user summary across every product surface: assets, video generations,
try-on look projects, subtitle projects and the credit ledger.

Read-only - nothing here mutates state, so it never needs the row lock
app.services.credits.account() takes for the write path. Each product already scopes its
own data by user_id (tested per product); this just totals what already exists rather
than introducing a new source of truth.
"""

from sqlalchemy import func, select

from app.db import Account, Asset, Generation, Ledger, LookProject, SubtitleProject

RECENT_TRANSACTIONS_LIMIT = 10


def summary(db, user_id):
    asset_counts = dict(
        db.execute(
            select(Asset.role, func.count()).where(Asset.user_id == user_id).group_by(Asset.role)
        ).all()
    )
    generation_counts = dict(
        db.execute(
            select(Generation.status, func.count())
            .where(Generation.user_id == user_id)
            .group_by(Generation.status)
        ).all()
    )
    look_projects = db.scalar(
        select(func.count()).select_from(LookProject).where(LookProject.user_id == user_id)
    )
    subtitle_projects = db.scalar(
        select(func.count()).select_from(SubtitleProject).where(SubtitleProject.user_id == user_id)
    )
    account = db.scalar(select(Account).where(Account.user_id == user_id))
    recent = list(
        db.scalars(
            select(Ledger)
            .where(Ledger.user_id == user_id)
            .order_by(Ledger.created_at.desc())
            .limit(RECENT_TRANSACTIONS_LIMIT)
        )
    )
    return {
        "userId": user_id,
        "credits": {
            "available": account.available if account else 0,
            "reserved": account.reserved if account else 0,
        },
        "assets": {"total": sum(asset_counts.values()), "byRole": asset_counts},
        "generations": {"total": sum(generation_counts.values()), "byStatus": generation_counts},
        "lookProjects": {"total": look_projects or 0},
        "subtitleProjects": {"total": subtitle_projects or 0},
        "recentTransactions": [
            {
                "id": t.id,
                "kind": t.kind,
                "availableDelta": t.available_delta,
                "reservedDelta": t.reserved_delta,
                "generationId": t.generation_id,
                "createdAt": t.created_at,
            }
            for t in recent
        ],
    }
