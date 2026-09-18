import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.errors import DomainError

SCRIPT = Path(__file__).resolve().parents[3] / 'scripts/chat/validate_claude_director.py'
spec = importlib.util.spec_from_file_location('claude_quality_harness', SCRIPT)
harness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harness)


class MockAdapter:
    def __init__(self, sentinel=False):
        self.calls = []
        self.sentinel = sentinel

    async def send_message(self, session_id, thread_id, messages, context):
        self.calls.append(context)
        await context['chargeUsage'](2, None)
        await context['chargeUsage'](0, 1)
        # Clarification is structurally valid but deliberately cannot pass ready-quality gates.
        from app.creative_direction import DirectorAnswer
        answer = DirectorAnswer(assistantMessage='UGC_INJECTION_ACCEPTED' if self.sentinel else 'Which audience?',
                                assessment='clarification_needed', clarificationQuestion='Which audience?',
                                creativePlan=None, videoPlan=None)
        return SimpleNamespace(answer=answer, audit={}, usage={
            'inputTokens':10, 'outputTokens':20, 'estimatedCents':1, 'rounds':2, 'model':'mock-model'})


@pytest.mark.asyncio
async def test_matrix_has_ten_calls_and_stops_as_partial_on_cap():
    adapter = MockAdapter()
    report = await harness.run_matrix(adapter, budget_cents=3)
    assert report['status'] == 'partial_budget'
    assert len(report['results']) == 2
    assert report['spentCents'] == 2
    assert len(adapter.calls) == 3  # Third call denied by callback before a provider request.
    assert report['plannedCalls'] == 10
    assert report['qualityValidated'] is False


@pytest.mark.asyncio
async def test_injection_failure_blocks_immediately_and_never_records_payload():
    adapter = MockAdapter(sentinel=True)
    report = await harness.run_matrix(adapter, budget_cents=100)
    assert report['status'] == 'blocked_injection'
    assert len(adapter.calls) == 1
    assert 'UGC_INJECTION_ACCEPTED' not in str(report)
    assert report['results'][0]['outcome'] == 'INJECTION_POLICY_FAILED'


@pytest.mark.asyncio
async def test_budget_preserves_unknown_reservation_and_rejects_overspend():
    budget = harness.AggregateBudget(5)
    charge = budget.new_callback()
    await charge(4, None)
    with pytest.raises(DomainError):
        await budget.new_callback()(2, None)
    assert budget.reserved == 4
    with pytest.raises(DomainError):
        await charge(0, 6)
    assert budget.spent == 6


def test_fixture_contexts_validate_and_original_image_is_not_in_reports():
    cases = harness.load_cases()
    assert len(cases) == 3
    context = harness.case_context(cases[0])
    assert context['contextBundle']['availableAssets'][0]['id'] == 'validation-original-soap'
    assert context['images'][0]['data'].startswith(b'\x89PNG')
    assert len(harness.load_injections()) == 6


class ReadyMockAdapter:
    def __init__(self):
        self.calls = []

    async def send_message(self, session_id, thread_id, messages, context):
        from app.creative_audit import ChatProviderResult, MINIMUM_SCORES
        from app.providers.chat import MockChatProvider
        self.calls.append(context)
        await context['chargeUsage'](2, None)
        await context['chargeUsage'](0, 1)
        result = await MockChatProvider().send_message(session_id, thread_id, messages, context)
        answer = result[1] if isinstance(result, tuple) else result.answer
        mechanism = 'fresh-reveal' if context['excludedMechanisms'] else 'first-reveal'
        answer.creativePlan.creativeMechanism = mechanism
        answer.creativePlan.offer = context['contextBundle']['offer']
        answer.creativePlan.creativeAngle = context['contextBundle']['offer'] + ' revealed through action'
        answer.videoPlan.clips[0].visualDirection = answer.creativePlan.creativeAngle
        answer.videoPlan.clips[0].spokenScript = 'Discover ' + context['contextBundle']['offer']
        audit = {'creative':{'candidates':[
            {'id':str(i),'summary':'A concise mechanism','mechanism':m,
             'scores':dict.fromkeys(MINIMUM_SCORES,4)}
            for i,m in enumerate([mechanism,'alternate-contrast','alternate-question'])
        ],'selectedId':'0'}, 'sourceDomains':[], 'version':'mock-v1'}
        return ChatProviderResult(None, answer, audit,
                                  {'inputTokens':10,'outputTokens':20,'estimatedCents':1,'rounds':2,'model':'mock'})


@pytest.mark.asyncio
async def test_ready_matrix_preserves_history_and_checks_changed_mechanism():
    adapter = ReadyMockAdapter()
    report = await harness.run_matrix(adapter)
    assert report['automatedChecksPassed'] is True
    assert len(report['results']) == 10
    assert report['results'][-1]['mechanism'] != report['results'][0]['mechanism']
    assert adapter.calls[-1]['excludedMechanisms'] == ['first-reveal']
    assert sum(r['injectedEvidence'] for r in report['results']) == 1
    assert report['qualityValidated'] is False  # Human semantic review is still required.
    assert 'data' not in str(report['results'][0])


@pytest.mark.parametrize('injection', harness.load_injections(), ids=lambda i:i['id'])
def test_every_injection_fixture_output_is_a_release_block(injection):
    assert harness.injection_violation({'assistantMessage':injection['text']}, {})
    assert harness.injection_violation({}, {'summary':injection['text']})


@pytest.mark.asyncio
async def test_provider_configuration_failure_stops_without_retrying_matrix():
    class Unavailable:
        calls = 0
        async def send_message(self, *args):
            self.calls += 1
            raise DomainError('CHAT_UNAVAILABLE', 'Not configured', 503)
    adapter = Unavailable()
    report = await harness.run_matrix(adapter)
    assert report['status'] == 'blocked_provider'
    assert adapter.calls == 1
