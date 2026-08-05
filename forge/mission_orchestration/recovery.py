"""Recovery, resume and cancellation for M3.6 Mission Orchestration."""

from __future__ import annotations

from pathlib import Path

from forge.mission_orchestration.errors import (
    MissionCancellationError,
    MissionRecoveryError,
)
from forge.mission_orchestration.models import (
    MissionCheckpoint,
    MissionExecution,
    MissionStatus,
    StageRun,
    StageStatus,
)
from forge.mission_orchestration.policies import MissionOrchestrationPolicy
from forge.mission_orchestration.service import repository_fingerprint


class MissionRecoveryService:
    """Validate and reconstruct resumable mission state."""

    def __init__(
        self,
        policy: MissionOrchestrationPolicy | None = None,
    ) -> None:
        self.policy = policy or MissionOrchestrationPolicy()

    def validate_resume(
        self,
        execution: MissionExecution,
        checkpoint: MissionCheckpoint,
    ) -> None:
        """Reject resume when checkpoint or repository state is stale."""
        if not self.policy.allow_resume:
            raise MissionRecoveryError("mission resume is disabled by policy")

        if execution.request.mission_id != checkpoint.mission_id:
            raise MissionRecoveryError("checkpoint mission ID does not match")

        if execution.workflow.workflow_id != checkpoint.workflow_id:
            raise MissionRecoveryError("checkpoint workflow ID does not match")

        current_fingerprint = repository_fingerprint(
            Path(execution.request.repository_root),
            execution.request.requested_paths,
        )

        if (
            self.policy.stop_on_repository_state_change
            and current_fingerprint != checkpoint.repository_fingerprint
        ):
            raise MissionRecoveryError(
                "repository fingerprint changed after checkpoint"
            )

    def resume(
        self,
        execution: MissionExecution,
        checkpoint: MissionCheckpoint,
    ) -> MissionExecution:
        """Reconstruct a resumable execution from one checkpoint."""
        self.validate_resume(execution, checkpoint)

        if checkpoint.status in {
            MissionStatus.COMPLETED,
            MissionStatus.CANCELLED,
            MissionStatus.FAILED,
        }:
            raise MissionRecoveryError(
                f"terminal mission cannot resume: {checkpoint.status.value}"
            )

        return execution.model_copy(
            update={
                "status": MissionStatus.RESUMING,
                "stage_runs": checkpoint.stage_runs,
                "current_stage_id": checkpoint.current_stage_id,
                "checkpoint_id": checkpoint.checkpoint_id,
                "failure_reason": None,
            }
        )

    def cancel(
        self,
        execution: MissionExecution,
        *,
        reason: str,
    ) -> MissionExecution:
        """Cancel a non-terminal mission and retain stage evidence."""
        if not self.policy.allow_cancellation:
            raise MissionCancellationError(
                "mission cancellation is disabled by policy"
            )

        if execution.status in {
            MissionStatus.COMPLETED,
            MissionStatus.CANCELLED,
            MissionStatus.FAILED,
        }:
            raise MissionCancellationError(
                f"terminal mission cannot be cancelled: {execution.status.value}"
            )

        if not reason.strip():
            raise MissionCancellationError("cancellation reason is required")

        cancelled_runs = tuple(
            self._cancel_running_stage(run)
            for run in execution.stage_runs
        )

        return execution.model_copy(
            update={
                "status": MissionStatus.CANCELLED,
                "stage_runs": cancelled_runs,
                "current_stage_id": None,
                "failure_reason": reason.strip(),
            }
        )

    @staticmethod
    def _cancel_running_stage(run: StageRun) -> StageRun:
        if run.status not in {
            StageStatus.RUNNING,
            StageStatus.READY,
            StageStatus.AWAITING_APPROVAL,
        }:
            return run

        return run.model_copy(
            update={
                "status": StageStatus.CANCELLED,
                "errors": (*run.errors, "mission cancelled"),
            }
        )