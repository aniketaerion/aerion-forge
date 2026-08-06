import pytest

from forge.autonomous_decision.errors import DecisionReplayError
from forge.autonomous_decision.models import DecisionRecord
from forge.autonomous_decision.replay_guard import (
    DecisionReplayGuard,
)
from forge.autonomous_decision.states import (
    DecisionDisposition,
    DecisionKind,
)


def record(
    decision_id: str,
    rationale: str,
) -> DecisionRecord:
    return DecisionRecord(
        decision_id=decision_id,
        request_id="request-1",
        context_id="context-1",
        decision_kind=DecisionKind.STOP,
        disposition=DecisionDisposition.NO_SAFE_ACTION,
        rationale=rationale,
        confidence=0.0,
        context_fingerprint="fingerprint-1",
    )


def test_identical_replay_is_idempotent() -> None:
    guard = DecisionReplayGuard()
    first = record("decision-1", "No safe action.")

    assert guard.check_and_record(first) == first
    assert guard.check_and_record(first) == first


def test_conflicting_replay_is_rejected() -> None:
    guard = DecisionReplayGuard()
    guard.check_and_record(
        record("decision-1", "No safe action.")
    )

    with pytest.raises(DecisionReplayError):
        guard.check_and_record(
            record("decision-2", "Different decision.")
        )