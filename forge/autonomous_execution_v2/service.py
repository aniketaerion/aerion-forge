"""Application service for M5.7 autonomous execution."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_execution_v2.authority import ExecutionAuthority
from forge.autonomous_execution_v2.coordinator import (
    AutonomousExecutionCoordinator,
    CoordinatedStepResult,
)
from forge.autonomous_execution_v2.models import ExecutionRun
from forge.autonomous_execution_v2.recovery import decide_recovery
from forge.autonomous_execution_v2.repository import InMemoryExecutionRepository
from forge.autonomous_execution_v2.states import (
    ExecutionRunState,
    RecoveryAction,
)
from forge.autonomous_execution_v2.step_execution import StepToolInvocation


@dataclass(slots=True)
class AutonomousExecutionService:
    """Persisted execution, recovery, and history service."""

    coordinator: AutonomousExecutionCoordinator
    repository: InMemoryExecutionRepository

    def register_run(self, run: ExecutionRun) -> None:
        self.repository.put_run(run)

    def execute_next(
        self,
        *,
        run_id: str,
        invocations_by_step: dict[str, tuple[StepToolInvocation, ...]],
        authority: ExecutionAuthority,
        attempt_number: int = 1,
    ) -> CoordinatedStepResult:
        run = self.repository.get_run(run_id)

        if run is None:
            raise KeyError(f"Unknown execution run: {run_id}")

        result = self.coordinator.execute_next(
            run=run,
            invocations_by_step=invocations_by_step,
            authority=authority,
            attempt_number=attempt_number,
        )
        self.repository.put_run(result.run)
        self.repository.put_attempt(result.outcome.attempt)

        for evidence in result.outcome.evidence:
            self.repository.put_evidence(evidence)

        if not result.outcome.succeeded:
            attempts = tuple(
                attempt
                for attempt in self.repository.attempts_for_run(run_id)
                if attempt.step_id == result.outcome.step_id
            )
            decision = decide_recovery(
                run_id=run_id,
                step_id=result.outcome.step_id,
                attempt=result.outcome.attempt,
                attempts_for_step=attempts,
                policy=self.coordinator.executor.policy,
            )
            self.repository.put_recovery_decision(decision)

            if decision.action is RecoveryAction.RETRY:
                recovering = result.run.model_copy(
                    update={"state": ExecutionRunState.RECOVERING}
                )
                self.repository.put_run(recovering)
                return CoordinatedStepResult(
                    run=recovering,
                    outcome=result.outcome,
                )

        return result