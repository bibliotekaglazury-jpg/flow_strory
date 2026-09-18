import hashlib
import hmac
import json
import time

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import Base, WebhookEvent
from app.errors import DomainError
from app.services.billing import apply_event, verify_event


def test_webhook_signature_required_and_validated(monkeypatch):
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")
    settings.cache_clear()
    body = json.dumps({"id": "evt_test", "type": "ignored", "data": {"object": {}}}).encode()
    timestamp = int(time.time())
    signature = hmac.new(b"whsec_test", str(timestamp).encode() + b"." + body, hashlib.sha256).hexdigest()
    assert verify_event(body, f"t={timestamp},v1={signature}")["id"] == "evt_test"
    with pytest.raises(DomainError):
        verify_event(body + b" ", f"t={timestamp},v1={signature}")
    settings.cache_clear()


def test_duplicate_event_is_recorded_once():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    event = {"id": "evt_duplicate", "type": "ignored", "data": {"object": {}}}
    with Session(engine) as db:
        apply_event(db, event, b"payload")
        apply_event(db, event, b"payload")
        assert len(list(db.scalars(select(WebhookEvent)))) == 1
