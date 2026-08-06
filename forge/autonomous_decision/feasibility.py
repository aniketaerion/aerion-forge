"""Candidate feasibility evaluation."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_decision.models import (
    CandidateAction,
    DecisionContext,
)
from forge.autonomous_decision.states import (
    CandidateActionKind,
    CandidateRejectionReason,
)


@dataclass(frozen=True, slots=True)
class FeasibilityResult:
    """Feasibility result for one candidate."""

    feasible: bool
    rejection_reasons: tuple[CandidateRejectionReason, ...]
    warnings: tuple[str, ...] = ()


def evaluate_feasibility(
    candidate: CandidateAction,
    context: DecisionContext,
) -> FeasibilityResult:
    """Evaluate structural feasibility without scoring."""
    reasons: list[CandidateRejectionReason] = []
    warnings: list[str] = []

    if any(
        not dependency.strip()
        for dependency in candidate.dependencies
    ):
        reasons.append(
            CandidateRejectionReason.MISSING_DEPENDENCY
        )

    if (
        candidate.target_step_id is not None
        and candidate.target_step_id
        in context.completed_step_ids
    ):
        reasons.append(
            CandidateRejectionReason.COMPLETED_STEP_REPLAY
        )

    if (
        candidate.action_kind
        is CandidateActionKind.RETRY_CURRENT_STEP
        and candidate.target_step_id
        not in context.failed_step_ids
    ):
        reasons.append(CandidateRejectionReason.INFEASIBLE)

    if (
        candidate.action_kind
        is CandidateActionKind.ROLLBACK_CURRENT_STEP
        and candidate.target_step_id is None
    ):
        reasons.append(CandidateRejectionReason.INFEASIBLE)

    if (
        candidate.action_kind
        is CandidateActionKind.COMPLETE_MISSION
        and (
            context.current_step_id is not None
            or context.failed_step_ids
            or context.unresolved_findings
        )
    ):
        reasons.append(CandidateRejectionReason.INFEASIBLE)

    if not candidate.evidence_references:
        warnings.append("Candidate has no supporting evidence.")

    return FeasibilityResult(
        feasible=not reasons,
        rejection_reasons=tuple(dict.fromkeys(reasons)),
        warnings=tuple(warnings),
    )