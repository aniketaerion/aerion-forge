import pytest

from forge.autonomous_execution.errors import ToolContractError
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


def gateway() -> ControlledToolGateway:
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            tool_name="file-editor",
            action_kinds=("apply_patch",),
            authority_required=AuthorityLevel.A2_MODIFY,
            risk_class=RiskClass.R2_MODERATE,
            mutates_repository=True,
            requires_checkpoint=True,
            argument_schema={"path": "str"},
        )
    )

    executor = ToolExecutor()
    executor.register_handler(
        "file-editor",
        lambda request: (
            0,
            (str(request.arguments["path"]),),
            "digest-1",
        ),
    )

    return ControlledToolGateway(
        registry=registry,
        executor=executor,
    )


def test_dry_run_performs_no_mutation() -> None:
    result = gateway().execute(
        ToolExecutionRequest(
            invocation_id="invocation-1",
            mission_id="mission-1",
            step_id="step-1",
            tool_name="file-editor",
            action_kind="apply_patch",
            arguments={
                "path": "forge/autonomous_execution/models.py"
            },
            approved_scope=("forge/autonomous_execution",),
            checkpoint_id="checkpoint-1",
            dry_run=True,
        )
    )

    assert result.affected_files == ()
    assert result.exit_code == 0


def test_mutating_tool_requires_checkpoint() -> None:
    with pytest.raises(ToolContractError):
        gateway().execute(
            ToolExecutionRequest(
                invocation_id="invocation-2",
                mission_id="mission-1",
                step_id="step-1",
                tool_name="file-editor",
                action_kind="apply_patch",
                arguments={
                    "path": "forge/autonomous_execution/models.py"
                },
                approved_scope=("forge/autonomous_execution",),
                dry_run=False,
            )
        )


def test_actual_effects_are_scope_checked() -> None:
    tool_gateway = gateway()

    with pytest.raises(ToolContractError):
        tool_gateway.execute(
            ToolExecutionRequest(
                invocation_id="invocation-3",
                mission_id="mission-1",
                step_id="step-1",
                tool_name="file-editor",
                action_kind="apply_patch",
                arguments={"path": "deployments/production.yml"},
                approved_scope=("forge/autonomous_execution",),
                checkpoint_id="checkpoint-1",
                dry_run=False,
            )
        )