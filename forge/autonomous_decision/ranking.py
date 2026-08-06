"""Deterministic ranking of accepted candidate assessments."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_decision.models import (
    CandidateAction,
    CandidateAssessment,
)


@dataclass(frozen=True, slots=True)
class RankedCandidate:
    """Candidate joined with its assessment and rank."""

    rank: int
    candidate: CandidateAction
    assessment: CandidateAssessment


def rank_candidates(
    candidates: tuple[CandidateAction, ...],
    assessments: tuple[CandidateAssessment, ...],
) -> tuple[RankedCandidate, ...]:
    """Rank accepted candidates using documented tie breakers."""
    candidate_by_id = {
        candidate.candidate_id: candidate
        for candidate in candidates
    }

    accepted = [
        assessment
        for assessment in assessments
        if (
            assessment.feasible
            and assessment.policy_allowed
            and not assessment.rejection_reasons
        )
    ]

    ordered = sorted(
        accepted,
        key=lambda assessment: (
            -assessment.total_score,
            assessment.risk_score,
            -assessment.confidence_score,
            -assessment.evidence_score,
            -assessment.reversibility_score,
            assessment.candidate_id,
        ),
    )

    return tuple(
        RankedCandidate(
            rank=index,
            candidate=candidate_by_id[
                assessment.candidate_id
            ],
            assessment=assessment,
        )
        for index, assessment in enumerate(
            ordered,
            start=1,
        )
    )