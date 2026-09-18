"""One subscription-backed director validation. Never submits a video or spends video credits."""
import json
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.db import ChatRecipeVersion, SessionLocal
from app.main import app

state = Path('../../.local/creative-director-validation.json')
if state.exists():
    raise SystemExit('Validation already attempted; inspect the existing result instead of repeating.')
state.parent.mkdir(exist_ok=True)
state.write_text(json.dumps({'attempted': True}))
state.chmod(0o600)
with TestClient(app) as client:
    request = 'Zrób naturalny 15-sekundowy UGC Review dla kremu do twarzy. Kobieta pokazuje słoiczek do kamery w jasnej łazience, ciepłe światło dzienne, nagranie telefonem. Krótki polski dialog i zaproszenie do obejrzenia produktu. Bez obietnic efektów. Jedno ciągłe ujęcie.'
    with Path('../web/public/template-styles/ugc-review.png').open('rb') as photo:
        upload = client.post('/api/assets', data={'role': 'product'}, files={'file': ('product.png', photo, 'image/png')})
    upload.raise_for_status()
    assets = {'productImageId': upload.json()['asset']['id']}
    session = client.post('/api/chat/sessions')
    session.raise_for_status()
    sid = session.json()['id']
    response = client.post(f'/api/chat/sessions/{sid}/messages', json={
        'text': request, 'context': {'templateId': 'ugc_review', 'inputAssets': assets, 'duration': 15, 'aspectRatio': '9:16'},
    })
    report = {'attempted': True, 'sessionId': sid, 'httpStatus': response.status_code, 'originalRequest': request}
    if response.is_success:
        answer = response.json()['answer']
        report['answer'] = answer
        if answer.get('videoPlan'):
            assert answer['videoPlan']['duration'] == 15
            assert answer['creativePlan']['spokenLanguage'].split('-')[0] == 'pl'
            assert len(answer['videoPlan']['clips']) == 1
            with SessionLocal() as db:
                version = db.scalar(select(ChatRecipeVersion).where(ChatRecipeVersion.session_id == sid))
                report['planning'] = version.recipe['planning']
            report['validated'] = True
        else:
            report['validated'] = False
    else:
        report['error'] = response.json().get('error')
    state.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps({k: report[k] for k in ('sessionId', 'httpStatus', 'validated') if k in report}))
    response.raise_for_status()
