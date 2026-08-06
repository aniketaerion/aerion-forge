from forge.autonomous_execution_v2.states import (
    EvidenceKind,
    ExecutionAttemptState,
    ExecutionRunState,
    ExecutionStepState,
    RecoveryAction,
)


def test_state_values_are_stable() -> None:
    assert ExecutionRunState.READY.value == "ready"
    assert ExecutionStepState.ELIGIBLE.value == "eligible"
    assert ExecutionAttemptState.RUNNING.value == "running"
    assert RecoveryAction.REPLAN.value == "replan"
    assert EvidenceKind.TEST_RESULT.value == "test_result"