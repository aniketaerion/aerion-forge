from forge.autonomous_decision.models import (
    CandidateAction,
    CandidateAssessment,
)
from forge.autonomous_decision.ranking import rank_candidates
from forge.autonomous_decision.states import (
    CandidateActionKind,
    CandidateSource,
)


def candidate(candidate_id: str) -> CandidateAction:
    return CandidateAction(
        candidate_id=candidate_id,
        action_kind=CandidateActionKind.PAUSE_MISSION,
        description="Pause mission.",
        required_authority="a1_read",
        risk_class="low",
        evidence_references=("evidence-1",),
        source=CandidateSource.ORCHESTRATION_STATE,
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
        utility_score=0.7,
        reversibility_score=0.9,
        total_score=total_score,
    )


def test_higher_score_ranks_first() -> None:
    candidates = (
        candidate("candidate-1"),
        candidate("candidate-2"),
    )
    assessments = (
        assessment(
            "assessment-1",
            "candidate-1",
            0.60,
        ),
        assessment(
            "assessment-2",
            "candidate-2",
            0.80,
        ),
    )

    ranked = rank_candidates(candidates, assessments)

    assert ranked[0].candidate.candidate_id == "candidate-2"
    assert ranked[0].rank == 1