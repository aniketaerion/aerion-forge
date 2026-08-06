import pytest

from forge.autonomous_memory.feedback import (
    FeedbackOutcome,
    MemoryFeedback,
    assert_feedback_is_usable,
)


def test_validated_feedback_requires_evidence() -> None:
    feedback = MemoryFeedback(
        feedback_id="feedback-1",
        memory_id="memory-1",
        mission_id="mission-1",
        outcome=FeedbackOutcome.SUCCESS,
        validated=True,
        evidence_references=(),
        rationale="Mission succeeded.",
    )

    with pytest.raises(ValueError):
        assert_feedback_is_usable(feedback)