"""Application service for deterministic mission lifecycle control."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_runtime.lifecycle import transition_mission
from forge.autonomous_runtime.models import AutonomousMission
from forge.autonomous_runtime.states import MissionState
from forge.autonomous_runtime.transitions import allowed_targets


@dataclass(frozen=True, slots=True)
class MissionTransitionRequest:
    """Request to move one mission snapshot to a new state."""

    target: MissionState
    outcome_id: str | None = None
    current_step_id: str | None = None
    increment_attempt: bool = False
    increment_replan: bool = False
    increment_tool_call: bool = False


class AutonomousLifecycleService:
    """Read-only decision and immutable transition service."""

    def available_transitions(
        self,
        mission: AutonomousMission,
    ) -> frozenset[MissionState]:
        return allowed_targets(mission.state)

    def transition(
        self,
        mission: AutonomousMission,
        request: MissionTransitionRequest,
    ) -> AutonomousMission:
        return transition_mission(
            mission,
            request.target,
            outcome_id=request.outcome_id,
            current_step_id=request.current_step_id,
            increment_attempt=request.increment_attempt,
            increment_replan=request.increment_replan,
            increment_tool_call=request.increment_tool_call,
        )