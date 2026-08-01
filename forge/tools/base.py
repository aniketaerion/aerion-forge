"""Abstract contract shared by every platform tool."""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """Normalized result returned by a tool execution."""

    success: bool
    output: Any = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Tool(ABC):
    """Validated, injectable execution boundary for local capabilities."""

    @abstractmethod
    def validate(self, action: str, parameters: dict[str, Any]) -> None:
        """Raise a descriptive exception when an operation is unsafe or invalid."""

    @abstractmethod
    def execute(self, action: str, parameters: dict[str, Any]) -> ToolResult:
        """Validate and perform an operation."""

    def rollback(self, result: ToolResult) -> ToolResult:
        """Rollback an operation when supported by the concrete tool."""
        return ToolResult(success=False, error=f"{type(self).__name__} does not support rollback")
