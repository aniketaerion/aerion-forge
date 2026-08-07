"""Mission lifecycle application service."""

from __future__ import annotations

from dataclasses import dataclass

from forge.mission_runtime.models import MissionSession
from forge.mission_runtime.repository import InMemoryMissionRepository
from forge.mission_runtime.state_machine import assert_transition
from forge.mission_runtime.states import MissionState


@dataclass(slots=True)
class MissionRuntimeService:
    repository: InMemoryMissionRepository

    def register(self, session: MissionSession) -> None:
        self.repository.put_session(session)

    def transition(
        self,
        *,
        session_id: str,
        target: MissionState,
    ) -> MissionSession:
        session = self.repository.get_session(session_id)
        if session is None:
            raise KeyError(f"Unknown mission session: {session_id}")

        assert_transition(session.state, target)
        updated = session.model_copy(update={"state": target})
        self.repository.put_session(updated)
        return updated