from forge.autonomous_runtime.states import (
    TERMINAL_MISSION_STATES,
    AuthorityLevel,
    MissionState,
    RiskClass,
)


def test_terminal_mission_states_are_explicit() -> None:
    assert {
        MissionState.COMPLETED,
        MissionState.FAILED,
        MissionState.CANCELLED,
    } == TERMINAL_MISSION_STATES


def test_authority_and_risk_are_ordered() -> None:
    assert AuthorityLevel.A0_READ < AuthorityLevel.A2_MODIFY
    assert AuthorityLevel.A4_COMMIT < AuthorityLevel.A6_MERGE_RELEASE
    assert RiskClass.R2_MODERATE < RiskClass.R4_CRITICAL