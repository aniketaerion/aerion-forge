import pytest

from forge.autonomous_runtime.errors import MissionContractError
from forge.autonomous_runtime.events import (
    InMemoryMissionEventJournal,
)
from forge.autonomous_runtime.models import MissionEvent
from forge.autonomous_runtime.states import MissionState


def event(
    event_id: str,
    sequence: int,
) -> MissionEvent:
    return MissionEvent(
        event_id=event_id,
        mission_id="mission-1",
        sequence=sequence,
        event_type="mission_state_changed",
        previous_state=(
            MissionState.RECEIVED
            if sequence == 1
            else MissionState.QUALIFYING
        ),
        new_state=(
            MissionState.QUALIFYING
            if sequence == 1
            else MissionState.QUALIFIED
        ),
        actor="runtime",
    )


def test_event_journal_is_ordered_and_append_only() -> None:
    journal = InMemoryMissionEventJournal()
    journal.append(event("event-1", 1))
    journal.append(event("event-2", 2))

    assert [item.sequence for item in journal.events_for("mission-1")] == [
        1,
        2,
    ]


def test_invalid_event_sequence_is_rejected() -> None:
    journal = InMemoryMissionEventJournal()

    with pytest.raises(MissionContractError):
        journal.append(event("event-2", 2))