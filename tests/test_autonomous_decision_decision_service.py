from forge.autonomous_decision.decision_journal import (
    InMemoryDecisionJournal,
)
from forge.autonomous_decision.decision_service import (
    AutonomousDecisionService,
)
from forge.autonomous_decision.models import (
    DecisionContext,
    DecisionRequest,
)
from forge.autonomous_decision.policies import (
    AutonomousDecisionPolicy,
)
from forge.autonomous_decision.replay_guard import (
    DecisionReplayGuard,
)
from forge.autonomous_decision.states import (
    DecisionDisposition,
)


def test_decision_service_selects_supported_next_action() -> None:
    service = AutonomousDecisionService(
        policy=AutonomousDecisionPolicy(),
        journal=InMemoryDecisionJournal(),
        replay_guard=DecisionReplayGuard(),
    )
    request = DecisionRequest(
        request_id="request-1",
        mission_id="mission-1",
        session_id="session-1",
        plan_id="plan-1",
        plan_version=1,
        repository_root="repository",
        requested_by="Aerion",
    )
    context = DecisionContext(
        context_id="context-1",
        mission_id="mission-1",
        session_id="session-1",
        mission_state="executing",
        orchestration_state="step_selecting",
        current_step_id="step-1",
        authority_level="a2_modify",
        approval_state="approved",
        repository_fingerprint="fingerprint-1",
        evidence_references=(
            "evidence-1",
            "evidence-2",
            "evidence-3",
        ),
        policy_version="1.0",
    )

    result = service.decide(request, context)

    assert result.record.selected_candidate_id is not None
    assert result.stop is None
    assert (
        result.record.disposition
        is DecisionDisposition.SELECT_ACTION
    )


def test_decision_service_returns_stop_without_evidence() -> None:
    service = AutonomousDecisionService(
        policy=AutonomousDecisionPolicy(),
        journal=InMemoryDecisionJournal(),
        replay_guard=DecisionReplayGuard(),
    )
    request = DecisionRequest(
        request_id="request-1",
        mission_id="mission-1",
        session_id="session-1",
        plan_id="plan-1",
        plan_version=1,
        repository_root="repository",
        requested_by="Aerion",
    )
    context = DecisionContext(
        context_id="context-1",
        mission_id="mission-1",
        session_id="session-1",
        mission_state="executing",
        orchestration_state="step_selecting",
        current_step_id="step-1",
        authority_level="a2_modify",
        approval_state="approved",
        repository_fingerprint="fingerprint-1",
        policy_version="1.0",
    )

    result = service.decide(request, context)

    assert (
        result.record.disposition
        is DecisionDisposition.NO_SAFE_ACTION
    )
    assert result.stop is not None