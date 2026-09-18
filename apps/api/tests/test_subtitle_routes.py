"""Subtitle Studio HTTP routes: request/response shape, ownership, idempotency, revision conflict."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.auth import identity
from app.db import Base, Asset, session
from app.main import app


@pytest.fixture
def client(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    with factory() as seed, seed.begin():
        for identifier, owner, duration in [("clip", "alice", 12.0), ("bob-clip", "bob", 12.0)]:
            seed.add(
                Asset(
                    id=identifier,
                    user_id=owner,
                    role="source_video",
                    mime_type="video/mp4",
                    file_name=f"{identifier}.mp4",
                    size_bytes=1,
                    storage_key=f"{owner}/{identifier}",
                    duration_seconds=duration,
                )
            )

    def db():
        with factory() as item, item.begin():
            yield item

    app.dependency_overrides[identity] = lambda: "alice"
    app.dependency_overrides[session] = db
    try:
        with TestClient(app) as value:
            value.factory = factory  # lets a test complete a render out-of-band, like the worker does
            yield value
    finally:
        app.dependency_overrides.pop(identity, None)
        app.dependency_overrides.pop(session, None)


def create_body(asset_id="clip", ratio="9:16"):
    return {"sourceAssetId": asset_id, "aspectRatio": ratio}


def test_create_returns_202_with_the_full_project_shape(client):
    response = client.post(
        "/api/subtitle-projects", json=create_body(), headers={"Idempotency-Key": "key-1"}
    )
    assert response.status_code == 202
    project = response.json()["project"]
    assert project["status"] == "transcribing"
    assert project["sourceAsset"]["id"] == "clip"
    assert project["cues"] == []
    assert project["style"]["preset"] == "modern"
    assert project["revision"] == 0
    assert project["latestExport"] is None


def test_create_requires_the_idempotency_key_header(client):
    response = client.post("/api/subtitle-projects", json=create_body())
    assert response.status_code == 422


def test_repeated_key_returns_the_same_project_without_a_second_call(client):
    first = client.post(
        "/api/subtitle-projects", json=create_body(), headers={"Idempotency-Key": "same"}
    )
    second = client.post(
        "/api/subtitle-projects", json=create_body(), headers={"Idempotency-Key": "same"}
    )
    assert first.json()["project"]["id"] == second.json()["project"]["id"]


def test_same_key_different_body_conflicts(client):
    client.post("/api/subtitle-projects", json=create_body(ratio="9:16"), headers={"Idempotency-Key": "same"})
    conflict = client.post(
        "/api/subtitle-projects", json=create_body(ratio="16:9"), headers={"Idempotency-Key": "same"}
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"


def test_alice_cannot_read_bobs_project(client):
    response = client.post(
        "/api/subtitle-projects", json=create_body("bob-clip"), headers={"Idempotency-Key": "bob-key"}
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "INVALID_ASSET"


def test_get_and_list_return_owned_projects_newest_first(client):
    a = client.post(
        "/api/subtitle-projects", json=create_body(), headers={"Idempotency-Key": "k1"}
    ).json()["project"]
    b = client.post(
        "/api/subtitle-projects", json=create_body(), headers={"Idempotency-Key": "k2"}
    ).json()["project"]

    fetched = client.get(f"/api/subtitle-projects/{a['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["project"]["id"] == a["id"]

    listed = client.get("/api/subtitle-projects")
    assert [p["id"] for p in listed.json()["projects"]] == [b["id"], a["id"]]
    assert listed.json()["nextCursor"] is None


def test_get_unknown_project_is_a_clean_404(client):
    response = client.get("/api/subtitle-projects/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SUBTITLE_PROJECT_NOT_FOUND"


def test_patch_increments_revision_and_a_stale_revision_conflicts(client):
    project = client.post(
        "/api/subtitle-projects", json=create_body(), headers={"Idempotency-Key": "k"}
    ).json()["project"]
    patch_body = {
        "revision": 0,
        "aspectRatio": "9:16",
        "cues": [
            {
                "id": "c1",
                "startMs": 0,
                "endMs": 1000,
                "text": "Hello",
                "words": [{"id": "w1", "text": "Hello", "startMs": 0, "endMs": 1000}],
            }
        ],
        "style": {
            "preset": "classic",
            "position": "top",
            "size": "large",
            "safeArea": False,
            "textColor": "#000000",
            "highlightColor": "#FF0000",
        },
    }
    updated = client.patch(f"/api/subtitle-projects/{project['id']}", json=patch_body)
    assert updated.status_code == 200
    assert updated.json()["project"]["revision"] == 1
    assert updated.json()["project"]["style"]["preset"] == "classic"

    stale = client.patch(f"/api/subtitle-projects/{project['id']}", json=patch_body)
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "REVISION_CONFLICT"


def test_export_requires_the_current_revision_and_is_idempotent(client):
    project = client.post(
        "/api/subtitle-projects", json=create_body(), headers={"Idempotency-Key": "k"}
    ).json()["project"]

    stale_export = client.post(
        f"/api/subtitle-projects/{project['id']}/exports",
        json={"revision": 1},
        headers={"Idempotency-Key": "export-key"},
    )
    assert stale_export.status_code == 409
    assert stale_export.json()["error"]["code"] == "REVISION_CONFLICT"

    first = client.post(
        f"/api/subtitle-projects/{project['id']}/exports",
        json={"revision": 0},
        headers={"Idempotency-Key": "export-key-2"},
    )
    assert first.status_code == 202
    assert first.json()["export"]["status"] == "queued"
    second = client.post(
        f"/api/subtitle-projects/{project['id']}/exports",
        json={"revision": 0},
        headers={"Idempotency-Key": "export-key-2"},
    )
    assert second.json()["export"]["id"] == first.json()["export"]["id"]


def test_get_export_reports_poll_after_ms_only_while_not_terminal(client):
    project = client.post(
        "/api/subtitle-projects", json=create_body(), headers={"Idempotency-Key": "k"}
    ).json()["project"]
    export = client.post(
        f"/api/subtitle-projects/{project['id']}/exports",
        json={"revision": 0},
        headers={"Idempotency-Key": "ek"},
    ).json()["export"]

    polled = client.get(f"/api/subtitle-projects/{project['id']}/exports/{export['id']}")
    assert polled.status_code == 200
    assert polled.json()["pollAfterMs"] == 2000


def test_alice_cannot_read_bobs_export(client):
    app.dependency_overrides[identity] = lambda: "bob"
    bob_project = client.post(
        "/api/subtitle-projects", json=create_body("bob-clip"), headers={"Idempotency-Key": "bk"}
    ).json()["project"]
    bob_export = client.post(
        f"/api/subtitle-projects/{bob_project['id']}/exports",
        json={"revision": 0},
        headers={"Idempotency-Key": "be"},
    ).json()["export"]

    app.dependency_overrides[identity] = lambda: "alice"
    response = client.get(f"/api/subtitle-projects/{bob_project['id']}/exports/{bob_export['id']}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SUBTITLE_PROJECT_NOT_FOUND"


def _complete(client, project_id, export_id):
    with client.factory() as db, db.begin():
        from app.db import SubtitleExport

        export = db.get(SubtitleExport, export_id)
        export.status = "completed"
        export.output_asset_id = "clip"
        db.flush()


def test_share_export_returns_a_token_the_public_endpoint_can_resolve(client):
    project = client.post(
        "/api/subtitle-projects", json=create_body(), headers={"Idempotency-Key": "sk"}
    ).json()["project"]
    export = client.post(
        f"/api/subtitle-projects/{project['id']}/exports",
        json={"revision": 0},
        headers={"Idempotency-Key": "sk-export"},
    ).json()["export"]
    _complete(client, project["id"], export["id"])

    shared = client.post(f"/api/subtitle-projects/{project['id']}/exports/{export['id']}/share")
    assert shared.status_code == 200
    token = shared.json()["export"]["shareToken"]
    assert token

    public = client.get(f"/api/subtitle-shares/{token}")
    assert public.status_code == 200
    assert public.json()["export"]["outputAsset"]["id"] == "clip"

    unshared = client.delete(f"/api/subtitle-projects/{project['id']}/exports/{export['id']}/share")
    assert unshared.json()["export"]["shareToken"] is None
    assert client.get(f"/api/subtitle-shares/{token}").status_code == 404


def test_sharing_someone_elses_export_is_a_clean_404(client):
    app.dependency_overrides[identity] = lambda: "bob"
    bob_project = client.post(
        "/api/subtitle-projects", json=create_body("bob-clip"), headers={"Idempotency-Key": "bk2"}
    ).json()["project"]
    bob_export = client.post(
        f"/api/subtitle-projects/{bob_project['id']}/exports",
        json={"revision": 0},
        headers={"Idempotency-Key": "be2"},
    ).json()["export"]

    app.dependency_overrides[identity] = lambda: "alice"
    response = client.post(
        f"/api/subtitle-projects/{bob_project['id']}/exports/{bob_export['id']}/share"
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SUBTITLE_PROJECT_NOT_FOUND"


def test_an_unknown_share_token_is_a_clean_404(client):
    response = client.get("/api/subtitle-shares/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SHARE_NOT_FOUND"


def test_delete_removes_the_project_and_a_repeat_delete_is_a_clean_404(client):
    project = client.post(
        "/api/subtitle-projects", json=create_body(), headers={"Idempotency-Key": "dk"}
    ).json()["project"]

    first = client.delete(f"/api/subtitle-projects/{project['id']}")
    assert first.status_code == 204

    assert client.get(f"/api/subtitle-projects/{project['id']}").status_code == 404
    assert client.delete(f"/api/subtitle-projects/{project['id']}").status_code == 404


def test_bob_cannot_delete_alices_project(client):
    project = client.post(
        "/api/subtitle-projects", json=create_body(), headers={"Idempotency-Key": "dk2"}
    ).json()["project"]

    app.dependency_overrides[identity] = lambda: "bob"
    response = client.delete(f"/api/subtitle-projects/{project['id']}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SUBTITLE_PROJECT_NOT_FOUND"

    app.dependency_overrides[identity] = lambda: "alice"
    assert client.get(f"/api/subtitle-projects/{project['id']}").status_code == 200
