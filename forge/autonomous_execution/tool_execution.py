"""Controlled in-process tool execution abstraction."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime

from forge.autonomous_execution.errors import ToolResolutionError
from forge.autonomous_execution.states import ToolExecutionStatus
from forge.autonomous_execution.tool_contracts import (
    ToolExecutionRequest,
    ToolExecutionResult,
)

ToolHandler = Callable[
    [ToolExecutionRequest],
    tuple[int, tuple[str, ...], str | None],
]


def utc_timestamp() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(slots=True)
class ToolExecutor:
    """Execute only explicitly registered in-process handlers."""

    _handlers: dict[str, ToolHandler] = field(default_factory=dict)

    def register_handler(
        self,
        tool_name: str,
        handler: ToolHandler,
    ) -> None:
        if tool_name in self._handlers:
            raise ToolResolutionError(
                f"Tool handler already registered: {tool_name}"
            )
        self._handlers[tool_name] = handler

    def handlers(self) -> Mapping[str, ToolHandler]:
        return dict(self._handlers)

    def execute(
        self,
        request: ToolExecutionRequest,
    ) -> ToolExecutionResult:
        started_at = utc_timestamp()

        if request.dry_run:
            return ToolExecutionResult(
                invocation_id=request.invocation_id,
                status=ToolExecutionStatus.DRY_RUN,
                exit_code=0,
                affected_files=(),
                started_at=started_at,
                completed_at=utc_timestamp(),
            )

        try:
            handler = self._handlers[request.tool_name]
        except KeyError as exc:
            raise ToolResolutionError(
                f"No execution handler registered: {request.tool_name}"
            ) from exc

        exit_code, affected_files, result_digest = handler(request)
        status = (
            ToolExecutionStatus.SUCCEEDED
            if exit_code == 0
            else ToolExecutionStatus.FAILED
        )

        return ToolExecutionResult(
            invocation_id=request.invocation_id,
            status=status,
            exit_code=exit_code,
            affected_files=affected_files,
            result_digest=result_digest,
            started_at=started_at,
            completed_at=utc_timestamp(),
        )