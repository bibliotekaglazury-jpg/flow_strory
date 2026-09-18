"""Explicit one-submission local smoke harness. Run from apps/api with its venv.
prepare: owned test images + schema-valid fixed Polish plan (NOT a real chat test).
submit: existing quote/job admission; guard file prevents repeat submission.
poll: existing worker process for just this admitted job; never retries submission.
"""
import asyncio
import json
import os
from pathlib import Path
import sys
import time
from uuid import uuid4
from sqlalchemy import select
from fastapi.testclient import TestClient
from app.config import settings
from app.db import SessionLocal, Job, Prompt, now
from app.main import app
from app.schemas import Creative
from app.services.assets import store_asset
from app.services.storage import Storage
from app.services.prompts import fingerprint
from app.video_recipe import VideoRecipe, compile_recipe
from app.worker import process

ROOT=Path(__file__).resolve().parents[2]
STATE=Path(os.environ.get("STORYFLOW_SMOKE_STATE", ROOT/'.local/single-video-smoke.json'))
USER='development-user'
if settings().app_env!='development' or settings().auth_mode!='mock':
    raise SystemExit('Local mock-auth harness only')
mode=sys.argv[1]
if mode=='prepare':
    if STATE.exists(): raise SystemExit('Existing smoke state; inspect instead of creating another paid test')
    photo=ROOT/'apps/web/public/template-styles/ugc-review.png'
    with SessionLocal.begin() as db:
        assets=[store_asset(db,Storage(),USER,role,photo.read_bytes(),'owned-ugc-'+role+'.png') for role in ('product','person')]
        recipe=VideoRecipe.model_validate(dict(language='pl',spokenContent=dict(required=True,language='pl',dialogue='To krem, który dziś chcę wam pokazać. Spójrzcie na opakowanie i jego prostą formę. Jeśli chcecie dowiedzieć się więcej, zajrzyjcie na stronę produktu.'),
            intent='ugc_product_ad',concept='Naturalne 15-sekundowe UGC kremu do twarzy po polsku.',duration=15,aspectRatio='9:16',qualityTier='auto',
            subject='The same adult woman in the supplied reference photograph. Preserve her face and identity.',
            product='The same plain pale cream jar held by the woman in the supplied reference. Preserve its shape, lid, color and blank label; invent no brand.',
            visualStyle='Authentic smartphone recording in a home, warm soft window daylight, realistic skin and neutral colors.',
            camera='One continuous steady handheld medium close-up. No cuts, no zooms, no camera orbit.',
            performance='Relaxed friendly natural Polish delivery, she holds the jar near her face then moves it slightly toward camera without opening it.',
            scenes=[dict(duration=15,description='Woman looks at the camera and speaks the supplied Polish dialogue at a comfortable pace. Keep jar fully visible, small natural hand movements; finish with a relaxed smile.')],
            audio='Native synchronized Polish female speech, quiet room ambience. No background music. Complete the dialogue naturally within 15 seconds.',
            constraints=['Preserve person identity','Preserve product appearance','Keep packaging stable','Single continuous 15-second take'],
            negativeRules=['No distorted hands','No product deformation','No face morphing','No language switching','No subtitles','No unsupported product claims']))
        creative=Creative(inputAssets={'productImageId':assets[0].id,'personImageId':assets[1].id},templateId='ugc_review',brief=recipe.concept,duration=15,aspectRatio='9:16',language='pl')
        prompt=Prompt(user_id=USER,snapshot=creative.model_dump(),fingerprint=fingerprint(creative.model_dump()),text=compile_recipe(recipe,{'references':['first image: product jar','second image: same creator']}),recipe=recipe.model_dump())
        db.add(prompt);db.flush()
        state={'creative':creative.model_dump(),'promptId':prompt.id,'prompt':prompt.text,'keys':[a.storage_key for a in assets],'idempotencyKey':'one-native-smoke-'+str(uuid4()),'chatValidation':'blocked: OpenAI key transfer awaiting approval; fixed schema-valid test recipe'}
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2));STATE.chmod(0o600)
    print(json.dumps({'prepared':True,'assetKeys':state['keys']}))
else:
    state=json.loads(STATE.read_text())
    if mode=='submit':
        if state.get('submitAttempted'):raise SystemExit('One paid-test attempt already recorded; polling only')
        with TestClient(app) as client:
            c=state['creative'];estimate={k:v for k,v in c.items() if k not in ('brief','language')}
            estimate.update(promptId=state['promptId'],model='auto',voice='auto',quality='auto')
            quote=client.get('/api/credits',params={'estimate':json.dumps(estimate)})
            if quote.status_code!=200:raise SystemExit('Quote rejected: '+str(quote.status_code)+' '+quote.text)
            state.update(submitAttempted=True,startedAt=time.time(),creditsEstimated=quote.json()['quote']['creditsEstimated'])
            STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2))
            body=c|{'promptId':state['promptId'],'prompt':state['prompt'],'model':'auto','voice':'auto','quality':'auto','quoteId':quote.json()['quote']['id']}
            result=client.post('/api/generations',json=body,headers={'Idempotency-Key':state['idempotencyKey']})
            if result.status_code!=202:raise SystemExit('Admission rejected: '+str(result.status_code)+' '+result.text)
            state['generationId']=result.json()['generation']['id']
            STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2))
            print(json.dumps({'generationId':state['generationId'],'creditsEstimated':state['creditsEstimated']}))
    elif mode=='poll':
        with SessionLocal.begin() as db:
            job=db.scalar(select(Job).where(Job.generation_id==state['generationId']).with_for_update())
            if job.submission_state not in ('done','reconciliation'):
                job.lease_owner='single-smoke';job.lease_until=now();job.attempts+=1
                jobid=job.id
            else:jobid=None
        if jobid:asyncio.run(process(jobid,'single-smoke'))
        with SessionLocal() as db:
            job=db.scalar(select(Job).where(Job.generation_id==state['generationId']))
            state.update(providerRequestId=job.provider_job_id,jobState=job.submission_state)
        with TestClient(app) as client:
            result=client.get('/api/generations/'+state['generationId']).json()['generation']
            state.update(status=result['status'],elapsedSeconds=round(time.time()-state['startedAt'],2),creditsCharged=result['creditsCharged'],error=result['error'])
            if result['status']=='completed':
                history=client.get('/api/generations').json()['generations']
                state['historyVerified']=any(g['id']==state['generationId'] for g in history)
                state['outputAssets']=[{k:v for k,v in a.items() if k not in ('url','urlExpiresAt')} for a in result['outputAssets']]
        STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2))
        print(json.dumps({k:state.get(k) for k in ('generationId','providerRequestId','jobState','status','elapsedSeconds','creditsCharged','error','historyVerified')}))
    else: raise SystemExit('prepare|submit|poll only')
