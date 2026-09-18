"""A multi-item look: several product images shown together as one outfit."""

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Asset, Base
from app.errors import DomainError
from app.schemas import LOOK_SIZE, InputAssets
from app.services.assets import owned_inputs


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        for identifier, owner, role in [
            ("hero", "alice", "product"),
            ("scarf", "alice", "product"),
            ("face", "alice", "person"),
            ("stranger", "bob", "product"),
        ]:
            session.add(
                Asset(
                    id=identifier,
                    user_id=owner,
                    role=role,
                    mime_type="image/png",
                    file_name=f"{identifier}.png",
                    size_bytes=1,
                    storage_key=f"{owner}/{identifier}",
                )
            )
        session.flush()
        yield session


def test_items_are_ordinary_product_images_so_no_new_role_is_needed(db):
    assets = owned_inputs(
        db,
        "alice",
        InputAssets(
            productImageId="hero",
            personImageId="face",
            items=[{"assetId": "scarf", "label": "scarf"}],
        ).model_dump(),
    )
    assert {a.id for a in assets} == {"hero", "face", "scarf"}
    assert {a.role for a in assets if a.id in {"hero", "scarf"}} == {"product"}


def test_items_are_ownership_checked_like_every_other_input(db):
    with pytest.raises(DomainError) as exc:
        owned_inputs(
            db,
            "alice",
            InputAssets(items=[{"assetId": "stranger", "label": "bag"}]).model_dump(),
        )
    assert exc.value.code == "INVALID_ASSET"


def test_a_person_photo_cannot_be_passed_off_as_a_look_item(db):
    with pytest.raises(DomainError):
        owned_inputs(
            db, "alice", InputAssets(items=[{"assetId": "face", "label": "hat"}]).model_dump()
        )


@pytest.mark.parametrize(
    "payload",
    [
        {"items": [{"assetId": "scarf", "label": "scarf"}, {"assetId": "scarf", "label": "again"}]},
        {"productImageId": "hero", "items": [{"assetId": "hero", "label": "same"}]},
    ],
)
def test_the_same_image_cannot_be_two_pieces_of_the_look(payload):
    with pytest.raises(ValidationError):
        InputAssets(**payload)


def test_look_size_and_labels_are_bounded():
    with pytest.raises(ValidationError):
        InputAssets(items=[{"assetId": f"a{i}", "label": "x"} for i in range(LOOK_SIZE + 1)])
    # The main product image counts as the first piece of the look, not an extra slot.
    with pytest.raises(ValidationError):
        InputAssets(
            productImageId="hero",
            items=[{"assetId": f"a{i}", "label": "x"} for i in range(LOOK_SIZE)],
        )
    InputAssets(
        productImageId="hero",
        items=[{"assetId": f"a{i}", "label": "x"} for i in range(LOOK_SIZE - 1)],
    )
    with pytest.raises(ValidationError):
        InputAssets(items=[{"assetId": "a", "label": "   "}])
    with pytest.raises(ValidationError):
        InputAssets(items=[{"assetId": "a", "label": "x" * 41}])
