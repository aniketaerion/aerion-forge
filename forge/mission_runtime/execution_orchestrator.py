"""M5.8 orchestration over the existing M5.7 execution service."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_execution_v2.authority import ExecutionAuthority
from forge.autonomous_execution_v2.models import ExecutionRun
from forge.autonomous_execution_v2.service import (
    AutonomousExecutionService,
)
from forge.autonomous_execution_v2.step_execution import (
    StepToolInvocation,
)


@dataclass(frozen=True, slots=True)
class MissionExecutionResult:
    run: ExecutionRun
    executed_step_ids: tuple[str, ...]
    evidence_references: tuple[str, ...]


@dataclass(slots=True)
class MissionExecutionOrchestrator:
    """Register and advance M5.7 execution runs."""

    service: AutonomousExecutionService

    def register(
        self,
        run: ExecutionRun,
    ) -> None:
        self.service.register_run(run)

    def execute_next(
        self,
        *,
        run_id: str,
        invocations_by_step: dict[
            str,
            tuple[StepToolInvocation, ...],
        ],
        authority: ExecutionAuthority,
        attempt_number: int = 1,
    ) -> MissionExecutionResult:
        result = self.service.execute_next(
            run_id=run_id,
            invocations_by_step=invocations_by_step,
            authority=authority,
            attempt_number=attempt_number,
        )

        evidence_references = tuple(
            f"execution-evidence:{item.evidence_id}"
            for item in result.outcome.evidence
        )

        return MissionExecutionResult(
            run=result.run,
            executed_step_ids=(
                result.outcome.step_id,
            ),
            evidence_references=evidence_references,
        )