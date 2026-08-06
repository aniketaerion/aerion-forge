"""Execution coordination for M5.7."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_execution_v2.authority import (
    ExecutionAuthority,
)
from forge.autonomous_execution_v2.errors import (
    ExecutionContractError,
    ExecutionStateError,
)
from forge.autonomous_execution_v2.graph_builder import (
    ExecutionGraphBuilder,
)
from forge.autonomous_execution_v2.models import (
    ExecutionRun,
    ExecutionStep,
)
from forge.autonomous_execution_v2.scheduler import (
    build_execution_schedule,
)
from forge.autonomous_execution_v2.states import (
    ExecutionRunState,
    ExecutionStepState,
)
from forge.autonomous_execution_v2.step_execution import (
    ControlledStepExecutor,
    StepExecutionOutcome,
    StepToolInvocation,
)


@dataclass(frozen=True, slots=True)
class CoordinatedStepResult:
    """Updated run and one step outcome."""

    run: ExecutionRun
    outcome: StepExecutionOutcome


@dataclass(frozen=True, slots=True)
class AutonomousExecutionCoordinator:
    """Select and execute the next eligible step."""

    graph_builder: ExecutionGraphBuilder
    executor: ControlledStepExecutor

    def execute_next(
        self,
        *,
        run: ExecutionRun,
        invocations_by_step: dict[
            str,
            tuple[StepToolInvocation, ...],
        ],
        authority: ExecutionAuthority,
        attempt_number: int = 1,
    ) -> CoordinatedStepResult:
        if run.state not in {
            ExecutionRunState.READY,
            ExecutionRunState.RUNNING,
        }:
            raise ExecutionStateError(
                "Execution run must be ready or running."
            )

        graph_result = self.graph_builder.build(run)
        states = {
            step.step_id: step.state
            for step in run.steps
        }
        schedule = build_execution_schedule(
            graph=graph_result.graph,
            step_states=states,
        )

        if schedule.next_step_id is None:
            raise ExecutionContractError(
                "Execution run has no eligible step."
            )

        selected = self._step_by_id(
            run.steps,
            schedule.next_step_id,
        )
        outcome = self.executor.execute(
            run_id=run.run_id,
            step=selected,
            attempt_number=attempt_number,
            invocations=invocations_by_step.get(
                selected.step_id,
                (),
            ),
            authority=authority,
        )
        updated_steps = tuple(
            self._updated_step(
                step,
                selected_step_id=selected.step_id,
                outcome=outcome,
            )
            for step in run.steps
        )
        all_succeeded = all(
            step.state is ExecutionStepState.SUCCEEDED
            for step in updated_steps
        )
        updated_run = run.model_copy(
            update={
                "state": (
                    ExecutionRunState.SUCCEEDED
                    if all_succeeded
                    else (
                        ExecutionRunState.RUNNING
                        if outcome.succeeded
                        else ExecutionRunState.FAILED
                    )
                ),
                "steps": updated_steps,
                "current_step_id": (
                    None
                    if all_succeeded
                    else selected.step_id
                ),
                "failure_reason": (
                    outcome.attempt.failure_reason
                    if not outcome.succeeded
                    else None
                ),
            }
        )

        return CoordinatedStepResult(
            run=updated_run,
            outcome=outcome,
        )

    @staticmethod
    def _step_by_id(
        steps: tuple[ExecutionStep, ...],
        step_id: str,
    ) -> ExecutionStep:
        for step in steps:
            if step.step_id == step_id:
                return step

        raise ExecutionContractError(
            f"Unknown execution step: {step_id}"
        )

    @staticmethod
    def _updated_step(
        step: ExecutionStep,
        *,
        selected_step_id: str,
        outcome: StepExecutionOutcome,
    ) -> ExecutionStep:
        if step.step_id != selected_step_id:
            return step

        return step.model_copy(
            update={
                "state": (
                    ExecutionStepState.SUCCEEDED
                    if outcome.succeeded
                    else ExecutionStepState.FAILED
                )
            }
        )