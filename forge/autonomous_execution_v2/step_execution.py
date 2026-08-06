"""Controlled execution of one M5.7 step."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_execution_v2.attempts import (
    complete_attempt,
    create_attempt,
    start_attempt,
)
from forge.autonomous_execution_v2.authority import (
    ExecutionAuthority,
    assert_step_authorized,
)
from forge.autonomous_execution_v2.evidence import (
    evidence_from_tool_result,
)
from forge.autonomous_execution_v2.models import (
    ExecutionAttempt,
    ExecutionEvidence,
    ExecutionStep,
)
from forge.autonomous_execution_v2.policies import (
    AutonomousExecutionV2Policy,
)
from forge.autonomous_execution_v2.tool_adapter import (
    ControlledToolGateway,
    ControlledToolRequest,
    ControlledToolResult,
)


@dataclass(frozen=True, slots=True)
class StepToolInvocation:
    """Planned controlled invocation for one execution step."""

    invocation_id: str
    tool_name: str
    arguments: dict[str, object]


@dataclass(frozen=True, slots=True)
class StepExecutionOutcome:
    """Result of executing one step attempt."""

    step_id: str
    attempt: ExecutionAttempt
    tool_results: tuple[ControlledToolResult, ...]
    evidence: tuple[ExecutionEvidence, ...]

    @property
    def succeeded(self) -> bool:
        return self.attempt.state.value == "succeeded"


@dataclass(frozen=True, slots=True)
class ControlledStepExecutor:
    """Execute step invocations exclusively through a gateway."""

    gateway: ControlledToolGateway
    policy: AutonomousExecutionV2Policy

    def execute(
        self,
        *,
        run_id: str,
        step: ExecutionStep,
        attempt_number: int,
        invocations: tuple[StepToolInvocation, ...],
        authority: ExecutionAuthority,
    ) -> StepExecutionOutcome:
        assert_step_authorized(
            step=step,
            authority=authority,
            policy=self.policy,
        )
        attempt = start_attempt(
            create_attempt(
                run_id=run_id,
                step_id=step.step_id,
                attempt_number=attempt_number,
            )
        )
        results: list[ControlledToolResult] = []
        evidence: list[ExecutionEvidence] = []

        for invocation in invocations:
            result = self.gateway.execute(
                ControlledToolRequest(
                    invocation_id=invocation.invocation_id,
                    run_id=run_id,
                    step_id=step.step_id,
                    tool_name=invocation.tool_name,
                    arguments=invocation.arguments,
                )
            )
            results.append(result)

            if result.succeeded:
                evidence.append(
                    evidence_from_tool_result(
                        run_id=run_id,
                        step_id=step.step_id,
                        attempt=attempt,
                        result=result,
                    )
                )
            else:
                failed = complete_attempt(
                    attempt,
                    succeeded=False,
                    tool_invocation_ids=tuple(
                        item.invocation_id
                        for item in results
                    ),
                    failure_reason=(
                        result.error
                        or "Controlled tool execution failed."
                    ),
                )
                return StepExecutionOutcome(
                    step_id=step.step_id,
                    attempt=failed,
                    tool_results=tuple(results),
                    evidence=tuple(evidence),
                )

        completed = complete_attempt(
            attempt,
            succeeded=True,
            tool_invocation_ids=tuple(
                item.invocation_id
                for item in results
            ),
        )

        return StepExecutionOutcome(
            step_id=step.step_id,
            attempt=completed,
            tool_results=tuple(results),
            evidence=tuple(evidence),
        )