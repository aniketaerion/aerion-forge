from forge.autonomous_decision.deduplication import (
    deduplicate_candidates,
)
from forge.autonomous_decision.models import CandidateAction
from forge.autonomous_decision.states import (
    CandidateActionKind,
    CandidateRejectionReason,
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


def test_semantic_duplicates_are_rejected() -> None:
    result = deduplicate_candidates(
        (candidate("candidate-2"), candidate("candidate-1"))
    )

    assert len(result.candidates) == 1
    assert result.rejected == (
        (
            "candidate-2",
            CandidateRejectionReason.DUPLICATE,
        ),
    )