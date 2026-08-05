"""Deterministic stage execution for M3.6 Mission Orchestration."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from forge.mission_orchestration.errors import (
    MissionDependencyError,
    MissionExecutionError,
    MissionPolicyViolationError,
)
from forge.mission_orchestration.identifiers import stage_run_identifier
from forge.mission_orchestration.models import (
    MissionApproval,
    MissionExecution,
    MissionStatus,
    StageDefinition,
    StageResult,
    StageRun,
    StageStatus,
)
from forge.mission_orchestration.policies import MissionOrchestrationPolicy

StageHandler = Callable[[MissionExecution, StageDefinition], StageResult]


class MissionExecutor:
    """Execute one deterministic workflow stage at a time."""

    def __init__(
        self,
        *,
        policy: MissionOrchestrationPolicy | None = None,
        handlers: dict[str, StageHandler] | None = None,
    ) -> None:
        self.policy = policy or MissionOrchestrationPolicy()
        self.handlers = handlers or {}

    def _successful_stage_ids(
        self,
        execution: MissionExecution,
    ) -> set[str]:
        return {
            run.stage_id
            for run in execution.stage_runs
            if run.status in {StageStatus.SUCCEEDED, StageStatus.SKIPPED}
        }

    def next_stage(
        self,
        execution: MissionExecution,
    ) -> StageDefinition | None:
        """Return the next dependency-ready stage."""
        completed = self._successful_stage_ids(execution)

        for stage in execution.workflow.stages:
            if stage.stage_id in completed:
                continue
            if set(stage.dependencies).issubset(completed):
                return stage
        return None

    def execute_next(
        self,
        execution: MissionExecution,
        *,
        approval: MissionApproval | None = None,
    ) -> MissionExecution:
        """Execute the next ready stage and return updated mission state."""
        if len(execution.stage_runs) >= self.policy.max_total_stage_runs:
            raise MissionPolicyViolationError(
                "mission exceeded maximum total stage runs"
            )

        stage = self.next_stage(execution)
        if stage is None:
            return execution.model_copy(
                update={
                    "status": MissionStatus.COMPLETED,
                    "current_stage_id": None,
                }
            )

        attempts = 1 + sum(
            1
            for run in execution.stage_runs
            if (
                run.stage_id == stage.stage_id
                and run.status is not StageStatus.AWAITING_APPROVAL
            )
        )
        self.policy.validate_stage_attempts(attempts)
        if attempts > stage.max_attempts:
            raise MissionPolicyViolationError(
                f"stage exceeded max attempts: {stage.stage_id}"
            )

        approval_evidence = approval or MissionApproval()
        if stage.approval_required and approval_evidence.decision.value != "approved":
            run = StageRun(
                stage_run_id=stage_run_identifier(
                    {
                        "mission_id": execution.request.mission_id,
                        "stage_id": stage.stage_id,
                        "attempt": attempts,
                        "status": StageStatus.AWAITING_APPROVAL.value,
                    }
                ),
                stage_id=stage.stage_id,
                attempt_number=attempts,
                status=StageStatus.AWAITING_APPROVAL,
                approval=approval_evidence,
            )
            return execution.model_copy(
                update={
                    "status": MissionStatus.AWAITING_APPROVAL,
                    "current_stage_id": stage.stage_id,
                    "stage_runs": (*execution.stage_runs, run),
                }
            )

        started = datetime.now(UTC)
        handler = self.handlers.get(stage.stage_id)
        if handler is None:
            result = StageResult(
                messages=(f"Stage completed: {stage.stage_id}",)
            )
        else:
            try:
                result = handler(execution, stage)
            except Exception as exc:
                raise MissionExecutionError(
                    f"stage failed: {stage.stage_id}: {exc}"
                ) from exc

        run = StageRun(
            stage_run_id=stage_run_identifier(
                {
                    "mission_id": execution.request.mission_id,
                    "stage_id": stage.stage_id,
                    "attempt": attempts,
                    "status": StageStatus.SUCCEEDED.value,
                }
            ),
            stage_id=stage.stage_id,
            attempt_number=attempts,
            status=StageStatus.SUCCEEDED,
            started_at=started,
            completed_at=datetime.now(UTC),
            approval=approval_evidence,
            result=result,
        )
        updated = execution.model_copy(
            update={
                "status": MissionStatus.RUNNING,
                "current_stage_id": stage.stage_id,
                "stage_runs": (*execution.stage_runs, run),
            }
        )

        if self.next_stage(updated) is None:
            return updated.model_copy(
                update={
                    "status": MissionStatus.COMPLETED,
                    "current_stage_id": None,
                }
            )
        return updated

    def validate_dependencies(self, execution: MissionExecution) -> None:
        """Reject stage runs that violate dependency ordering."""
        completed: set[str] = set()
        by_id = {
            stage.stage_id: stage
            for stage in execution.workflow.stages
        }

        for run in execution.stage_runs:
            try:
                stage = by_id[run.stage_id]
            except KeyError as exc:
                raise MissionDependencyError(
                    f"unknown stage run: {run.stage_id}"
                ) from exc
            if not set(stage.dependencies).issubset(completed):
                raise MissionDependencyError(
                    f"stage ran before dependencies: {stage.stage_id}"
                )
            if run.status in {StageStatus.SUCCEEDED, StageStatus.SKIPPED}:
                completed.add(run.stage_id)
