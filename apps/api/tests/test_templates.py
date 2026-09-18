import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Account, Asset, Base
from app.errors import DomainError
from app.schemas import CreateGeneration, Estimate
from app.services import templates
from app.services.generations import create, quote
from app.services.rendering import validate_inputs

FIXTURE = json.loads(
    (Path(__file__).resolve().parents[3] / "packages/contracts/template-filter-cases.json").read_text()
)

EXPECTED_GENERATIVE_TEMPLATE_IDS = [
    "ugc_review",
    "product_unboxing",
    "problem_solution",
    "product_demo",
    "testimonial",
    "trending_style",
    "hook_cta",
    "before_after",
    "self_presentation",
]


def test_runtime_catalog_contains_only_current_generative_templates():
    catalog = templates.records()
    assert [item["id"] for item in catalog] == EXPECTED_GENERATIVE_TEMPLATE_IDS
    assert all(item["templateType"] == "generative" for item in catalog)


@pytest.mark.parametrize("case", FIXTURE["cases"])
def test_shared_catalog_filter_vectors(case):
    assert [t["id"] for t in FIXTURE["templates"] if templates.matches(t, case["filters"])] == case[
        "expected"
    ]


@pytest.fixture
def catalog(monkeypatch):
    spec = dict(
        FIXTURE["templates"][0],
        id="rve_test",
        inputSchema={
            "type": "object",
            "properties": {"headline": {"type": "string", "maxLength": 40}},
            "additionalProperties": False,
        },
    )
    monkeypatch.setattr(templates, "records", lambda: [spec])
    return spec


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Account(user_id="alice", available=1000, reserved=0))
        db.flush()
        yield db


def test_public_catalog_strips_implementation(catalog):
    catalog.update(source={"path": "/private/source"}, remotion={"componentPath": "private.tsx"})
    public = templates.public_catalog()[0]
    assert "source" not in public and "remotion" not in public
    assert public["available"] is True


def test_render_quote_bound_to_normalized_inputs_and_ledger(db, catalog, monkeypatch):
    import app.services.generations as generations

    monkeypatch.setattr(
        generations, "registry", lambda: (_ for _ in ()).throw(AssertionError("AI routing called"))
    )
    request = dict(
        templateId="rve_test",
        duration=15,
        aspectRatio="9:16",
        inputAssets={},
        normalizedInputs={"headline": "First"},
    )
    q = quote(db, "alice", Estimate(**request))
    body = CreateGeneration(**request, quoteId=q.id)
    changed = body.model_copy(update={"normalizedInputs": {"headline": "Changed"}})
    with pytest.raises(DomainError, match="Refresh"):
        create(db, "alice", changed, "changed")
    g = create(db, "alice", body, "same")
    assert g.selected_model == "render_only" and g.status == "queued"
    assert create(db, "alice", body, "same").id == g.id
    assert db.get(Account, "alice").reserved == q.amount


@pytest.mark.parametrize("value", ["https://evil.example/a.png", "/etc/passwd", "../secret", "other-user"])
def test_media_requires_owned_asset(db, catalog, value):
    catalog["inputSchema"] = {
        "properties": {"productImage": {"type": "string", "format": "asset-id", "mediaType": "image"}}
    }
    db.add(
        Asset(
            id="other-user",
            user_id="bob",
            role="product",
            mime_type="image/png",
            file_name="x.png",
            size_bytes=1,
            storage_key="bob/x",
        )
    )
    db.flush()
    with pytest.raises(DomainError) as exc:
        validate_inputs(db, "alice", catalog, {"productImage": value})
    assert exc.value.code == "INVALID_ASSET"


def test_unknown_input_and_oversize_text_rejected(db, catalog):
    for value in [{"componentPath": "/evil"}, {"headline": "x" * 41}]:
        with pytest.raises(DomainError):
            validate_inputs(db, "alice", catalog, value)


def test_render_cancel_after_start_refunds_without_remote_provider(db, catalog):
    from sqlalchemy import select
    from app.db import Job
    from app.services.generations import cancel

    request = dict(
        templateId="rve_test", duration=15, aspectRatio="9:16", inputAssets={}, normalizedInputs={}
    )
    q = quote(db, "alice", Estimate(**request))
    g = create(db, "alice", CreateGeneration(**request, quoteId=q.id), "cancel-render")
    job = db.scalar(select(Job).where(Job.generation_id == g.id))
    job.submission_state = "intent"
    g.status = "generating"
    cancel(db, "alice", g.id)
    assert g.status == "cancelled" and g.charged == 0
    assert db.get(Account, "alice").available == 1000


def test_definition_change_invalidates_quote_without_reserving(db, catalog):
    request = dict(templateId="rve_test", duration=15, aspectRatio="9:16", inputAssets={})
    q = quote(db, "alice", Estimate(**request))
    body = CreateGeneration(**request, quoteId=q.id)
    catalog["version"] = "changed"
    with pytest.raises(DomainError) as exc:
        create(db, "alice", body, "definition-changed")
    assert exc.value.code == "STALE_QUOTE"
    assert db.get(Account, "alice").reserved == 0


def test_preview_and_validation_metadata_do_not_change_definition(catalog):
    before = templates.definition_fingerprint(catalog)
    catalog.update(
        previewVideo="/new.mp4", thumbnail="/new.webp", validation={"checkedAt": "later"}, featured=True
    )
    assert templates.definition_fingerprint(catalog) == before


def test_history_uses_admitted_asset_ids_after_schema_change(db, catalog):
    from app.services.generations import view, history

    catalog["inputSchema"] = {"properties": {"productImage": {"type": "string", "mediaType": "image"}}}
    asset = Asset(
        id="owned-image",
        user_id="alice",
        role="product",
        mime_type="image/png",
        file_name="x.png",
        size_bytes=1,
        storage_key="alice/x",
    )
    db.add(asset)
    db.flush()
    request = dict(
        templateId="rve_test",
        duration=15,
        aspectRatio="9:16",
        inputAssets={},
        normalizedInputs={"productImage": asset.id},
    )
    q = quote(db, "alice", Estimate(**request))
    g = create(db, "alice", CreateGeneration(**request, quoteId=q.id), "history-schema")
    assert g.snapshot["renderInputAssetIds"] == [asset.id]
    catalog["inputSchema"] = {"properties": {"newField": {"type": "string"}}, "required": ["newField"]}
    for status in ["completed", "failed"]:
        g.status = status
        assert view(db, g)["inputAssets"][0]["id"] == asset.id
        assert history(db, "alice", 20, None)["generations"][0]["id"] == g.id


def test_api_catalog_defaults_to_enabled_and_supports_explicit_disabled(monkeypatch):
    from fastapi.testclient import TestClient
    from app.auth import identity
    from app.main import app

    monkeypatch.setattr(templates, "records", lambda: FIXTURE["templates"])
    app.dependency_overrides[identity] = lambda: "catalog-test"
    try:
        with TestClient(app) as client:
            response = client.get("/api/templates")
            assert response.status_code == 200, response.text
            assert [t["id"] for t in response.json()["templates"]] == ["text", "photo", "both"]
            assert all(t["available"] for t in response.json()["templates"])
            assert [t["id"] for t in client.get("/api/templates?enabled=false").json()["templates"]] == [
                "video"
            ]
    finally:
        app.dependency_overrides.pop(identity, None)
