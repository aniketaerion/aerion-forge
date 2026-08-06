"""Initial confidence assessment."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_memory.models import MemoryObservation
from forge.autonomous_memory.states import MemoryKind, MemorySourceKind


@dataclass(frozen=True, slots=True)
class ConfidenceAssessment:
    score: float
    factors: tuple[str, ...]


_BASE = {
    MemorySourceKind.REPOSITORY: 0.80,
    MemorySourceKind.VALIDATION: 0.85,
    MemorySourceKind.EXECUTION: 0.75,
    MemorySourceKind.DECISION: 0.70,
    MemorySourceKind.MISSION: 0.65,
    MemorySourceKind.SESSION: 0.60,
    MemorySourceKind.ARCHITECTURE_REVIEW: 0.80,
    MemorySourceKind.HUMAN_CORRECTION: 0.75,
}


def assess_initial_confidence(
    *,
    observation: MemoryObservation,
    memory_kind: MemoryKind,
) -> ConfidenceAssessment:
    score = _BASE[observation.source_kind]
    factors = [f"source={observation.source_kind.value}"]

    if observation.evidence_references:
        score += min(
            0.15,
            len(observation.evidence_references) * 0.03,
        )
        factors.append(
            f"evidence_count={len(observation.evidence_references)}"
        )
    else:
        score -= 0.20
        factors.append("no_evidence")

    if memory_kind is MemoryKind.HYPOTHESIS:
        score = min(score, 0.60)
        factors.append("hypothesis_cap")

    return ConfidenceAssessment(
        score=round(max(0.0, min(score, 1.0)), 6),
        factors=tuple(factors),
    )