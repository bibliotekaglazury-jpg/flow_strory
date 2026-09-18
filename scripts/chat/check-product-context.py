"""One local subscription-backed image/chat check; never submits video."""
from pathlib import Path
import json

from fastapi.testclient import TestClient

from app.main import app
from app.services import chat

adapter = chat.provider()
send = adapter.send_message


async def checked_send(*args):
    try:
        return await send(*args)
    except Exception as error:
        # Only our fixed internal validation errors; never raw provider events.
        print("Adapter error type:", type(error).__name__)
        if type(error) is ValueError:
            print("Validation:", str(error))
        raise


adapter.send_message = checked_send


with TestClient(app) as client:
    photo = Path("../web/public/template-styles/ugc-review.png")
    with photo.open("rb") as image:
        upload = client.post("/api/assets", data={"role": "product"}, files={"file": ("product.png", image, "image/png")})
    upload.raise_for_status()
    asset = upload.json()["asset"]
    session = client.post("/api/chat/sessions")
    session.raise_for_status()
    session_id = session.json()["id"]
    result = client.post(f"/api/chat/sessions/{session_id}/messages", json={
        "text": "Obejrzyj załączone zdjęcie. Powiedz, co faktycznie widzisz. Przygotuj naturalny UGC Review po polsku dla widocznego produktu, 15 sekund. Nie szukaj w sieci na potrzeby tego testu.",
        "context": {"templateId": "ugc_review", "inputAssets": {"productImageId": asset["id"]}, "duration": 15, "aspectRatio": "9:16"},
    })
    print(json.dumps({"status": result.status_code, "sessionId": session_id, "answer": result.json().get("answer"), "error": result.json().get("error")}, ensure_ascii=False))
    result.raise_for_status()
    if result.json()["answer"]["needsMoreInformation"]:
        result = client.post(f"/api/chat/sessions/{session_id}/messages", json={
            "text": "To krem do twarzy. Pokaż kosmetyk jako prosty element codziennego rytuału. Przygotuj teraz gotowy plan po polsku bez dalszych pytań, nie używaj wyszukiwarki.",
            "context": {"templateId": "ugc_review", "inputAssets": {"productImageId": asset["id"]}, "duration": 15, "aspectRatio": "9:16"},
        })
        result.raise_for_status()
        answer = result.json()["answer"]
        assert answer["recipe"]["language"].split("-")[0] == "pl"
        assert answer["recipe"]["duration"] == 15
        print(json.dumps({"continued": True, "answer": answer}, ensure_ascii=False))
