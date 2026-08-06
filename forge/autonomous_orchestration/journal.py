"""Append-only orchestration journal."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from forge.autonomous_orchestration.errors import (
    OrchestrationContractError,
)
from forge.autonomous_orchestration.states import OrchestrationState


def utc_now() -> datetime:
    return datetime.now(UTC)


class OrchestrationEvent(BaseModel):
    """Immutable orchestration event."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    event_type: str = Field(min_length=1)
    previous_state: OrchestrationState | None = None
    new_state: OrchestrationState | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


@dataclass(slots=True)
class InMemoryOrchestrationJournal:
    """Deterministic append-only orchestration event store."""

    _events: list[OrchestrationEvent] = field(default_factory=list)

    def append(self, event: OrchestrationEvent) -> None:
        if any(
            existing.event_id == event.event_id
            for existing in self._events
        ):
            raise OrchestrationContractError(
                f"Duplicate orchestration event: {event.event_id}"
            )

        events = self.events_for(event.session_id)
        expected = events[-1].sequence + 1 if events else 1

        if event.sequence != expected:
            raise OrchestrationContractError(
                f"Orchestration event sequence must be {expected}."
            )

        self._events.append(event)

    def events_for(
        self,
        session_id: str,
    ) -> tuple[OrchestrationEvent, ...]:
        return tuple(
            event
            for event in self._events
            if event.session_id == session_id
        )