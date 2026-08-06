"""Registered tool catalogue for autonomous execution."""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.autonomous_execution.errors import (
    ToolContractError,
    ToolResolutionError,
)
from forge.autonomous_execution.tool_contracts import ToolDefinition


@dataclass(slots=True)
class ToolRegistry:
    """Deterministic allowlist of executable tools."""

    _tools: dict[str, ToolDefinition] = field(default_factory=dict)

    def register(self, definition: ToolDefinition) -> None:
        if definition.tool_name in self._tools:
            raise ToolContractError(
                f"Tool already registered: {definition.tool_name}"
            )
        self._tools[definition.tool_name] = definition

    def resolve(self, tool_name: str) -> ToolDefinition:
        try:
            return self._tools[tool_name]
        except KeyError as exc:
            raise ToolResolutionError(
                f"Tool is not registered: {tool_name}"
            ) from exc

    def definitions(self) -> tuple[ToolDefinition, ...]:
        return tuple(
            self._tools[name]
            for name in sorted(self._tools)
        )

    def contains(self, tool_name: str) -> bool:
        return tool_name in self._tools