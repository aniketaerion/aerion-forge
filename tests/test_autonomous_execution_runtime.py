from forge.autonomous_execution.execution_journal import (
    InMemoryExecutionJournal,
)
from forge.autonomous_execution.lease_manager import (
    InMemoryExecutionLeaseManager,
)
from forge.autonomous_execution.models import ExecutionRequest
from forge.autonomous_execution.policies import (
    AutonomousExecutionPolicy,
)
from forge.autonomous_execution.runtime import (
    AutonomousExecutionRuntime,
)
from forge.autonomous_execution.states import (
    StepExecutionState,
)
from forge.autonomous_execution.tool_contracts import (
    ToolDefinition,
    ToolExecutionRequest,
)
from forge.autonomous_execution.tool_execution import ToolExecutor
from forge.autonomous_execution.tool_gateway import (
    ControlledToolGateway,
)
from forge.autonomous_execution.tool_registry import ToolRegistry
from forge.autonomous_runtime.states import AuthorityLevel, RiskClass


def runtime() -> AutonomousExecutionRuntime:
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            tool_name="ruff",
            action_kinds=("check",),
            authority_required=AuthorityLevel.A0_READ,
            risk_class=RiskClass.R0_READ_ONLY,
            argument_schema={"path": "str"},
        )
    )

    executor = ToolExecutor()
    executor.register_handler(
        "ruff",
        lambda request: (0, (), "digest-1"),
    )

    policy = AutonomousExecutionPolicy()
    return AutonomousExecutionRuntime(
        gateway=ControlledToolGateway(
            registry=registry,
            executor=executor,
            policy=policy,
        ),
        leases=InMemoryExecutionLeaseManager(),
        journal=InMemoryExecutionJournal(),
        policy=policy,
    )


def test_runtime_executes_one_step_successfully() -> None:
    result = runtime().execute(
        ExecutionRequest(
            request_id="request-1",
            mission_id="mission-1",
            plan_id="plan-1",
            step_id="step-1",
            repository_root="repository",
            requested_by="Aerion",
        ),
        ToolExecutionRequest(
            invocation_id="invocation-1",
            mission_id="mission-1",
            step_id="step-1",
            tool_name="ruff",
            action_kind="check",
            arguments={"path": "."},
            dry_run=True,
        ),
        repository_fingerprint="fingerprint-1",
    )

    assert result.record.state is StepExecutionState.SUCCEEDED
    assert len(result.evidence) == 1
    assert result.record.evidence_ids