"""Structured decision rationale generation."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_decision.models import (
    CandidateAssessment,
    DecisionContext,
)
from forge.autonomous_decision.ranking import RankedCandidate
from forge.autonomous_decision.states import DecisionDisposition


@dataclass(frozen=True, slots=True)
class DecisionRationale:
    """Human-readable and structured decision explanation."""

    summary: str
    factors: tuple[str, ...]
    rejected_alternatives: tuple[str, ...]


def build_rationale(
    *,
    context: DecisionContext,
    disposition: DecisionDisposition,
    selected: RankedCandidate | None,
    assessments: tuple[CandidateAssessment, ...],
) -> DecisionRationale:
    """Build deterministic rationale from assessments."""
    rejected = tuple(
        sorted(
            assessment.candidate_id
            for assessment in assessments
            if assessment.rejection_reasons
        )
    )

    if selected is None:
        return DecisionRationale(
            summary=(
                "No candidate satisfied feasibility, policy, "
                "risk, confidence, evidence, and utility constraints."
            ),
            factors=(
                f"context={context.context_id}",
                f"disposition={disposition.value}",
                f"rejected_candidates={len(rejected)}",
            ),
            rejected_alternatives=rejected,
        )

    assessment = selected.assessment

    factors = (
        f"context={context.context_id}",
        f"candidate={selected.candidate.candidate_id}",
        f"rank={selected.rank}",
        f"total_score={assessment.total_score:.6f}",
        f"risk={assessment.risk_score:.6f}",
        f"confidence={assessment.confidence_score:.6f}",
        f"evidence={assessment.evidence_score:.6f}",
        f"utility={assessment.utility_score:.6f}",
        f"reversibility={assessment.reversibility_score:.6f}",
    )

    return DecisionRationale(
        summary=(
            f"Selected {selected.candidate.action_kind.value} "
            f"for candidate {selected.candidate.candidate_id}."
        ),
        factors=factors,
        rejected_alternatives=rejected,
    )