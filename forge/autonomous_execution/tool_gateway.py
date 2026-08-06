"""Controlled gateway for autonomous tool invocations."""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.autonomous_execution.argument_validation import (
    validate_tool_arguments,
)
from forge.autonomous_execution.effect_verification import (
    verify_affected_files,
)
from forge.autonomous_execution.errors import ToolContractError
from forge.autonomous_execution.policies import (
    AutonomousExecutionPolicy,
)
from forge.autonomous_execution.tool_contracts import (
    ToolExecutionRequest,
    ToolExecutionResult,
)
from forge.autonomous_execution.tool_execution import ToolExecutor
from forge.autonomous_execution.tool_registry import ToolRegistry


@dataclass(slots=True)
class ControlledToolGateway:
    """Resolve, validate, execute, and verify one tool invocation."""

    registry: ToolRegistry
    executor: ToolExecutor
    policy: AutonomousExecutionPolicy = field(
        default_factory=AutonomousExecutionPolicy
    )

    def execute(
        self,
        request: ToolExecutionRequest,
    ) -> ToolExecutionResult:
        definition = self.registry.resolve(request.tool_name)

        validate_tool_arguments(definition, request)

        if (
            definition.mutates_repository
            and self.policy.gateway.require_checkpoint_for_mutation
            and request.checkpoint_id is None
        ):
            raise ToolContractError(
                "Mutating tool invocation requires a checkpoint."
            )

        result = self.executor.execute(request)

        if self.policy.gateway.require_effect_verification:
            verify_affected_files(
                result.affected_files,
                request.approved_scope,
            )

        if len(result.affected_files) > (
            self.policy.budgets.maximum_affected_files
        ):
            raise ToolContractError(
                "Tool affected more files than the execution policy allows."
            )

        return result