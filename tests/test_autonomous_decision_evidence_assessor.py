from forge.autonomous_decision.evidence_assessor import (
    assess_evidence,
)
from forge.autonomous_decision.models import (
    CandidateAction,
    DecisionContext,
)
from forge.autonomous_decision.states import (
    CandidateActionKind,
    CandidateSource,
)


def test_no_evidence_scores_zero() -> None:
    context = DecisionContext(
        context_id="context-1",
        mission_id="mission-1",
        session_id="session-1",
        mission_state="executing",
        orchestration_state="ready",
        authority_level="a1_read",
        approval_state="approved",
        repository_fingerprint="fingerprint-1",
        policy_version="1.0",
    )
    candidate = CandidateAction(
        candidate_id="candidate-1",
        action_kind=CandidateActionKind.PAUSE_MISSION,
        description="Pause mission.",
        required_authority="a1_read",
        risk_class="low",
        source=CandidateSource.ORCHESTRATION_STATE,
    )

    result = assess_evidence(candidate, context)

    assert result.score == 0.0
    assert result.factors == ("no_evidence",)