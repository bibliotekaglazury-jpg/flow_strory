"""Try-on projects: one generation's model, products, settings and every photo it produced.

A project is the folder the try-on screen shows. Photos were previously kept only in the
browser, so a reload lost them even though the images themselves were stored.
"""

from sqlalchemy import delete as sa_delete, func, select

from app.db import Asset, LookPhoto, LookProject, now
from app.errors import DomainError
from app.services.assets import owned_inputs
from app.services.storage import Storage, asset_view

LABELS = {None: "Hero", "front": "Front", "three_quarter": "¾", "back": "Back", "detail": "Detail"}
LIST_LIMIT = 50


def owned(db, user_id, project_id):
    project = db.scalar(
        select(LookProject).where(LookProject.id == project_id, LookProject.user_id == user_id)
    )
    if not project:
        raise DomainError("LOOK_PROJECT_NOT_FOUND", "That project is unavailable.", 404)
    return project


def create(db, user_id, body):
    inputs = body.inputAssets.model_dump()
    owned_inputs(db, user_id, inputs)
    project = LookProject(
        user_id=user_id, input_assets=inputs, scene=body.scene, aspect_ratio=body.aspectRatio
    )
    db.add(project)
    db.flush()
    return detail(db, project)


def delete(db, user_id, project_id):
    """Removes a try-on folder and its photo records. Children are deleted explicitly rather
    than left to the DB's ON DELETE CASCADE, matching Subtitle Studio's project delete: SQLite
    (used in tests) does not enforce foreign keys by default. The model/product/output assets
    are left alone — they are reusable library assets, not owned by this project."""
    project = owned(db, user_id, project_id)
    db.execute(sa_delete(LookPhoto).where(LookPhoto.project_id == project_id))
    db.delete(project)
    db.flush()


def record(db, project, asset, angle):
    position = db.scalar(
        select(func.count()).select_from(LookPhoto).where(LookPhoto.project_id == project.id)
    )
    db.add(
        LookPhoto(
            project_id=project.id,
            asset_id=asset.id,
            label=LABELS.get(angle, "Hero"),
            position=position,
        )
    )
    project.updated_at = now()
    db.flush()


def _photos(db, project):
    return list(
        db.scalars(
            select(LookPhoto)
            .where(LookPhoto.project_id == project.id)
            .order_by(LookPhoto.position)
        )
    )


def _images(db, project, photos):
    if not photos:
        return {}
    rows = db.scalars(
        select(Asset).where(
            Asset.id.in_([photo.asset_id for photo in photos]), Asset.user_id == project.user_id
        )
    )
    return {asset.id: asset for asset in rows}


def summaries(db, user_id):
    """Newest project first; a project whose generation produced nothing is not a folder."""
    storage = Storage()
    projects = db.scalars(
        select(LookProject)
        .where(LookProject.user_id == user_id)
        .order_by(LookProject.created_at.desc())
        .limit(LIST_LIMIT)
    )
    result = []
    for project in projects:
        photos = _photos(db, project)
        if not photos:
            continue
        cover = _images(db, project, photos[:1]).get(photos[0].asset_id)
        result.append(
            {
                "id": project.id,
                "scene": project.scene,
                "aspectRatio": project.aspect_ratio,
                "photoCount": len(photos),
                "coverUrl": asset_view(cover, storage)["url"] if cover else None,
                "createdAt": project.created_at,
                "updatedAt": project.updated_at,
            }
        )
    return result


def detail(db, project):
    storage = Storage()
    inputs = owned_inputs(db, project.user_id, project.input_assets)
    photos = _photos(db, project)
    images = _images(db, project, photos)
    return {
        "id": project.id,
        "scene": project.scene,
        "aspectRatio": project.aspect_ratio,
        "inputAssets": project.input_assets,
        "model": next((asset_view(a, storage) for a in inputs if a.role == "person"), None),
        "products": [asset_view(a, storage) for a in inputs if a.role == "product"],
        "photos": [
            {"asset": asset_view(images[photo.asset_id], storage), "label": photo.label}
            for photo in photos
            if photo.asset_id in images
        ],
        "createdAt": project.created_at,
        "updatedAt": project.updated_at,
    }
