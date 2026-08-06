"""Authority checks for M5.7 controlled execution."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_execution_v2.errors import (
    ExecutionAuthorityError,
    ExecutionPolicyError,
)
from forge.autonomous_execution_v2.models import ExecutionStep
from forge.autonomous_execution_v2.policies import (
    AutonomousExecutionV2Policy,
)


@dataclass(frozen=True, slots=True)
class ExecutionAuthority:
    """Authority granted to one execution run."""

    subject: str
    repository_root: str
    permitted_tools: tuple[str, ...] = ()
    permitted_capabilities: tuple[str, ...] = ()
    high_risk_approved: bool = False
    destructive_approved: bool = False


def assert_step_authorized(
    *,
    step: ExecutionStep,
    authority: ExecutionAuthority,
    policy: AutonomousExecutionV2Policy,
) -> None:
    """Raise when a step is outside the granted authority."""
    if not authority.subject.strip():
        raise ExecutionAuthorityError(
            "Execution authority subject cannot be empty."
        )

    missing_tools = tuple(
        tool
        for tool in step.required_tools
        if tool not in authority.permitted_tools
    )

    if missing_tools:
        raise ExecutionAuthorityError(
            "Execution authority does not permit tools: "
            + ", ".join(missing_tools)
        )

    if (
        step.risk in {"high", "critical"}
        and policy.safety.require_approval_for_high_risk
        and not authority.high_risk_approved
    ):
        raise ExecutionAuthorityError(
            "High-risk execution requires explicit approval."
        )

    if step.destructive:
        if not policy.safety.allow_destructive_execution:
            raise ExecutionPolicyError(
                "Destructive execution is forbidden by policy."
            )

        if not authority.destructive_approved:
            raise ExecutionAuthorityError(
                "Destructive execution requires explicit approval."
            )