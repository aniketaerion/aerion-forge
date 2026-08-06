"""Append-only journal for step execution events."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from forge.autonomous_execution.errors import ExecutionContractError
from forge.autonomous_execution.states import StepExecutionState


def utc_now() -> datetime:
    return datetime.now(UTC)


class ExecutionEvent(BaseModel):
    """Immutable step execution event."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str = Field(min_length=1)
    execution_id: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    event_type: str = Field(min_length=1)
    previous_state: StepExecutionState | None = None
    new_state: StepExecutionState | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


@dataclass(slots=True)
class InMemoryExecutionJournal:
    """Deterministic append-only execution journal."""

    _events: list[ExecutionEvent] = field(default_factory=list)

    def append(self, event: ExecutionEvent) -> None:
        if any(
            existing.event_id == event.event_id
            for existing in self._events
        ):
            raise ExecutionContractError(
                f"Duplicate execution event: {event.event_id}"
            )

        events = self.events_for(event.execution_id)
        expected = events[-1].sequence + 1 if events else 1

        if event.sequence != expected:
            raise ExecutionContractError(
                f"Execution event sequence must be {expected}."
            )

        self._events.append(event)

    def events_for(
        self,
        execution_id: str,
    ) -> tuple[ExecutionEvent, ...]:
        return tuple(
            event
            for event in self._events
            if event.execution_id == execution_id
        )