from forge.autonomous_decision.models import (
    CandidateAction,
    CandidateAssessment,
)
from forge.autonomous_decision.selector import select_candidate
from forge.autonomous_decision.states import (
    CandidateActionKind,
    CandidateSource,
    DecisionDisposition,
)


def candidate(candidate_id: str) -> CandidateAction:
    return CandidateAction(
        candidate_id=candidate_id,
        action_kind=CandidateActionKind.EXECUTE_NEXT_STEP,
        target_step_id="step-1",
        description="Execute step.",
        required_authority="a2_modify",
        risk_class="medium",
        evidence_references=("evidence-1",),
        source=CandidateSource.APPROVED_PLAN,
    )


def assessment(
    assessment_id: str,
    candidate_id: str,
    total_score: float,
) -> CandidateAssessment:
    return CandidateAssessment(
        assessment_id=assessment_id,
        candidate_id=candidate_id,
        feasible=True,
        policy_allowed=True,
        risk_score=0.2,
        confidence_score=0.8,
        evidence_score=0.8,
        utility_score=0.8,
        reversibility_score=0.9,
        total_score=total_score,
    )


def test_selector_picks_highest_ranked_candidate() -> None:
    result = select_candidate(
        (
            candidate("candidate-1"),
            candidate("candidate-2"),
        ),
        (
            assessment("assessment-1", "candidate-1", 0.6),
            assessment("assessment-2", "candidate-2", 0.9),
        ),
    )

    assert result.selected is not None
    assert result.selected.candidate.candidate_id == "candidate-2"
    assert result.disposition is DecisionDisposition.SELECT_ACTION


def test_selector_returns_no_safe_action_without_acceptance() -> None:
    result = select_candidate((), ())

    assert result.selected is None
    assert (
        result.disposition
        is DecisionDisposition.NO_SAFE_ACTION
    )