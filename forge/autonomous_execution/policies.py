"""Bounded policies for autonomous execution."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from forge.autonomous_execution.errors import ExecutionPolicyError
from forge.autonomous_runtime.states import AuthorityLevel, RiskClass


class ExecutionBudgetPolicy(BaseModel):
    """Finite execution budgets."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    maximum_step_attempts: int = Field(default=2, ge=1, le=10)
    maximum_tool_invocations_per_step: int = Field(
        default=8,
        ge=1,
        le=100,
    )
    maximum_execution_seconds: int = Field(
        default=900,
        ge=1,
        le=86400,
    )
    maximum_lease_seconds: int = Field(
        default=1200,
        ge=30,
        le=86400,
    )
    maximum_affected_files: int = Field(
        default=50,
        ge=1,
        le=1000,
    )

    @model_validator(mode="after")
    def validate_time_relationships(
        self,
    ) -> ExecutionBudgetPolicy:
        if self.maximum_lease_seconds < self.maximum_execution_seconds:
            raise ValueError(
                "maximum_lease_seconds must cover "
                "maximum_execution_seconds."
            )
        return self


class ToolGatewayPolicy(BaseModel):
    """Default-safe tool-gateway policy."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    allow_network_access: bool = False
    allow_unrestricted_shell: bool = False
    allow_dynamic_tool_import: bool = False
    require_registered_tools: bool = True
    require_argument_validation: bool = True
    require_effect_verification: bool = True
    require_checkpoint_for_mutation: bool = True
    redact_secrets: bool = True
    dry_run_by_default: bool = True

    @model_validator(mode="after")
    def validate_safety_invariants(
        self,
    ) -> ToolGatewayPolicy:
        violations: list[str] = []

        if self.allow_network_access:
            violations.append("network access must be denied by default")
        if self.allow_unrestricted_shell:
            violations.append("unrestricted shell must remain disabled")
        if self.allow_dynamic_tool_import:
            violations.append("dynamic tool import must remain disabled")
        if not self.require_registered_tools:
            violations.append("registered tools are mandatory")
        if not self.require_argument_validation:
            violations.append("argument validation is mandatory")
        if not self.require_effect_verification:
            violations.append("effect verification is mandatory")
        if not self.require_checkpoint_for_mutation:
            violations.append(
                "checkpoint-before-mutation is mandatory"
            )
        if not self.redact_secrets:
            violations.append("secret redaction is mandatory")

        if violations:
            raise ExecutionPolicyError("; ".join(violations))

        return self


class ExecutionAuthorityPolicy(BaseModel):
    """Execution-specific authority constraints."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    autonomous_ceiling: AuthorityLevel = AuthorityLevel.A2_MODIFY
    explicit_approval_from: AuthorityLevel = AuthorityLevel.A4_COMMIT
    high_risk_from: RiskClass = RiskClass.R3_HIGH

    @model_validator(mode="after")
    def validate_order(
        self,
    ) -> ExecutionAuthorityPolicy:
        if self.autonomous_ceiling >= self.explicit_approval_from:
            raise ValueError(
                "Autonomous ceiling must stay below "
                "the explicit approval boundary."
            )
        return self


class AutonomousExecutionPolicy(BaseModel):
    """Top-level execution-engine policy."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = "1.0"
    budgets: ExecutionBudgetPolicy = Field(
        default_factory=ExecutionBudgetPolicy
    )
    gateway: ToolGatewayPolicy = Field(
        default_factory=ToolGatewayPolicy
    )
    authority: ExecutionAuthorityPolicy = Field(
        default_factory=ExecutionAuthorityPolicy
    )
    single_writer_required: bool = True
    one_tool_at_a_time: bool = True

    @model_validator(mode="after")
    def validate_runtime_invariants(
        self,
    ) -> AutonomousExecutionPolicy:
        violations: list[str] = []

        if not self.single_writer_required:
            violations.append("single-writer execution is mandatory")
        if not self.one_tool_at_a_time:
            violations.append("one-tool-at-a-time is mandatory")

        if violations:
            raise ExecutionPolicyError("; ".join(violations))

        return self