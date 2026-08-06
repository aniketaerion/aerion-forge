"""Deterministic risk assessment for decision candidates."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_decision.models import (
    CandidateAction,
    DecisionContext,
)
from forge.autonomous_decision.states import CandidateActionKind


@dataclass(frozen=True, slots=True)
class RiskAssessment:
    """Normalized risk score and explainable factors."""

    score: float
    factors: tuple[str, ...]


_RISK_CLASS_SCORES = {
    "low": 0.20,
    "medium": 0.50,
    "high": 0.80,
    "critical": 1.00,
}


def assess_risk(
    candidate: CandidateAction,
    context: DecisionContext,
) -> RiskAssessment:
    """Assess candidate risk using explicit bounded factors."""
    score = _RISK_CLASS_SCORES.get(
        candidate.risk_class.casefold(),
        1.0,
    )
    factors: list[str] = [
        f"risk_class={candidate.risk_class.casefold()}"
    ]

    if not candidate.reversible:
        score += 0.15
        factors.append("irreversible")

    if candidate.approval_required:
        score += 0.05
        factors.append("approval_required")

    if candidate.target_step_id in context.failed_step_ids:
        score += 0.10
        factors.append("targets_failed_step")

    if candidate.action_kind in {
        CandidateActionKind.ROLLBACK_CURRENT_STEP,
        CandidateActionKind.CANCEL_MISSION,
    }:
        score += 0.10
        factors.append("destructive_or_terminal_action")

    if context.unresolved_findings:
        score += min(
            0.15,
            len(context.unresolved_findings) * 0.03,
        )
        factors.append("unresolved_findings")

    return RiskAssessment(
        score=round(min(score, 1.0), 6),
        factors=tuple(factors),
    )