"""Append-only mission event journal contracts."""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.autonomous_runtime.errors import MissionContractError
from forge.autonomous_runtime.models import MissionEvent


@dataclass(slots=True)
class InMemoryMissionEventJournal:
    """Deterministic append-only event journal for M5.1."""

    _events: list[MissionEvent] = field(default_factory=list)

    def append(self, event: MissionEvent) -> None:
        """Append one event while enforcing ordering and uniqueness."""
        if any(
            existing.event_id == event.event_id
            for existing in self._events
        ):
            raise MissionContractError(
                f"Duplicate mission event identifier: {event.event_id}"
            )

        mission_events = [
            existing
            for existing in self._events
            if existing.mission_id == event.mission_id
        ]

        expected_sequence = (
            mission_events[-1].sequence + 1
            if mission_events
            else 1
        )

        if event.sequence != expected_sequence:
            raise MissionContractError(
                "Mission event sequence is invalid: "
                f"expected {expected_sequence}, got {event.sequence}."
            )

        self._events.append(event)

    def events_for(
        self,
        mission_id: str,
    ) -> tuple[MissionEvent, ...]:
        """Return immutable ordered events for one mission."""
        return tuple(
            event
            for event in self._events
            if event.mission_id == mission_id
        )

    def latest_for(
        self,
        mission_id: str,
    ) -> MissionEvent | None:
        """Return the latest event for one mission."""
        events = self.events_for(mission_id)
        return events[-1] if events else None