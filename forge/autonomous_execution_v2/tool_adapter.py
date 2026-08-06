"""Controlled tool-gateway adapter contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ControlledToolRequest:
    """One controlled tool invocation request."""

    invocation_id: str
    run_id: str
    step_id: str
    tool_name: str
    arguments: dict[str, object]


@dataclass(frozen=True, slots=True)
class ControlledToolResult:
    """Normalized result returned by the controlled gateway."""

    invocation_id: str
    succeeded: bool
    output_references: tuple[str, ...] = ()
    summary: str = ""
    error: str | None = None


class ControlledToolGateway(Protocol):
    """Protocol implemented by the M5.2 controlled gateway adapter."""

    def execute(
        self,
        request: ControlledToolRequest,
    ) -> ControlledToolResult:
        """Execute one governed tool request."""
        ...