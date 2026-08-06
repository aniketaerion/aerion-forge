import pytest

from forge.autonomous_execution_v2.attempts import (
    complete_attempt,
    create_attempt,
    start_attempt,
)
from forge.autonomous_execution_v2.errors import (
    ExecutionContractError,
)
from forge.autonomous_execution_v2.states import (
    ExecutionAttemptState,
)


def test_attempt_lifecycle_succeeds() -> None:
    attempt = create_attempt(
        run_id="run-1",
        step_id="step-1",
        attempt_number=1,
    )
    running = start_attempt(attempt)
    completed = complete_attempt(
        running,
        succeeded=True,
        tool_invocation_ids=("invocation-1",),
    )

    assert completed.state is ExecutionAttemptState.SUCCEEDED


def test_failed_attempt_requires_reason() -> None:
    attempt = start_attempt(
        create_attempt(
            run_id="run-1",
            step_id="step-1",
            attempt_number=1,
        )
    )

    with pytest.raises(ExecutionContractError):
        complete_attempt(
            attempt,
            succeeded=False,
            tool_invocation_ids=(),
        )