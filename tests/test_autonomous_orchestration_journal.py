import pytest

from forge.autonomous_orchestration.errors import (
    OrchestrationContractError,
)
from forge.autonomous_orchestration.journal import (
    InMemoryOrchestrationJournal,
    OrchestrationEvent,
)


def test_journal_enforces_sequence() -> None:
    journal = InMemoryOrchestrationJournal()
    journal.append(
        OrchestrationEvent(
            event_id="event-1",
            session_id="session-1",
            sequence=1,
            event_type="created",
        )
    )

    with pytest.raises(OrchestrationContractError):
        journal.append(
            OrchestrationEvent(
                event_id="event-2",
                session_id="session-1",
                sequence=3,
                event_type="invalid",
            )
        )