"""Deterministic decision selection."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_decision.models import (
    CandidateAction,
    CandidateAssessment,
)
from forge.autonomous_decision.ranking import (
    RankedCandidate,
    rank_candidates,
)
from forge.autonomous_decision.states import (
    CandidateActionKind,
    DecisionDisposition,
)


@dataclass(frozen=True, slots=True)
class SelectionResult:
    """Result of deterministic candidate selection."""

    selected: RankedCandidate | None
    ranked: tuple[RankedCandidate, ...]
    disposition: DecisionDisposition


def disposition_for_candidate(
    candidate: CandidateAction,
) -> DecisionDisposition:
    """Map one candidate action to a committed disposition."""
    mapping = {
        CandidateActionKind.EXECUTE_NEXT_STEP: (
            DecisionDisposition.SELECT_ACTION
        ),
        CandidateActionKind.RETRY_CURRENT_STEP: (
            DecisionDisposition.RETRY
        ),
        CandidateActionKind.ROLLBACK_CURRENT_STEP: (
            DecisionDisposition.ROLLBACK
        ),
        CandidateActionKind.REPLAN_REMAINING_WORK: (
            DecisionDisposition.REPLAN
        ),
        CandidateActionKind.REQUEST_APPROVAL: (
            DecisionDisposition.PAUSE
        ),
        CandidateActionKind.PAUSE_MISSION: (
            DecisionDisposition.PAUSE
        ),
        CandidateActionKind.ESCALATE_MISSION: (
            DecisionDisposition.ESCALATE
        ),
        CandidateActionKind.COMPLETE_MISSION: (
            DecisionDisposition.COMPLETE
        ),
        CandidateActionKind.CANCEL_MISSION: (
            DecisionDisposition.CANCEL
        ),
    }

    return mapping[candidate.action_kind]


def select_candidate(
    candidates: tuple[CandidateAction, ...],
    assessments: tuple[CandidateAssessment, ...],
) -> SelectionResult:
    """Select at most one accepted candidate."""
    ranked = rank_candidates(candidates, assessments)

    if not ranked:
        return SelectionResult(
            selected=None,
            ranked=(),
            disposition=DecisionDisposition.NO_SAFE_ACTION,
        )

    selected = ranked[0]

    return SelectionResult(
        selected=selected,
        ranked=ranked,
        disposition=disposition_for_candidate(
            selected.candidate
        ),
    )