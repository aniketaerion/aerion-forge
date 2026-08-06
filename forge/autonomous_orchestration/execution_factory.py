"""Factories for one bounded M5.2 execution request."""

from __future__ import annotations

from forge.autonomous_execution.identifiers import (
    execution_request_identifier,
)
from forge.autonomous_execution.models import ExecutionRequest
from forge.autonomous_orchestration.models import (
    MissionSession,
    OrchestrationRequest,
)
from forge.autonomous_runtime.models import MissionStep


def build_execution_request(
    orchestration_request: OrchestrationRequest,
    session: MissionSession,
    step: MissionStep,
) -> ExecutionRequest:
    """Create one deterministic execution request."""
    payload = {
        "mission_id": session.mission_id,
        "plan_id": session.plan_id,
        "step_id": step.step_id,
        "session_version": session.version,
        "cycle_count": session.cycle_count,
    }

    return ExecutionRequest(
        request_id=execution_request_identifier(payload),
        mission_id=session.mission_id,
        plan_id=session.plan_id,
        step_id=step.step_id,
        repository_root=session.repository_root,
        dry_run=orchestration_request.dry_run,
        requested_by=orchestration_request.requested_by,
    )