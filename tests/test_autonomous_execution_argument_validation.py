import pytest

from forge.autonomous_execution.argument_validation import (
    validate_tool_arguments,
)
from forge.autonomous_execution.errors import ToolContractError
from forge.autonomous_execution.tool_contracts import (
    ToolDefinition,
    ToolExecutionRequest,
)
from forge.autonomous_runtime.states import AuthorityLevel, RiskClass


def definition() -> ToolDefinition:
    return ToolDefinition(
        tool_name="ruff",
        action_kinds=("check",),
        authority_required=AuthorityLevel.A0_READ,
        risk_class=RiskClass.R0_READ_ONLY,
        argument_schema={"path": "str"},
    )


def request(
    arguments: dict[str, object],
) -> ToolExecutionRequest:
    return ToolExecutionRequest(
        invocation_id="invocation-1",
        mission_id="mission-1",
        step_id="step-1",
        tool_name="ruff",
        action_kind="check",
        arguments=arguments,
    )


def test_valid_arguments_pass() -> None:
    validate_tool_arguments(
        definition(),
        request({"path": "."}),
    )


def test_missing_argument_is_rejected() -> None:
    with pytest.raises(ToolContractError):
        validate_tool_arguments(
            definition(),
            request({}),
        )


def test_wrong_argument_type_is_rejected() -> None:
    with pytest.raises(ToolContractError):
        validate_tool_arguments(
            definition(),
            request({"path": 1}),
        )