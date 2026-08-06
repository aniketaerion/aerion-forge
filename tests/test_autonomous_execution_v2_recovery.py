from forge.autonomous_execution_v2.attempts import (
    complete_attempt,
    create_attempt,
    start_attempt,
)
from forge.autonomous_execution_v2.policies import AutonomousExecutionV2Policy
from forge.autonomous_execution_v2.recovery import decide_recovery
from forge.autonomous_execution_v2.states import RecoveryAction


def test_recovery_requests_retry() -> None:
    attempt = complete_attempt(
        start_attempt(
            create_attempt(
                run_id="run-1",
                step_id="step-1",
                attempt_number=1,
            )
        ),
        succeeded=False,
        tool_invocation_ids=(),
        failure_reason="Failed.",
    )

    decision = decide_recovery(
        run_id="run-1",
        step_id="step-1",
        attempt=attempt,
        attempts_for_step=(attempt,),
        policy=AutonomousExecutionV2Policy(),
    )

    assert decision.action is RecoveryAction.RETRY