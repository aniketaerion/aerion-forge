"""Mission orchestration service for M3.6."""

from __future__ import annotations

import hashlib
from pathlib import Path

from forge.mission_orchestration.executor import MissionExecutor
from forge.mission_orchestration.identifiers import (
    checkpoint_identifier,
    mission_identifier,
)
from forge.mission_orchestration.models import (
    MissionApproval,
    MissionCheckpoint,
    MissionExecution,
    MissionRequest,
    MissionStatus,
)
from forge.mission_orchestration.policies import MissionOrchestrationPolicy
from forge.mission_orchestration.store import MissionCheckpointStore
from forge.mission_orchestration.workflow import build_default_workflow


def repository_fingerprint(
    repository_root: Path,
    paths: tuple[str, ...],
) -> str:
    """Fingerprint only the mission's bounded target paths."""
    root = repository_root.resolve()
    digest = hashlib.sha256()

    for relative_path in sorted(paths):
        target = (root / relative_path).resolve()
        target.relative_to(root)
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\x00")
        if target.is_file():
            digest.update(target.read_bytes())
        digest.update(b"\x00")
    return digest.hexdigest()


class MissionOrchestrationService:
    """Create, execute and checkpoint engineering missions."""

    def __init__(
        self,
        *,
        policy: MissionOrchestrationPolicy | None = None,
        executor: MissionExecutor | None = None,
    ) -> None:
        self.policy = policy or MissionOrchestrationPolicy()
        self.executor = executor or MissionExecutor(policy=self.policy)

    def create_request(
        self,
        *,
        repository_root: Path,
        objective: str,
        requested_paths: tuple[str, ...],
        constraints: tuple[str, ...] = (),
        requested_outcomes: tuple[str, ...] = (),
    ) -> MissionRequest:
        """Create a deterministic bounded mission request."""
        root = self.policy.resolve_repository(repository_root)
        normalized = self.policy.validate_paths(requested_paths)
        mission_id = mission_identifier(
            {
                "repository_root": str(root),
                "objective": objective,
                "requested_paths": normalized,
                "constraints": constraints,
                "requested_outcomes": requested_outcomes,
            }
        )
        return MissionRequest(
            mission_id=mission_id,
            repository_root=str(root),
            objective=objective,
            requested_paths=normalized,
            constraints=constraints,
            requested_outcomes=requested_outcomes,
        )

    def create_execution(
        self,
        request: MissionRequest,
    ) -> MissionExecution:
        """Create a validated mission execution."""
        workflow = build_default_workflow(
            request,
            policy=self.policy,
        )
        return MissionExecution(
            request=request,
            workflow=workflow,
            status=MissionStatus.READY,
        )

    def run_next(
        self,
        execution: MissionExecution,
        *,
        approval: MissionApproval | None = None,
    ) -> MissionExecution:
        """Execute exactly one workflow stage."""
        return self.executor.execute_next(
            execution,
            approval=approval,
        )

    def checkpoint(
        self,
        execution: MissionExecution,
        store: MissionCheckpointStore,
    ) -> MissionCheckpoint:
        """Persist one resumable checkpoint."""
        fingerprint = repository_fingerprint(
            Path(execution.request.repository_root),
            execution.request.requested_paths,
        )
        checkpoint = MissionCheckpoint(
            checkpoint_id=checkpoint_identifier(
                {
                    "mission_id": execution.request.mission_id,
                    "workflow_id": execution.workflow.workflow_id,
                    "status": execution.status.value,
                    "stage_run_ids": [
                        run.stage_run_id for run in execution.stage_runs
                    ],
                    "repository_fingerprint": fingerprint,
                }
            ),
            mission_id=execution.request.mission_id,
            workflow_id=execution.workflow.workflow_id,
            status=execution.status,
            stage_runs=execution.stage_runs,
            current_stage_id=execution.current_stage_id,
            repository_fingerprint=fingerprint,
        )
        store.save(checkpoint)
        return checkpoint