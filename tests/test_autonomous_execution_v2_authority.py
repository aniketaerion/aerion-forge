import pytest

from forge.autonomous_execution_v2.authority import (
    ExecutionAuthority,
    assert_step_authorized,
)
from forge.autonomous_execution_v2.errors import (
    ExecutionAuthorityError,
)
from forge.autonomous_execution_v2.models import ExecutionStep
from forge.autonomous_execution_v2.policies import (
    AutonomousExecutionV2Policy,
)


def test_authority_rejects_missing_tool() -> None:
    step = ExecutionStep(
        step_id="step-1",
        planning_step_id="planning-step-1",
        sequence=1,
        name="Edit",
        description="Apply controlled repository edit.",
        required_tools=("filesystem",),
    )

    with pytest.raises(ExecutionAuthorityError):
        assert_step_authorized(
            step=step,
            authority=ExecutionAuthority(
                subject="agent",
                repository_root="repository",
            ),
            policy=AutonomousExecutionV2Policy(),
        )