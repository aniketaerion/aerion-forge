"""Expected-utility and reversibility assessment."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_decision.models import CandidateAction
from forge.autonomous_decision.states import CandidateActionKind


@dataclass(frozen=True, slots=True)
class UtilityAssessment:
    """Normalized utility and reversibility scores."""

    utility_score: float
    reversibility_score: float
    factors: tuple[str, ...]


_BASE_UTILITY = {
    CandidateActionKind.EXECUTE_NEXT_STEP: 0.85,
    CandidateActionKind.RETRY_CURRENT_STEP: 0.65,
    CandidateActionKind.ROLLBACK_CURRENT_STEP: 0.45,
    CandidateActionKind.REPLAN_REMAINING_WORK: 0.60,
    CandidateActionKind.REQUEST_APPROVAL: 0.50,
    CandidateActionKind.PAUSE_MISSION: 0.35,
    CandidateActionKind.ESCALATE_MISSION: 0.40,
    CandidateActionKind.COMPLETE_MISSION: 1.00,
    CandidateActionKind.CANCEL_MISSION: 0.10,
}


def assess_utility(
    candidate: CandidateAction,
) -> UtilityAssessment:
    """Assess expected mission utility and reversibility."""
    utility = _BASE_UTILITY[candidate.action_kind]
    factors: list[str] = [
        f"action={candidate.action_kind.value}"
    ]

    utility -= min(0.30, candidate.expected_cost * 0.05)
    if candidate.expected_cost:
        factors.append(
            f"expected_cost={candidate.expected_cost}"
        )

    if not candidate.expected_effects:
        utility -= 0.15
        factors.append("no_expected_effects")

    reversibility = 0.90 if candidate.reversible else 0.10
    factors.append(
        "reversible"
        if candidate.reversible
        else "irreversible"
    )

    return UtilityAssessment(
        utility_score=round(
            max(0.0, min(utility, 1.0)),
            6,
        ),
        reversibility_score=reversibility,
        factors=tuple(factors),
    )