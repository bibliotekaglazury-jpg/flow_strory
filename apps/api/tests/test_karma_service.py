"""Karma -> UGC service mode, end to end through the real identity dependency.

Karma sends the service bearer plus X-Karma-Subject (a UUIDv5 of the workspace). Two
subjects stand in for two Karma workspaces; neither may see or touch the other's data.
"""

import uuid
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.db import Account, Asset, Base, Generation, Ledger, session
from app.main import app
from app.services import try_on, uploads

TOKEN = "karma-service-token-for-tests-0123456789"
NAMESPACE = uuid.UUID("6f6e1f5c-2b8a-5d47-9f0e-4b3a1c7d9e21")
ALICE = str(uuid.uuid5(NAMESPACE, "karma-workspace:alice"))
BOB = str(uuid.uuid5(NAMESPACE, "karma-workspace:bob"))


def png(color="white"):
    data = BytesIO()
    Image.new("RGB", (16, 16), color).save(data, format="PNG")
    return data.getvalue()


def jpeg():
    data = BytesIO()
    Image.new("RGB", (16, 16), "red").save(data, format="JPEG")
    return data.getvalue()


def service(subject, **extra):
    return {"Authorization": f"Bearer {TOKEN}", "X-Karma-Subject": subject, **extra}


@pytest.fixture
def factory(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_PATH", str(tmp_path))
    monkeypatch.setenv("STORAGE_MODE", "local")
    monkeypatch.setenv("IMAGE_PROVIDER", "mock")
    monkeypatch.setenv("AUTH_MODE", "mock")
    monkeypatch.setenv("KARMA_SERVICE_TOKEN", TOKEN)
    monkeypatch.setenv("KARMA_ALLOWED_ORIGINS", "https://app.karmaposting.com")
    monkeypatch.setenv("PUBLIC_API_URL", "http://testserver")
    settings.cache_clear()
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(engine, expire_on_commit=False)


@pytest.fixture
def client(factory):
    def db():
        with factory() as item, item.begin():
            yield item

    app.dependency_overrides[session] = db
    try:
        with TestClient(app) as value:
            yield value
    finally:
        app.dependency_overrides.pop(session, None)
        settings.cache_clear()


def whoami(client, headers):
    """The subject a request ran as, read back from the account it initialised."""
    response = client.get("/api/profile", headers=headers)
    assert response.status_code == 200, response.text
    return response


def subjects(factory):
    with factory() as db:
        return set(db.scalars(select(Account.user_id)))


def direct_upload(client, subject, data, role="person", content_type="image/png", size=None):
    issued = client.post(
        "/api/assets/upload-url",
        json={"role": role, "contentType": content_type, "size": size or len(data), "filename": "a.png"},
        headers=service(subject),
    )
    assert issued.status_code == 201, issued.text
    body = issued.json()
    put = client.put(
        body["uploadUrl"].replace("http://testserver", ""), content=data, headers=body["headers"]
    )
    return body, put


def uploaded_asset(client, subject, role="person", color="white"):
    body, put = direct_upload(client, subject, png(color), role=role)
    assert put.status_code == 204, put.text
    done = client.post(
        "/api/assets/upload-complete",
        json={"uploadId": body["uploadId"], "source": "try_on"},
        headers=service(subject),
    )
    assert done.status_code == 200, done.text
    return done.json()


def staged_files(root):
    return [p for p in (root / "uploads").rglob("*") if p.is_file()]


# --- service auth ---------------------------------------------------------------------------


def test_service_bearer_with_subject_runs_as_that_subject(client, factory):
    whoami(client, service(ALICE))
    assert ALICE in subjects(factory)


def test_a_service_subject_gets_no_development_credits(client, factory):
    whoami(client, service(ALICE))
    with factory() as db:
        assert db.get(Account, ALICE).available == 0
        assert not db.scalar(select(Ledger).where(Ledger.user_id == ALICE))


def test_a_forged_subject_without_the_secret_is_ignored(client, factory):
    whoami(client, {"Authorization": "Bearer not-the-token", "X-Karma-Subject": ALICE})
    whoami(client, {"X-Karma-Subject": ALICE})
    assert ALICE not in subjects(factory)
    assert settings().mock_user_id in subjects(factory)


def test_the_service_bearer_needs_a_valid_v5_subject(client):
    for subject in [None, "", "alice", ALICE.upper(), str(uuid.uuid4()), ALICE + "x"]:
        headers = {"Authorization": f"Bearer {TOKEN}"}
        if subject is not None:
            headers["X-Karma-Subject"] = subject
        response = client.get("/api/profile", headers=headers)
        assert response.status_code == 401, subject


def test_service_mode_is_off_while_the_token_is_unset(client, factory, monkeypatch):
    monkeypatch.setenv("KARMA_SERVICE_TOKEN", "")
    settings.cache_clear()
    whoami(client, service(ALICE))
    assert ALICE not in subjects(factory)


def test_without_the_token_supabase_auth_is_unchanged(client, monkeypatch):
    monkeypatch.setenv("KARMA_SERVICE_TOKEN", "")
    monkeypatch.setenv("AUTH_MODE", "supabase")
    monkeypatch.setenv("SUPABASE_URL", "https://example.invalid")
    settings.cache_clear()
    # The service bearer is not a JWT, so the ordinary path rejects it.
    assert client.get("/api/profile", headers=service(ALICE)).status_code == 401
    assert client.get("/api/profile").status_code == 401


def test_with_the_token_set_a_wrong_bearer_still_takes_the_supabase_path(client, monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "supabase")
    monkeypatch.setenv("SUPABASE_URL", "https://example.invalid")
    settings.cache_clear()
    response = client.get(
        "/api/profile", headers={"Authorization": "Bearer forged", "X-Karma-Subject": ALICE}
    )
    assert response.status_code == 401
    assert client.get("/api/profile", headers=service(ALICE)).status_code == 200


def test_production_refuses_a_short_service_token():
    from app.config import Settings

    with pytest.raises(ValueError, match="KARMA_SERVICE_TOKEN"):
        Settings(
            app_env="production",
            auth_mode="supabase",
            storage_mode="s3",
            video_provider="openrouter",
            image_provider="openrouter",
            subtitle_transcription_provider="whisper",
            text_provider="openai",
            supabase_url="https://x.supabase.co",
            s3_access_key_id="id",
            s3_secret_access_key="secret",
            karma_service_token="short",
        )


# --- reservation / one charge ---------------------------------------------------------------


def try_on_body(person, product, key="preview-0001", **extra):
    return {
        "inputAssets": {"personImageId": person, "productImageId": product},
        "aspectRatio": "9:16",
        "idempotencyKey": key,
        **extra,
    }


def test_a_service_paid_start_without_a_reservation_is_refused(client):
    person = uploaded_asset(client, ALICE)
    product = uploaded_asset(client, ALICE, role="product", color="blue")
    body = try_on_body(person["id"], product["id"])
    response = client.post("/api/try-on", json=body, headers=service(ALICE))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "RESERVATION_REQUIRED"
    bad = client.post("/api/try-on", json=body, headers=service(ALICE, **{"X-Karma-Reservation": "a b"}))
    assert bad.status_code == 403


def test_a_video_start_without_a_reservation_is_refused_before_admission(client, monkeypatch):
    from app.services import generations

    called = []
    monkeypatch.setattr(generations, "create", lambda *a, **k: called.append(a))
    body = {
        "productUrl": "https://example.com",
        "inputAssets": {},
        "templateId": "ugc_review",
        "brief": "Show product",
        "duration": 15,
        "aspectRatio": "9:16",
        "promptId": "p",
        "prompt": "x",
        "quoteId": "q",
    }
    response = client.post("/api/generations", json=body, headers=service(ALICE, **{"Idempotency-Key": "k"}))
    assert response.status_code == 403, response.text
    assert called == []


def test_a_service_try_on_with_a_reservation_debits_nothing(client, factory, monkeypatch):
    monkeypatch.setenv("IMAGE_CREDITS_PER_GENERATION", "4")
    settings.cache_clear()
    person = uploaded_asset(client, ALICE)
    product = uploaded_asset(client, ALICE, role="product", color="blue")
    response = client.post(
        "/api/try-on",
        json=try_on_body(person["id"], product["id"]),
        headers=service(ALICE, **{"X-Karma-Reservation": "hold-1"}),
    )
    assert response.status_code == 201, response.text
    assert response.json()["creditsCharged"] == 0
    with factory() as db:
        account = db.get(Account, ALICE)
        assert (account.available, account.reserved) == (0, 0)
        assert [row.kind for row in db.scalars(select(Ledger).where(Ledger.user_id == ALICE))] == [
            "karma_reservation"
        ]


def test_an_ordinary_user_needs_no_reservation_header(client):
    response = client.post("/api/try-on", json=try_on_body("missing", "missing"))
    # Reaches the asset check, not the reservation check.
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "INVALID_ASSET"


# --- isolation between two subjects ---------------------------------------------------------


@pytest.fixture
def alice_world(client, factory):
    person = uploaded_asset(client, ALICE)
    product = uploaded_asset(client, ALICE, role="product", color="blue")
    project = client.post(
        "/api/look-projects",
        json={
            "inputAssets": {"personImageId": person["id"], "productImageId": product["id"]},
            "scene": "studio",
            "aspectRatio": "9:16",
        },
        headers=service(ALICE),
    )
    assert project.status_code == 201, project.text
    project_id = project.json()["project"]["id"]
    photo = client.post(
        "/api/try-on",
        json=try_on_body(person["id"], product["id"], projectId=project_id),
        headers=service(ALICE, **{"X-Karma-Reservation": "hold-a"}),
    )
    assert photo.status_code == 201, photo.text
    with factory() as db, db.begin():
        db.add(
            Generation(
                id="alice-video",
                user_id=ALICE,
                snapshot={
                    "inputAssets": {},
                    "templateId": "ugc_review",
                    "model": "auto",
                    "prompt": "Show the product.",
                    "duration": 15,
                    "aspectRatio": "9:16",
                },
                request_hash="h",
                idempotency_key="k",
                status="queued",
                estimated=0,
                charged=0,
            )
        )
    pending, _ = direct_upload(client, ALICE, png("green"))
    return {
        "person": person,
        "product": product,
        "project": project_id,
        "photo": photo.json()["asset"],
        "upload": pending["uploadId"],
    }


def test_bob_cannot_read_alices_library_projects_or_generations(client, alice_world):
    bob = service(BOB)
    for role in ("person", "product"):
        listed = client.get(f"/api/assets?role={role}&source=try_on", headers=bob).json()["assets"]
        assert listed == []
    assert client.get("/api/look-projects", headers=bob).json()["projects"] == []
    assert client.get(f"/api/look-projects/{alice_world['project']}", headers=bob).status_code == 404
    assert client.get("/api/generations", headers=bob).json()["generations"] == []
    assert client.get("/api/generations/alice-video", headers=bob).status_code == 404
    profile = client.get("/api/profile", headers=bob).json()
    assert ALICE not in str(profile)
    # Alice still sees her own.
    alice = service(ALICE)
    assert client.get(f"/api/look-projects/{alice_world['project']}", headers=alice).status_code == 200
    assert client.get("/api/generations/alice-video", headers=alice).status_code == 200


def test_bob_cannot_delete_or_cancel_alices_things(client, alice_world):
    bob = service(BOB)
    assert client.delete(f"/api/look-projects/{alice_world['project']}", headers=bob).status_code == 404
    assert client.post("/api/generations/alice-video/cancel", headers=bob).status_code == 404
    assert client.delete("/api/generations/alice-video", headers=bob).status_code == 404
    alice = service(ALICE)
    assert client.get(f"/api/look-projects/{alice_world['project']}", headers=alice).status_code == 200
    assert client.get("/api/generations/alice-video", headers=alice).status_code == 200


def test_bob_cannot_generate_with_alices_photos_project_or_preview(client, alice_world, monkeypatch):
    calls = []

    async def generate(*args):
        calls.append(args)
        return png()

    monkeypatch.setattr(try_on, "provider", lambda: type("P", (), {"generate": staticmethod(generate)})())
    bob = service(BOB, **{"X-Karma-Reservation": "hold-b"})
    own_person = uploaded_asset(client, BOB)
    own_product = uploaded_asset(client, BOB, role="product", color="blue")
    attempts = [
        try_on_body(alice_world["person"]["id"], own_product["id"], key="bob-0001"),
        try_on_body(own_person["id"], alice_world["product"]["id"], key="bob-0002"),
        try_on_body(own_person["id"], own_product["id"], key="bob-0003", projectId=alice_world["project"]),
        try_on_body(
            own_person["id"], own_product["id"], key="bob-0004", baseAssetId=alice_world["photo"]["id"]
        ),
    ]
    for body in attempts:
        response = client.post("/api/try-on", json=body, headers=bob)
        assert response.status_code == 404, (body, response.text)
    project = client.post(
        "/api/look-projects",
        json={
            "inputAssets": {"personImageId": alice_world["person"]["id"]},
            "scene": "studio",
            "aspectRatio": "9:16",
        },
        headers=service(BOB),
    )
    assert project.status_code == 404
    assert calls == []


def test_bob_cannot_complete_alices_upload(client, alice_world, factory):
    response = client.post(
        "/api/assets/upload-complete", json={"uploadId": alice_world["upload"]}, headers=service(BOB)
    )
    assert response.status_code == 404
    done = client.post(
        "/api/assets/upload-complete", json={"uploadId": alice_world["upload"]}, headers=service(ALICE)
    )
    assert done.status_code == 200


def test_a_media_link_is_bound_to_its_owners_key(client, alice_world):
    url = alice_world["photo"]["url"].replace("http://testserver", "")
    assert f"/api/media/{ALICE}/" in url
    assert client.get(url).status_code == 200
    forged = url.replace(ALICE, BOB)
    assert client.get(forged).status_code == 403


# --- direct upload --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "payload,status",
    [
        ({"role": "person", "contentType": "image/png", "size": 10 * 1024 * 1024 + 1}, 413),
        ({"role": "product", "contentType": "image/gif", "size": 10}, 415),
        ({"role": "person", "contentType": "video/mp4", "size": 10}, 415),
        ({"role": "source_video", "contentType": "video/mp4", "size": 500 * 1024 * 1024 + 1}, 413),
        ({"role": "source_video", "contentType": "image/png", "size": 10}, 415),
        ({"role": "output_video", "contentType": "video/mp4", "size": 10}, 422),
        ({"role": "person", "contentType": "image/png", "size": 0}, 422),
    ],
)
def test_upload_url_refuses_over_the_limits(client, payload, status):
    response = client.post("/api/assets/upload-url", json=payload, headers=service(ALICE))
    assert response.status_code == status, response.text


def test_upload_url_is_short_lived_and_bound_to_type(client):
    from datetime import UTC, datetime, timedelta

    response = client.post(
        "/api/assets/upload-url",
        json={"role": "source_video", "contentType": "video/mp4", "size": 400 * 1024 * 1024},
        headers=service(ALICE),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["method"] == "PUT"
    assert body["headers"] == {"Content-Type": "video/mp4"}
    expires = datetime.fromisoformat(body["expiresAt"])
    assert expires <= datetime.now(UTC) + timedelta(minutes=15, seconds=5)
    claims = uploads.decode(body["uploadId"])
    assert (claims["u"], claims["r"], claims["c"], claims["s"]) == (
        ALICE,
        "source_video",
        "video/mp4",
        400 * 1024 * 1024,
    )


def test_a_complete_upload_becomes_an_asset_once(client, factory):
    asset = uploaded_asset(client, ALICE)
    assert asset["role"] == "person" and asset["mimeType"] == "image/png"
    with factory() as db:
        stored = db.get(Asset, asset["id"])
        assert stored.user_id == ALICE and stored.source == "try_on"
        assert stored.storage_key.startswith(f"{ALICE}/")
    library = client.get("/api/assets?role=person&source=try_on", headers=service(ALICE)).json()["assets"]
    assert [a["id"] for a in library] == [asset["id"]]


def test_completing_twice_returns_the_same_asset(client):
    body, put = direct_upload(client, ALICE, png())
    assert put.status_code == 204
    first = client.post(
        "/api/assets/upload-complete", json={"uploadId": body["uploadId"]}, headers=service(ALICE)
    )
    again = client.post(
        "/api/assets/upload-complete", json={"uploadId": body["uploadId"]}, headers=service(ALICE)
    )
    assert first.status_code == again.status_code == 200
    assert first.json()["id"] == again.json()["id"]


def test_a_put_after_completion_cannot_replace_the_asset(client, tmp_path):
    body, _ = direct_upload(client, ALICE, png())
    asset = client.post(
        "/api/assets/upload-complete", json={"uploadId": body["uploadId"]}, headers=service(ALICE)
    ).json()
    client.put(
        body["uploadUrl"].replace("http://testserver", ""),
        content=jpeg()[: len(png())],
        headers=body["headers"],
    )
    served = client.get(asset["url"].replace("http://testserver", ""))
    assert served.content == png()


def test_complete_with_a_wrong_size_is_rejected_and_deleted(client, tmp_path):
    data = png()
    body, put = direct_upload(client, ALICE, data, size=len(data) + 10)
    assert put.status_code == 204
    response = client.post(
        "/api/assets/upload-complete", json={"uploadId": body["uploadId"]}, headers=service(ALICE)
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "UPLOAD_SIZE_MISMATCH"
    assert staged_files(tmp_path) == []


def test_complete_with_the_wrong_magic_bytes_is_rejected_and_deleted(client, tmp_path):
    body, put = direct_upload(client, ALICE, jpeg(), content_type="image/png")
    assert put.status_code == 204
    response = client.post(
        "/api/assets/upload-complete", json={"uploadId": body["uploadId"]}, headers=service(ALICE)
    )
    assert response.status_code == 415
    assert staged_files(tmp_path) == []

    fake, put = direct_upload(client, ALICE, b"\x89PNG\r\n\x1a\n" + b"not an image" * 4)
    response = client.post(
        "/api/assets/upload-complete", json={"uploadId": fake["uploadId"]}, headers=service(ALICE)
    )
    assert response.status_code == 415


def test_a_video_upload_with_image_bytes_is_rejected(client):
    body, put = direct_upload(client, ALICE, png(), role="source_video", content_type="video/mp4")
    assert put.status_code == 204
    response = client.post(
        "/api/assets/upload-complete", json={"uploadId": body["uploadId"]}, headers=service(ALICE)
    )
    assert response.status_code == 415


def test_complete_before_the_put_is_refused(client):
    issued = client.post(
        "/api/assets/upload-url",
        json={"role": "person", "contentType": "image/png", "size": 100},
        headers=service(ALICE),
    ).json()
    response = client.post(
        "/api/assets/upload-complete", json={"uploadId": issued["uploadId"]}, headers=service(ALICE)
    )
    assert response.status_code == 409


def test_a_forged_upload_id_is_unknown(client):
    issued = client.post(
        "/api/assets/upload-url",
        json={"role": "person", "contentType": "image/png", "size": 100},
        headers=service(ALICE),
    ).json()
    payload, _, signature = issued["uploadId"].partition(".")
    import base64
    import json

    claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    claims["s"] = 10**9
    forged = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=") + "." + signature
    for upload_id in (forged, "nonsense", issued["uploadId"] + "0"):
        response = client.post(
            "/api/assets/upload-complete", json={"uploadId": upload_id}, headers=service(ALICE)
        )
        assert response.status_code == 404
        assert (
            client.put(
                f"/api/uploads/{upload_id}", content=b"x", headers={"Content-Type": "image/png"}
            ).status_code
            == 404
        )


def test_the_local_put_enforces_type_and_declared_size(client):
    data = png()
    issued = client.post(
        "/api/assets/upload-url",
        json={"role": "person", "contentType": "image/png", "size": len(data) - 1},
        headers=service(ALICE),
    ).json()
    path = issued["uploadUrl"].replace("http://testserver", "")
    assert client.put(path, content=data, headers={"Content-Type": "image/jpeg"}).status_code == 415
    assert client.put(path, content=data, headers={"Content-Type": "image/png"}).status_code == 413


def test_an_expired_upload_is_refused(client, monkeypatch):
    body, put = direct_upload(client, ALICE, png())
    import time

    real = time.time
    monkeypatch.setattr(uploads.time, "time", lambda: real() + uploads.TTL_SECONDS + 60)
    assert (
        client.put(
            body["uploadUrl"].replace("http://testserver", ""), content=png(), headers=body["headers"]
        ).status_code
        == 410
    )
    monkeypatch.setattr(
        uploads.time, "time", lambda: real() + uploads.TTL_SECONDS + uploads.COMPLETE_GRACE_SECONDS + 60
    )
    response = client.post(
        "/api/assets/upload-complete", json={"uploadId": body["uploadId"]}, headers=service(ALICE)
    )
    assert response.status_code == 410


# --- CORS for the Karma origin --------------------------------------------------------------


def test_cors_allows_only_the_karma_origin_and_only_put_and_get(client):
    karma = "https://app.karmaposting.com"
    ok = client.options(
        "/api/uploads/anything", headers={"Origin": karma, "Access-Control-Request-Method": "PUT"}
    )
    assert ok.status_code == 204
    assert ok.headers["access-control-allow-origin"] == karma
    assert ok.headers["access-control-allow-methods"] == "GET, PUT"
    for origin, method in [("https://evil.example", "PUT"), (karma, "DELETE"), (karma, "POST")]:
        refused = client.options(
            "/api/media/x", headers={"Origin": origin, "Access-Control-Request-Method": method}
        )
        assert refused.status_code == 403
    # JSON API routes are server-to-server only.
    api = client.get("/api/profile", headers={"Origin": karma})
    assert "access-control-allow-origin" not in api.headers


def test_s3_cors_rules_cover_put_and_get_for_the_listed_origins():
    from app.storage_cors import cors_configuration

    rules = cors_configuration(["https://app.karmaposting.com"])["CORSRules"]
    assert rules == [
        {
            "AllowedOrigins": ["https://app.karmaposting.com"],
            "AllowedMethods": ["PUT", "GET"],
            "AllowedHeaders": ["Content-Type"],
            "MaxAgeSeconds": 600,
        }
    ]
    with pytest.raises(ValueError):
        cors_configuration([])
