"""Tool argument validation against registered contracts."""

from __future__ import annotations

from typing import Any

from forge.autonomous_execution.errors import ToolContractError
from forge.autonomous_execution.tool_contracts import (
    ToolDefinition,
    ToolExecutionRequest,
)


def _matches_type(
    value: Any,
    expected: str,
) -> bool:
    mapping: dict[str, type[Any] | tuple[type[Any], ...]] = {
        "str": str,
        "int": int,
        "float": (int, float),
        "bool": bool,
        "list": list,
        "dict": dict,
    }
    expected_type = mapping.get(expected)

    if expected_type is None:
        raise ToolContractError(
            f"Unsupported argument schema type: {expected}"
        )

    return isinstance(value, expected_type)


def validate_tool_arguments(
    definition: ToolDefinition,
    request: ToolExecutionRequest,
) -> None:
    """Validate tool, action, required arguments, and argument types."""
    if request.tool_name != definition.tool_name:
        raise ToolContractError(
            "Tool request does not match resolved tool definition."
        )

    if request.action_kind not in definition.action_kinds:
        raise ToolContractError(
            f"Action '{request.action_kind}' is not allowed "
            f"for tool '{definition.tool_name}'."
        )

    schema = definition.argument_schema
    unknown = set(request.arguments).difference(schema)

    if unknown:
        raise ToolContractError(
            "Unknown tool arguments: "
            + ", ".join(sorted(unknown))
        )

    missing = set(schema).difference(request.arguments)

    if missing:
        raise ToolContractError(
            "Missing tool arguments: "
            + ", ".join(sorted(missing))
        )

    for name, expected in schema.items():
        value = request.arguments[name]

        if not _matches_type(value, expected):
            raise ToolContractError(
                f"Argument '{name}' must be of type '{expected}'."
            )