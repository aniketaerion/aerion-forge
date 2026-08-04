"""Validation and bounded repair orchestration."""

from __future__ import annotations

from pathlib import Path

from forge.validation_repair.errors import RepairAttemptLimitError, RepairPlanningError
from forge.validation_repair.identifiers import repair_session_identifier
from forge.validation_repair.models import (
    RepairAttempt,
    RepairCandidate,
    RepairReport,
    RepairSession,
    RepairStatus,
    ValidationCommand,
    ValidationRun,
    ValidationStatus,
)
from forge.validation_repair.planner import plan_repairs
from forge.validation_repair.policies import ValidationRepairPolicy
from forge.validation_repair.runner import run_validation


class ValidationRepairService:
    """Run validators and create bounded repair-session evidence."""

    def __init__(self, policy: ValidationRepairPolicy | None = None) -> None:
        self.policy = policy or ValidationRepairPolicy()

    def validate(
        self,
        repository_root: Path,
        commands: tuple[ValidationCommand, ...],
    ) -> tuple[ValidationRun, ...]:
        return tuple(
            run_validation(repository_root, command, self.policy)
            for command in commands
        )

    def plan(
        self,
        validation_runs: tuple[ValidationRun, ...],
    ) -> tuple[RepairCandidate, ...]:
        findings = tuple(
            finding
            for run in validation_runs
            if run.status is not ValidationStatus.PASSED
            for finding in run.findings
        )
        candidates = plan_repairs(findings)
        if findings and not candidates:
            raise RepairPlanningError(
                "validation findings could not be mapped to target paths"
            )
        return candidates

    def create_session(
        self,
        repository_root: Path,
        candidates: tuple[RepairCandidate, ...],
        *,
        approved: bool = False,
    ) -> RepairSession:
        root = self.policy.resolve_repository(repository_root)
        if len(candidates) > self.policy.max_repair_attempts:
            raise RepairAttemptLimitError(
                "candidate count exceeds configured repair-attempt limit"
            )
        attempts = tuple(
            RepairAttempt(
                attempt_number=index,
                candidate=candidate,
                status=RepairStatus.PLANNED,
            )
            for index, candidate in enumerate(candidates, start=1)
        )
        return RepairSession(
            session_id=repair_session_identifier(
                {
                    "repository_root": str(root),
                    "candidate_ids": [c.candidate_id for c in candidates],
                    "approved": approved,
                }
            ),
            repository_root=str(root),
            max_attempts=self.policy.max_repair_attempts,
            attempts=attempts,
            approved=approved,
        )

    def build_report(
        self,
        session: RepairSession,
        validation_runs: tuple[ValidationRun, ...],
    ) -> RepairReport:
        succeeded = bool(validation_runs) and all(
            run.status is ValidationStatus.PASSED for run in validation_runs
        )
        return RepairReport(
            session_id=session.session_id,
            repository_root=session.repository_root,
            succeeded=succeeded,
            attempts=session.attempts,
            final_validation_runs=validation_runs,
            messages=("No repair has been applied in Package 3.",),
        )