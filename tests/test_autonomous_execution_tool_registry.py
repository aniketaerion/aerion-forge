import pytest

from forge.autonomous_execution.errors import (
    ToolContractError,
    ToolResolutionError,
)
from forge.autonomous_execution.tool_contracts import ToolDefinition
from forge.autonomous_execution.tool_registry import ToolRegistry
from forge.autonomous_runtime.states import AuthorityLevel, RiskClass


def definition() -> ToolDefinition:
    return ToolDefinition(
        tool_name="ruff",
        action_kinds=("check",),
        authority_required=AuthorityLevel.A0_READ,
        risk_class=RiskClass.R0_READ_ONLY,
        argument_schema={"path": "str"},
    )


def test_registry_resolves_registered_tool() -> None:
    registry = ToolRegistry()
    registry.register(definition())

    assert registry.resolve("ruff").tool_name == "ruff"


def test_duplicate_tool_is_rejected() -> None:
    registry = ToolRegistry()
    registry.register(definition())

    with pytest.raises(ToolContractError):
        registry.register(definition())


def test_unknown_tool_is_rejected() -> None:
    with pytest.raises(ToolResolutionError):
        ToolRegistry().resolve("unknown")