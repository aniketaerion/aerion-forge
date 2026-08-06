"""Evidence-quality assessment for autonomous decisions."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_decision.models import (
    CandidateAction,
    DecisionContext,
)


@dataclass(frozen=True, slots=True)
class EvidenceAssessment:
    """Normalized evidence score and explainable factors."""

    score: float
    factors: tuple[str, ...]


def assess_evidence(
    candidate: CandidateAction,
    context: DecisionContext,
) -> EvidenceAssessment:
    """Assess available evidence deterministically."""
    candidate_evidence = set(candidate.evidence_references)
    context_evidence = set(context.evidence_references)
    combined = candidate_evidence | context_evidence

    if not combined:
        return EvidenceAssessment(
            score=0.0,
            factors=("no_evidence",),
        )

    score = 0.35
    factors: list[str] = [
        f"unique_evidence={len(combined)}"
    ]

    score += min(0.35, len(combined) * 0.07)

    overlap = candidate_evidence.intersection(context_evidence)
    if overlap:
        score += min(0.15, len(overlap) * 0.05)
        factors.append(f"shared_evidence={len(overlap)}")

    if context.repository_fingerprint:
        score += 0.10
        factors.append("repository_fingerprint_present")

    if context.unresolved_findings:
        score -= min(
            0.20,
            len(context.unresolved_findings) * 0.04,
        )
        factors.append("unresolved_findings")

    return EvidenceAssessment(
        score=round(max(0.0, min(score, 1.0)), 6),
        factors=tuple(factors),
    )