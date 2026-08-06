"""Contracts for the controlled autonomous tool gateway."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from forge.autonomous_execution.states import ToolExecutionStatus
from forge.autonomous_runtime.states import AuthorityLevel, RiskClass


class FrozenToolContract(BaseModel):
    """Base immutable tool contract."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class ToolDefinition(FrozenToolContract):
    """Registered tool metadata and safety contract."""

    tool_name: str = Field(min_length=1)
    action_kinds: tuple[str, ...] = Field(min_length=1)
    authority_required: AuthorityLevel
    risk_class: RiskClass
    mutates_repository: bool = False
    requires_checkpoint: bool = False
    timeout_seconds: int = Field(default=300, ge=1, le=86400)
    argument_schema: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_checkpoint_requirement(
        self,
    ) -> ToolDefinition:
        if self.mutates_repository and not self.requires_checkpoint:
            raise ValueError(
                "Mutating tools require a checkpoint."
            )
        return self


class ToolExecutionRequest(FrozenToolContract):
    """One controlled tool invocation request."""

    invocation_id: str = Field(min_length=1)
    mission_id: str = Field(min_length=1)
    step_id: str = Field(min_length=1)
    tool_name: str = Field(min_length=1)
    action_kind: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)
    approved_scope: tuple[str, ...] = ()
    checkpoint_id: str | None = None
    approval_id: str | None = None
    dry_run: bool = True


class ToolExecutionResult(FrozenToolContract):
    """Immutable controlled tool result."""

    invocation_id: str = Field(min_length=1)
    status: ToolExecutionStatus
    exit_code: int | None = None
    stdout_reference: str | None = None
    stderr_reference: str | None = None
    affected_files: tuple[str, ...] = ()
    result_digest: str | None = None
    started_at: str = Field(min_length=1)
    completed_at: str | None = None