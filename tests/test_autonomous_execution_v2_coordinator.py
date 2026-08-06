from dataclasses import dataclass

from forge.autonomous_execution_v2.authority import (
    ExecutionAuthority,
)
from forge.autonomous_execution_v2.coordinator import (
    AutonomousExecutionCoordinator,
)
from forge.autonomous_execution_v2.graph_builder import (
    ExecutionGraphBuilder,
)
from forge.autonomous_execution_v2.models import (
    ExecutionRun,
    ExecutionStep,
)
from forge.autonomous_execution_v2.policies import (
    AutonomousExecutionV2Policy,
)
from forge.autonomous_execution_v2.states import (
    ExecutionRunState,
    ExecutionStepState,
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
    def execute(
        self,
        request: ControlledToolRequest,
    ) -> ControlledToolResult:
        return ControlledToolResult(
            invocation_id=request.invocation_id,
            succeeded=True,
            output_references=("result-1",),
            summary="Completed.",
        )


def test_coordinator_executes_next_step() -> None:
    policy = AutonomousExecutionV2Policy()
    run = ExecutionRun(
        run_id="run-1",
        request_id="request-1",
        plan_id="plan-1",
        plan_version=1,
        repository_root="repository",
        repository_fingerprint="fingerprint",
        state=ExecutionRunState.READY,
        steps=(
            ExecutionStep(
                step_id="step-1",
                planning_step_id="planning-step-1",
                sequence=1,
                name="Validate",
                description="Run controlled validation.",
                required_tools=("test",),
            ),
        ),
    )
    result = AutonomousExecutionCoordinator(
        graph_builder=ExecutionGraphBuilder(
            policy=policy
        ),
        executor=ControlledStepExecutor(
            gateway=FakeGateway(),
            policy=policy,
        ),
    ).execute_next(
        run=run,
        invocations_by_step={
            "step-1": (
                StepToolInvocation(
                    invocation_id="invocation-1",
                    tool_name="test",
                    arguments={},
                ),
            )
        },
        authority=ExecutionAuthority(
            subject="agent",
            repository_root="repository",
            permitted_tools=("test",),
        ),
    )

    assert result.run.state is ExecutionRunState.SUCCEEDED
    assert (
        result.run.steps[0].state
        is ExecutionStepState.SUCCEEDED
    )