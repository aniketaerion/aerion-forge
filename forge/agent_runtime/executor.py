"""Execution engine for M3.8 Unified Agent Runtime."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from forge.agent_runtime.errors import (
    AgentRuntimeApprovalError,
    AgentRuntimeExecutionError,
)
from forge.agent_runtime.models import (
    AgentRuntimePolicy,
    AgentSession,
    AgentSessionStatus,
    AgentStageStatus,
    ApprovalKind,
)
from forge.agent_runtime.policies import require_approval
from forge.agent_runtime.registry import AgentCapabilityRegistry
from forge.agent_runtime.state import (
    append_stage_result,
    failed_required_stage,
    next_ready_stage,
    transition_session,
)


def _status_for_stage(
    stage_capability: str,
) -> AgentSessionStatus:
    if stage_capability == "mission_planning":
        return AgentSessionStatus.PLANNING
    if stage_capability in {
        "validation_repair",
        "build_verification",
    }:
        return AgentSessionStatus.VERIFYING
    if stage_capability == "autonomous_repair":
        return AgentSessionStatus.REPAIRING
    return AgentSessionStatus.EXECUTING


class AgentRuntimeExecutor:
    """Execute one stage at a time through registered adapters."""

    def __init__(
        self,
        registry: AgentCapabilityRegistry,
        policy: AgentRuntimePolicy | None = None,
    ) -> None:
        self.registry = registry
        self.policy = policy or AgentRuntimePolicy()

    def run_next(
        self,
        session: AgentSession,
        *,
        repository_root: Path,
        context: Mapping[str, Any] | None = None,
    ) -> AgentSession:
        """Execute exactly one ready stage or finalize the session."""
        if session.status in {
            AgentSessionStatus.COMPLETED,
            AgentSessionStatus.FAILED,
            AgentSessionStatus.CANCELLED,
        }:
            return session

        failed = failed_required_stage(session)
        if failed is not None:
            if session.status is AgentSessionStatus.FAILED:
                return session
            return transition_session(
                session,
                AgentSessionStatus.FAILED,
                current_stage_id=failed.stage_id,
            )

        stage = next_ready_stage(session)
        if stage is None:
            if len(session.stage_results) == len(session.stages):
                if session.status is AgentSessionStatus.COMPLETED:
                    return session
                return transition_session(
                    session,
                    AgentSessionStatus.COMPLETED,
                    current_stage_id=None,
                )

            raise AgentRuntimeExecutionError(
                "no dependency-satisfied stage is available"
            )

        if stage.requires_approval is not None:
            try:
                require_approval(
                    session.approvals,
                    stage.requires_approval,
                    self.policy,
                )
            except AgentRuntimeApprovalError:
                if session.status is AgentSessionStatus.AWAITING_APPROVAL:
                    return session

                return transition_session(
                    session,
                    AgentSessionStatus.AWAITING_APPROVAL,
                    current_stage_id=stage.stage_id,
                )

        target_status = _status_for_stage(stage.capability.value)
        active = (
            session
            if session.status is target_status
            else transition_session(
                session,
                target_status,
                current_stage_id=stage.stage_id,
            )
        )

        adapter = self.registry.get(stage.capability)

        try:
            result = adapter.execute(
                repository_root.resolve(),
                active,
                stage,
                context or {},
            )
        except Exception as exc:
            raise AgentRuntimeExecutionError(
                f"stage execution failed: {stage.stage_id}"
            ) from exc

        updated = append_stage_result(active, result)

        if (
            stage.required
            and result.status
            in {
                AgentStageStatus.FAILED,
                AgentStageStatus.BLOCKED,
            }
        ):
            return transition_session(
                updated,
                AgentSessionStatus.FAILED,
                current_stage_id=stage.stage_id,
            )

        return updated

    def run_to_boundary(
        self,
        session: AgentSession,
        *,
        repository_root: Path,
        context: Mapping[str, Any] | None = None,
    ) -> AgentSession:
        """Execute until approval, failure, cancellation, or completion."""
        current = session

        for _ in range(current.request.max_stages + 1):
            before = current
            current = self.run_next(
                current,
                repository_root=repository_root,
                context=context,
            )

            if current.status in {
                AgentSessionStatus.AWAITING_APPROVAL,
                AgentSessionStatus.COMPLETED,
                AgentSessionStatus.FAILED,
                AgentSessionStatus.CANCELLED,
            }:
                return current

            if current == before:
                raise AgentRuntimeExecutionError(
                    "agent runtime made no execution progress"
                )

        raise AgentRuntimeExecutionError(
            "agent runtime exceeded request stage bound"
        )


def required_approval_for_status(
    status: AgentSessionStatus,
) -> ApprovalKind | None:
    """Map runtime boundaries to their expected approval kind."""
    if status is AgentSessionStatus.PLANNING:
        return ApprovalKind.PLAN
    if status is AgentSessionStatus.EXECUTING:
        return ApprovalKind.EDIT
    if status is AgentSessionStatus.REPAIRING:
        return ApprovalKind.REPAIR
    if status is AgentSessionStatus.VERIFYING:
        return ApprovalKind.RELEASE
    return None