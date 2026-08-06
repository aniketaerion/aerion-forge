"""Deterministic confidence assessment."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_decision.models import (
    CandidateAction,
    DecisionContext,
)


@dataclass(frozen=True, slots=True)
class ConfidenceAssessment:
    """Normalized confidence score and rationale."""

    score: float
    factors: tuple[str, ...]


def assess_confidence(
    candidate: CandidateAction,
    context: DecisionContext,
) -> ConfidenceAssessment:
    """Assess confidence from evidence and state consistency."""
    score = 0.40
    factors: list[str] = ["base_confidence"]

    evidence_count = len(
        set(candidate.evidence_references)
        | set(context.evidence_references)
    )
    if evidence_count:
        score += min(0.30, evidence_count * 0.05)
        factors.append(f"evidence_count={evidence_count}")
    else:
        score -= 0.20
        factors.append("no_evidence")

    if candidate.target_step_id is not None:
        if candidate.target_step_id == context.current_step_id:
            score += 0.15
            factors.append("matches_current_step")
        elif candidate.target_step_id in context.failed_step_ids:
            score += 0.10
            factors.append("matches_failed_step")
        else:
            score -= 0.15
            factors.append("step_context_mismatch")

    if context.unresolved_findings:
        score -= min(
            0.20,
            len(context.unresolved_findings) * 0.04,
        )
        factors.append("unresolved_findings")

    if context.approval_state == "approved":
        score += 0.05
        factors.append("approved_context")

    return ConfidenceAssessment(
        score=round(max(0.0, min(score, 1.0)), 6),
        factors=tuple(factors),
    )