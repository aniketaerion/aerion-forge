"""Single-session registry for autonomous mission orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.autonomous_orchestration.errors import (
    OrchestrationContractError,
)
from forge.autonomous_orchestration.models import MissionSession
from forge.autonomous_orchestration.states import (
    TERMINAL_ORCHESTRATION_STATES,
)


@dataclass(slots=True)
class InMemorySessionRegistry:
    """Enforce one active orchestration session per mission."""

    _sessions: dict[str, MissionSession] = field(default_factory=dict)

    def create(self, session: MissionSession) -> None:
        existing = self._sessions.get(session.mission_id)

        if (
            existing is not None
            and existing.state not in TERMINAL_ORCHESTRATION_STATES
        ):
            raise OrchestrationContractError(
                "Mission already has an active orchestration session."
            )

        self._sessions[session.mission_id] = session

    def get(self, mission_id: str) -> MissionSession:
        try:
            return self._sessions[mission_id]
        except KeyError as exc:
            raise OrchestrationContractError(
                f"No orchestration session exists for mission: "
                f"{mission_id}"
            ) from exc

    def update(
        self,
        session: MissionSession,
        *,
        expected_version: int,
    ) -> None:
        current = self.get(session.mission_id)

        if current.version != expected_version:
            raise OrchestrationContractError(
                "Orchestration session version conflict."
            )

        if session.version != expected_version + 1:
            raise OrchestrationContractError(
                "Updated orchestration session must increment version "
                "by exactly one."
            )

        self._sessions[session.mission_id] = session

    def active_sessions(self) -> tuple[MissionSession, ...]:
        return tuple(
            session
            for session in sorted(
                self._sessions.values(),
                key=lambda item: item.mission_id,
            )
            if session.state not in TERMINAL_ORCHESTRATION_STATES
        )