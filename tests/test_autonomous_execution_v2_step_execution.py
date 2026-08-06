from dataclasses import dataclass, field

from forge.autonomous_execution_v2.authority import (
    ExecutionAuthority,
)
from forge.autonomous_execution_v2.models import ExecutionStep
from forge.autonomous_execution_v2.policies import (
    AutonomousExecutionV2Policy,
)
from forge.autonomous_execution_v2.step_execution import (
    ControlledStepExecutor,
    StepToolInvocation,
)
from forge.autonomous_execution_v2.tool_adapter import (
    ControlledToolRequest,
    ControlledToolResult,
)


@dataclass
class FakeGateway:
    requests: list[ControlledToolRequest] = field(
        default_factory=list
    )

    def execute(
        self,
        request: ControlledToolRequest,
    ) -> ControlledToolResult:
        self.requests.append(request)
        return ControlledToolResult(
            invocation_id=request.invocation_id,
            succeeded=True,
            output_references=("result-1",),
            summary="Completed.",
        )


def test_step_executes_through_gateway() -> None:
    gateway = FakeGateway()
    outcome = ControlledStepExecutor(
        gateway=gateway,
        policy=AutonomousExecutionV2Policy(),
    ).execute(
        run_id="run-1",
        step=ExecutionStep(
            step_id="step-1",
            planning_step_id="planning-step-1",
            sequence=1,
            name="Validate",
            description="Run controlled validation.",
            required_tools=("test",),
        ),
        attempt_number=1,
        invocations=(
            StepToolInvocation(
                invocation_id="invocation-1",
                tool_name="test",
                arguments={"target": "tests"},
            ),
        ),
        authority=ExecutionAuthority(
            subject="agent",
            repository_root="repository",
            permitted_tools=("test",),
        ),
    )

    assert outcome.succeeded
    assert len(outcome.evidence) == 1
    assert len(gateway.requests) == 1