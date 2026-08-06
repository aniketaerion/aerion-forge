"""Outcome feedback contracts and attribution."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class FeedbackOutcome(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"


@dataclass(frozen=True, slots=True)
class MemoryFeedback:
    """Validated outcome attributed to reused memory."""

    feedback_id: str
    memory_id: str
    mission_id: str
    outcome: FeedbackOutcome
    validated: bool
    evidence_references: tuple[str, ...]
    rationale: str


def assert_feedback_is_usable(
    feedback: MemoryFeedback,
) -> None:
    """Require validated feedback and evidence."""
    if not feedback.validated:
        raise ValueError(
            "Only validated feedback may update learning."
        )

    if not feedback.evidence_references:
        raise ValueError(
            "Validated feedback requires evidence."
        )