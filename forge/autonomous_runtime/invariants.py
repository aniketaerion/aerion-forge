"""Mission lifecycle invariant checks."""

from __future__ import annotations

from forge.autonomous_runtime.errors import MissionContractError
from forge.autonomous_runtime.models import AutonomousMission
from forge.autonomous_runtime.states import (
    TERMINAL_MISSION_STATES,
    AuthorityLevel,
    MissionState,
)


def assert_budget_available(
    mission: AutonomousMission,
) -> None:
    """Ensure all mission-level execution budgets remain available."""
    budgets = mission.request.budgets

    if mission.replan_count > budgets.maximum_replans:
        raise MissionContractError("Mission replan budget is exhausted.")

    if mission.tool_call_count > budgets.maximum_tool_calls:
        raise MissionContractError("Mission tool-call budget is exhausted.")

    if mission.attempt_count > (
        budgets.maximum_steps
        * budgets.maximum_attempts_per_step
    ):
        raise MissionContractError("Mission attempt budget is exhausted.")


def assert_authority_consistent(
    mission: AutonomousMission,
) -> None:
    """Ensure granted authority does not exceed requested authority."""
    if mission.granted_authority > mission.request.requested_authority:
        raise MissionContractError(
            "Granted authority exceeds requested authority."
        )


def assert_terminal_outcome_consistent(
    mission: AutonomousMission,
) -> None:
    """Ensure terminal missions carry an outcome reference."""
    if (
        mission.state in TERMINAL_MISSION_STATES
        and mission.outcome_id is None
    ):
        raise MissionContractError(
            "Terminal mission requires an outcome identifier."
        )


def assert_execution_authority(
    mission: AutonomousMission,
) -> None:
    """Ensure execution state has sufficient authority."""
    if (
        mission.state is MissionState.EXECUTING
        and mission.granted_authority < AuthorityLevel.A2_MODIFY
    ):
        raise MissionContractError(
            "Executing mission requires at least A2 authority."
        )


def assert_mission_invariants(
    mission: AutonomousMission,
) -> None:
    """Validate all current M5.1 mission invariants."""
    assert_budget_available(mission)
    assert_authority_consistent(mission)
    assert_terminal_outcome_consistent(mission)
    assert_execution_authority(mission)