from forge.autonomous_decision.feasibility import (
    evaluate_feasibility,
)
from forge.autonomous_decision.models import (
    CandidateAction,
    DecisionContext,
)
from forge.autonomous_decision.states import (
    CandidateActionKind,
    CandidateRejectionReason,
    CandidateSource,
)


def context() -> DecisionContext:
    return DecisionContext(
        context_id="context-1",
        mission_id="mission-1",
        session_id="session-1",
        mission_state="executing",
        orchestration_state="ready",
        completed_step_ids=("step-1",),
        authority_level="a2_modify",
        approval_state="approved",
        repository_fingerprint="fingerprint-1",
        evidence_references=("evidence-1",),
        policy_version="1.0",
    )


def test_completed_step_replay_is_infeasible() -> None:
    candidate = CandidateAction(
        candidate_id="candidate-1",
        action_kind=CandidateActionKind.EXECUTE_NEXT_STEP,
        target_step_id="step-1",
        description="Execute step.",
        required_authority="a2_modify",
        risk_class="medium",
        evidence_references=("evidence-1",),
        source=CandidateSource.APPROVED_PLAN,
    )

    result = evaluate_feasibility(candidate, context())

    assert not result.feasible
    assert (
        CandidateRejectionReason.COMPLETED_STEP_REPLAY
        in result.rejection_reasons
    )