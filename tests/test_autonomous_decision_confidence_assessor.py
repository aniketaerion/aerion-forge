from forge.autonomous_decision.confidence_assessor import (
    assess_confidence,
)
from forge.autonomous_decision.models import (
    CandidateAction,
    DecisionContext,
)
from forge.autonomous_decision.states import (
    CandidateActionKind,
    CandidateSource,
)


def test_matching_step_and_evidence_raise_confidence() -> None:
    context = DecisionContext(
        context_id="context-1",
        mission_id="mission-1",
        session_id="session-1",
        mission_state="executing",
        orchestration_state="ready",
        current_step_id="step-1",
        authority_level="a2_modify",
        approval_state="approved",
        repository_fingerprint="fingerprint-1",
        evidence_references=("evidence-1",),
        policy_version="1.0",
    )
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

    result = assess_confidence(candidate, context)

    assert result.score >= 0.60
    assert "matches_current_step" in result.factors