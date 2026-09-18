"""Optional development relay: signed media GET only, no app/API/auth routes.

Expose ONLY this loopback service through a temporary tunnel, never the development API.
The allowlist is a JSON array of storage keys in STORYFLOW_MEDIA_ALLOWLIST.
"""

import json
import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from app.config import settings
from app.services.storage import Storage
from app.errors import DomainError

app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)


@app.get("/api/media/{key:path}")
def media(key: str, expires: int, signature: str):
    if settings().app_env != "development" or settings().storage_mode != "local":
        raise HTTPException(404)
    allowed = json.loads(os.environ.get("STORYFLOW_MEDIA_ALLOWLIST", "[]"))
    if key not in allowed:
        raise HTTPException(404)
    try:
        path = Storage().verify(key, expires, signature)
    except DomainError:
        raise HTTPException(403) from None
    if not path.is_file():
        raise HTTPException(404)
    return FileResponse(path, headers={"Cache-Control": "private, no-store"})
