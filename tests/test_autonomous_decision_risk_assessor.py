from forge.autonomous_decision.models import (
    CandidateAction,
    DecisionContext,
)
from forge.autonomous_decision.risk_assessor import assess_risk
from forge.autonomous_decision.states import (
    CandidateActionKind,
    CandidateSource,
)


def context() -> DecisionContext:
    return DecisionContext(
        context_id="context-1",
        mission_id="mission-1",
        session_id="session-1",
        mission_state="executing",
        orchestration_state="ready",
        authority_level="a2_modify",
        approval_state="approved",
        repository_fingerprint="fingerprint-1",
        evidence_references=("evidence-1",),
        policy_version="1.0",
    )


def test_irreversible_high_risk_action_scores_high() -> None:
    candidate = CandidateAction(
        candidate_id="candidate-1",
        action_kind=CandidateActionKind.CANCEL_MISSION,
        description="Cancel mission.",
        required_authority="a2_modify",
        risk_class="high",
        reversible=False,
        evidence_references=("evidence-1",),
        source=CandidateSource.ORCHESTRATION_STATE,
    )

    result = assess_risk(candidate, context())

    assert result.score == 1.0
    assert "irreversible" in result.factors