"""Application service for orchestration-session lifecycle."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_orchestration.identifiers import (
    mission_session_identifier,
)
from forge.autonomous_orchestration.models import (
    MissionSession,
    OrchestrationRequest,
    utc_now,
)
from forge.autonomous_orchestration.session_registry import (
    InMemorySessionRegistry,
)
from forge.autonomous_orchestration.states import OrchestrationState
from forge.autonomous_orchestration.transitions import (
    assert_orchestration_transition,
)


@dataclass(slots=True)
class MissionSessionService:
    """Create and transition versioned orchestration sessions."""

    registry: InMemorySessionRegistry

    def create(
        self,
        request: OrchestrationRequest,
        *,
        plan_id: str,
        plan_version: int,
    ) -> MissionSession:
        session = MissionSession(
            session_id=mission_session_identifier(
                {
                    "mission_id": request.mission_id,
                    "plan_id": plan_id,
                    "plan_version": plan_version,
                    "request_id": request.request_id,
                }
            ),
            mission_id=request.mission_id,
            plan_id=plan_id,
            plan_version=plan_version,
            repository_root=request.repository_root,
        )
        self.registry.create(session)
        return session

    def transition(
        self,
        session: MissionSession,
        target: OrchestrationState,
        *,
        stop_reason: str | None = None,
    ) -> MissionSession:
        assert_orchestration_transition(session.state, target)

        updated = session.model_copy(
            update={
                "state": target,
                "stop_reason": stop_reason,
                "version": session.version + 1,
                "updated_at": utc_now(),
            }
        )
        self.registry.update(
            updated,
            expected_version=session.version,
        )
        return updated

    def set_current_step(
        self,
        session: MissionSession,
        step_id: str,
    ) -> MissionSession:
        updated = session.model_copy(
            update={
                "current_step_id": step_id,
                "version": session.version + 1,
                "updated_at": utc_now(),
            }
        )
        self.registry.update(
            updated,
            expected_version=session.version,
        )
        return updated

    def mark_step_completed(
        self,
        session: MissionSession,
        step_id: str,
    ) -> MissionSession:
        completed = tuple(
            sorted(
                set(session.completed_step_ids).union({step_id})
            )
        )

        updated = session.model_copy(
            update={
                "current_step_id": (
                    None
                    if session.current_step_id == step_id
                    else session.current_step_id
                ),
                "completed_step_ids": completed,
                "execution_count": session.execution_count + 1,
                "cycle_count": session.cycle_count + 1,
                "version": session.version + 1,
                "updated_at": utc_now(),
            }
        )
        self.registry.update(
            updated,
            expected_version=session.version,
        )
        return updated