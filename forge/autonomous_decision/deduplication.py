"""Semantic candidate deduplication."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_decision.models import CandidateAction
from forge.autonomous_decision.states import CandidateRejectionReason


@dataclass(frozen=True, slots=True)
class CandidateDeduplicationResult:
    """Unique candidates and rejected duplicate identifiers."""

    candidates: tuple[CandidateAction, ...]
    rejected: tuple[
        tuple[str, CandidateRejectionReason],
        ...,
    ]


def candidate_semantic_key(
    candidate: CandidateAction,
) -> tuple[str, str, str]:
    """Return a stable semantic candidate key."""
    return (
        candidate.action_kind.value,
        candidate.target_step_id or "",
        candidate.description.strip().casefold(),
    )


def deduplicate_candidates(
    candidates: tuple[CandidateAction, ...],
) -> CandidateDeduplicationResult:
    """Remove semantic duplicates deterministically."""
    seen: set[tuple[str, str, str]] = set()
    accepted: list[CandidateAction] = []
    rejected: list[
        tuple[str, CandidateRejectionReason]
    ] = []

    for candidate in sorted(
        candidates,
        key=lambda item: item.candidate_id,
    ):
        key = candidate_semantic_key(candidate)

        if key in seen:
            rejected.append(
                (
                    candidate.candidate_id,
                    CandidateRejectionReason.DUPLICATE,
                )
            )
            continue

        seen.add(key)
        accepted.append(candidate)

    return CandidateDeduplicationResult(
        candidates=tuple(accepted),
        rejected=tuple(rejected),
    )