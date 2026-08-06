"""Deterministic mission lifecycle operations."""

from __future__ import annotations

from datetime import UTC, datetime

from forge.autonomous_runtime.errors import MissionStateError
from forge.autonomous_runtime.invariants import (
    assert_mission_invariants,
)
from forge.autonomous_runtime.models import AutonomousMission
from forge.autonomous_runtime.states import (
    TERMINAL_MISSION_STATES,
    MissionState,
)
from forge.autonomous_runtime.transitions import (
    assert_transition_allowed,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


def transition_mission(
    mission: AutonomousMission,
    target: MissionState,
    *,
    outcome_id: str | None = None,
    current_step_id: str | None = None,
    increment_attempt: bool = False,
    increment_replan: bool = False,
    increment_tool_call: bool = False,
) -> AutonomousMission:
    """Return a new immutable mission snapshot in the target state."""
    if mission.state in TERMINAL_MISSION_STATES:
        raise MissionStateError(
            f"Terminal mission cannot transition from {mission.state.value}."
        )

    assert_mission_invariants(mission)
    assert_transition_allowed(mission.state, target)

    if target in TERMINAL_MISSION_STATES and not outcome_id:
        raise MissionStateError(
            "Terminal transition requires an outcome identifier."
        )

    updated = mission.model_copy(
        update={
            "version": mission.version + 1,
            "state": target,
            "current_step_id": current_step_id,
            "attempt_count": mission.attempt_count
            + int(increment_attempt),
            "replan_count": mission.replan_count
            + int(increment_replan),
            "tool_call_count": mission.tool_call_count
            + int(increment_tool_call),
            "outcome_id": outcome_id
            if target in TERMINAL_MISSION_STATES
            else mission.outcome_id,
            "updated_at": utc_now(),
        }
    )

    assert_mission_invariants(updated)
    return updated


def pause_mission(
    mission: AutonomousMission,
) -> AutonomousMission:
    return transition_mission(mission, MissionState.PAUSED)


def cancel_mission(
    mission: AutonomousMission,
    *,
    outcome_id: str,
) -> AutonomousMission:
    return transition_mission(
        mission,
        MissionState.CANCELLED,
        outcome_id=outcome_id,
    )


def fail_mission(
    mission: AutonomousMission,
    *,
    outcome_id: str,
) -> AutonomousMission:
    return transition_mission(
        mission,
        MissionState.FAILED,
        outcome_id=outcome_id,
    )