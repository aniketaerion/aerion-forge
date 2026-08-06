from forge.autonomous_execution_v2.attempts import (
    complete_attempt,
    create_attempt,
    start_attempt,
)
from forge.autonomous_execution_v2.models import ExecutionAttempt
from forge.autonomous_execution_v2.policies import AutonomousExecutionV2Policy
from forge.autonomous_execution_v2.retry import evaluate_retry


def failed_attempt(number: int) -> ExecutionAttempt:
    return complete_attempt(
        start_attempt(
            create_attempt(
                run_id="run-1",
                step_id="step-1",
                attempt_number=number,
            )
        ),
        succeeded=False,
        tool_invocation_ids=(),
        failure_reason="Failed.",
    )


def test_retry_is_bounded() -> None:
    policy = AutonomousExecutionV2Policy()
    decision = evaluate_retry(
        attempts=(
            failed_attempt(1),
            failed_attempt(2),
            failed_attempt(3),
        ),
        policy=policy,
    )

    assert not decision.allowed
    assert decision.next_attempt_number is None