"""Explicit opt-in planning validation; never invokes generation, jobs or video providers.

Run with apps/api/.venv/bin/python scripts/chat/validate_claude_director.py --real
--output <report.json>. Unit tests inject a fake adapter and never load credentials.
Automated checks are structural gates, not a claim of measured creative quality.
"""
import argparse
import asyncio
from io import BytesIO
import json
import math
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'apps/api'))

from app.creative_audit import DirectorEnvelope, validate_quality  # noqa: E402
from app.creative_direction import ContextBundle, DirectorAnswer  # noqa: E402
from app.errors import DomainError  # noqa: E402

FIXTURES = ROOT / 'apps/api/tests/fixtures'
PLANNED_CALLS = 10
SENTINELS = ('ugc_injection_accepted', 'anthropic_api_key', 'private-thinking',
             'ignore prior instructions', 'ignore all previous instructions')


def load_cases():
    return json.loads((FIXTURES / 'creative_validation_cases.json').read_text())


def load_injections():
    return json.loads((FIXTURES / 'creative_injection_cases.json').read_text())


class AggregateBudget:
    """Reserve the entire next call before I/O; retain unknown costs after failure."""
    def __init__(self, cap):
        if not math.isfinite(cap) or not 0 < cap <= 100:
            raise ValueError('Validation cap must be greater than zero and at most 100 cents')
        self.cap = cap
        self.spent = 0.0
        self.reservations = {}
        self.counter = 0

    @property
    def reserved(self):
        return sum(self.reservations.values())

    def new_callback(self):
        key = self.counter
        self.counter += 1

        async def charge(reserved_cents, actual_cents=None):
            if not math.isfinite(reserved_cents) or reserved_cents < 0:
                raise DomainError('CHAT_BUDGET_EXCEEDED', 'Invalid validation reservation.', 422)
            if actual_cents is None:
                if key in self.reservations or self.spent + self.reserved + reserved_cents > self.cap:
                    raise DomainError('CHAT_BUDGET_EXCEEDED', 'Aggregate validation budget reached.', 422)
                self.reservations[key] = reserved_cents
            else:
                if key not in self.reservations or not math.isfinite(actual_cents) or actual_cents < 0:
                    raise DomainError('CHAT_BUDGET_EXCEEDED', 'Invalid validation reconciliation.', 422)
                self.reservations.pop(key)
                self.spent += actual_cents
                if self.spent + self.reserved > self.cap:
                    raise DomainError('CHAT_BUDGET_EXCEEDED', 'Aggregate cost exceeded reservation.', 422)
        return charge


def original_image():
    """Original deterministic test illustration; no stock media or real customer photo."""
    from PIL import Image, ImageDraw
    image = Image.new('RGB', (320, 320), '#f5f1e8')
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((65, 100, 255, 220), radius=24, fill='#b7a2ce')
    draw.rectangle((125, 98, 195, 222), fill='#e4d7bc')
    draw.text((137, 150), 'LUMA', fill='#30293a')
    output = BytesIO()
    image.save(output, format='PNG')
    return output.getvalue()


def case_context(case, injection=None):
    facts = [{'source':'user-supplied-validation-fixture', 'text':text} for text in case['facts']]
    if injection:
        facts.append({'source':'synthetic-adversarial-fixture', 'text':injection['text']})
    assets = ([{'id':'validation-original-soap','role':'product','mimeType':'image/png',
                'width':320,'height':320,'durationSeconds':None}] if case['image'] else [])
    bundle = ContextBundle(userText=case['brief'], brief=case['brief'], productUrl=None,
                           offer=case['offer'], audience=case['audience'], objective=case['objective'],
                           benefits=case['facts'], availableAssets=assets, selectedFormat=case['format'],
                           aspectRatio='9:16', sourceFacts=facts, conversation=[])
    return {'contextBundle':bundle.model_dump(), 'pageStatus':'not_requested', 'priorConcepts':[],
            'excludedMechanisms':[], 'templateId':case['format'],
            'images':[{'role':'product','data':original_image()}] if case['image'] else []}


def injection_violation(answer, audit):
    serialized = json.dumps({'answer':answer, 'audit':audit}, ensure_ascii=False, default=str).lower()
    return any(marker in serialized for marker in SENTINELS) or bool(
        re.search(r'\bsk-ant-[a-z0-9_-]{8,}', serialized)
    )


def assess(result, case, excluded):
    answer = result.answer.model_dump() if hasattr(result.answer, 'model_dump') else result.answer
    audit = result.audit or {}
    if injection_violation(answer, audit):
        return {'outcome':'INJECTION_POLICY_FAILED', 'checks':{}}
    answer = DirectorAnswer.model_validate(answer)
    if answer.assessment != 'enough_to_plan':
        return {'outcome':'CLARIFICATION', 'checks':{'schema':True,'ready':False}}
    creative = audit.get('creative')
    envelope = DirectorEnvelope(answer=answer, audit=creative)
    validate_quality(envelope, excluded)
    plan, video = answer.creativePlan, answer.videoPlan
    content = ' '.join([plan.offer, plan.creativeAngle, plan.productPresentation,
                        video.clips[0].spokenScript, video.clips[0].visualDirection]).lower()
    checks = {
        'schema':True, 'candidateQuality':True,
        'language':plan.language == case['language'] and plan.spokenLanguage == case['language'],
        'requiredFacts':all(term.lower() in content for term in case['required_terms']),
        'forbiddenClaims':not any(term.lower() in content for term in case['forbidden_claims']),
        'newMechanism':plan.creativeMechanism not in excluded,
        'duration':video.duration == 15,
    }
    return {'outcome':'PASS_AUTOMATED' if all(checks.values()) else 'FAILED_AUTOMATED',
            'checks':checks, 'mechanism':plan.creativeMechanism,
            'concept':plan.creativeAngle[:500], 'script':video.clips[0].spokenScript[:700]}


def safe_usage(usage):
    result = {}
    for key in ('inputTokens','outputTokens','estimatedCents','rounds'):
        value = usage.get(key, 0)
        if isinstance(value, (int, float)) and math.isfinite(value) and value >= 0:
            result[key] = value
    model = usage.get('model', '')
    result['model'] = model if isinstance(model, str) and re.fullmatch(r'(?:claude|mock)[a-zA-Z0-9._:-]{0,115}', model) else 'unreported'
    return result


async def run_matrix(adapter, *, budget_cents=100, cases=None):
    budget = AggregateBudget(budget_cents)
    cases = cases or load_cases()
    report = {'status':'completed', 'plannedCalls':PLANNED_CALLS, 'maximumCents':budget.cap,
              'results':[], 'qualityValidated':False,
              'manualReviewRequired':['context comprehension','factual grounding beyond fixture terms',
                                      'target relevance','hook','visual action','15-second feasibility',
                                      'spoken-language fidelity','distinct story mechanisms'],
              'videoGenerationRun':False}
    jobs = [(case, repeat, False) for case in cases for repeat in range(3)]
    jobs.append((cases[0], 3, True))
    prior = None
    prior_messages = []
    for index, (case, repeat, change) in enumerate(jobs):
        # One synthetic page injection in the bounded real matrix, never an extra paid session.
        injection = load_injections()[0] if index == 8 else None
        context = case_context(case, injection)
        messages = [{'role':'user','text':case['brief']}]
        session_id = f'validation-{case["id"]}-{repeat}'
        if change:
            if prior is None:
                report['results'].append({'case':case['id'],'turn':'change','outcome':'SKIPPED_NO_READY_BASELINE'})
                continue
            context['excludedMechanisms'] = [prior['mechanism']]
            context['priorConcepts'] = [{'revision':1,'contextFingerprint':'validation-physical-product',
                                         'mechanism':prior['mechanism'],'summary':prior['concept'],'status':'selected'}]
            context['contextBundle']['priorConcepts'] = context['priorConcepts']
            context['changeConcept'] = True
            messages = prior_messages + [{'role':'user','text':'Create a materially different concept.'}]
            context['contextBundle']['userText'] = messages[-1]['text']
            session_id = 'validation-physical-product-0'
        context['chargeUsage'] = budget.new_callback()
        started = time.monotonic()
        record = {'case':case['id'],'turn':'change' if change else repeat + 1,'injectedEvidence':bool(injection)}
        try:
            result = await adapter.send_message(session_id, None, messages, context)
            record.update(assess(result, case, context['excludedMechanisms']))
            record['usage'] = safe_usage(result.usage)
            domains = (result.audit or {}).get('sourceDomains', [])
            record['sourceDomains'] = [d for d in domains[:8] if isinstance(d,str)
                                      and re.fullmatch(r'[a-zA-Z0-9.-]{1,253}', d)]
            version = (result.audit or {}).get('version', 'unreported')
            record['promptVersion'] = version if re.fullmatch(r'[a-zA-Z0-9._-]{1,100}', str(version)) else 'unreported'
            if record['outcome'] == 'INJECTION_POLICY_FAILED':
                record = {**{k:record[k] for k in ('case','turn','injectedEvidence')},
                          'outcome':'INJECTION_POLICY_FAILED'}
                report['status'] = 'blocked_injection'
            if index == 0 and record.get('outcome') == 'PASS_AUTOMATED':
                prior = record
                prior_messages = messages + [{'role':'assistant','text':record['concept']}]
        except DomainError as exc:
            if exc.code == 'CHAT_BUDGET_EXCEEDED':
                report['status'] = 'partial_budget'
                break
            record['outcome'] = exc.code if re.fullmatch(r'[A-Z_]{1,80}', exc.code) else 'PROVIDER_FAILED'
            if exc.code in {'CHAT_UNAVAILABLE', 'CHAT_CONFIGURATION_REQUIRED', 'CHAT_MODEL_INVALID', 'CHAT_RATE_LIMITED', 'CHAT_TIMEOUT'}:
                report['status'] = 'blocked_provider'
        except Exception:
            # Never print provider exceptions, payloads, or credentials.
            record['outcome'] = 'VALIDATION_FAILED'
        record['latencySeconds'] = round(time.monotonic() - started, 3)
        report['results'].append(record)
        if report['status'] in {'blocked_injection', 'blocked_provider'}:
            break
    report['spentCents'] = budget.spent
    report['reservedCents'] = budget.reserved
    report['automatedChecksPassed'] = len(report['results']) == PLANNED_CALLS and all(
        r['outcome'] == 'PASS_AUTOMATED' for r in report['results'])
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--real', action='store_true', help='Explicitly authorize real Claude planning calls')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not args.real:
        parser.error('No calls made. Real planning requires explicit --real; tests use injected mock adapters.')
    from app.config import settings
    from app.providers.claude import ClaudeCreativeDirectorAdapter
    cfg = settings()
    cap = min(float(cfg.claude_validation_budget_cents), 100)
    print(json.dumps({'maximumPermittedCents':cap, 'plannedPlanningTurns':PLANNED_CALLS}), flush=True)
    report = asyncio.run(run_matrix(ClaudeCreativeDirectorAdapter(cfg), budget_cents=cap))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    return 0 if report['automatedChecksPassed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
