from forge.autonomous_decision.candidate_generator import (
    generate_candidates,
)
from forge.autonomous_decision.models import (
    DecisionContext,
    DecisionRequest,
)
from forge.autonomous_decision.policies import (
    AutonomousDecisionPolicy,
)
from forge.autonomous_decision.states import (
    CandidateActionKind,
)


def request() -> DecisionRequest:
    return DecisionRequest(
        request_id="request-1",
        mission_id="mission-1",
        session_id="session-1",
        plan_id="plan-1",
        plan_version=1,
        repository_root="repository",
        requested_by="Aerion",
    )


def context() -> DecisionContext:
    return DecisionContext(
        context_id="context-1",
        mission_id="mission-1",
        session_id="session-1",
        mission_state="executing",
        orchestration_state="step_selecting",
        current_step_id="step-1",
        authority_level="a2_modify",
        approval_state="approved",
        repository_fingerprint="fingerprint-1",
        evidence_references=("evidence-1",),
        policy_version="1.0",
    )


def test_generator_produces_bounded_candidates() -> None:
    result = generate_candidates(
        request(),
        context(),
        AutonomousDecisionPolicy(),
    )

    assert len(result.candidates) <= 20
    assert any(
        candidate.action_kind
        is CandidateActionKind.EXECUTE_NEXT_STEP
        for candidate in result.candidates
    )


def test_failed_step_generates_recovery_candidates() -> None:
    failed_context = context().model_copy(
        update={"failed_step_ids": ("step-1",)}
    )

    result = generate_candidates(
        request(),
        failed_context,
        AutonomousDecisionPolicy(),
    )

    kinds = {
        candidate.action_kind
        for candidate in result.candidates
    }

    assert CandidateActionKind.RETRY_CURRENT_STEP in kinds
    assert CandidateActionKind.ROLLBACK_CURRENT_STEP in kinds
    assert CandidateActionKind.REPLAN_REMAINING_WORK in kinds