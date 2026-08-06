from forge.autonomous_orchestration.states import (
    RESUMABLE_ORCHESTRATION_STATES,
    TERMINAL_ORCHESTRATION_STATES,
    OrchestrationState,
)


def test_terminal_states_are_explicit() -> None:
    assert OrchestrationState.COMPLETED in TERMINAL_ORCHESTRATION_STATES
    assert OrchestrationState.FAILED in TERMINAL_ORCHESTRATION_STATES
    assert OrchestrationState.READY not in TERMINAL_ORCHESTRATION_STATES


def test_paused_session_is_resumable() -> None:
    assert OrchestrationState.PAUSED in RESUMABLE_ORCHESTRATION_STATES
    assert (
        OrchestrationState.COMPLETED
        not in RESUMABLE_ORCHESTRATION_STATES
    )