"""Coordinate one bounded autonomous mission iteration."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_execution.planner import (
    AutonomousExecutionPlanner,
)
from forge.autonomous_orchestration.budget_monitor import (
    evaluate_budgets,
)
from forge.autonomous_orchestration.execution_factory import (
    build_execution_request,
)
from forge.autonomous_orchestration.identifiers import (
    orchestration_iteration_identifier,
)
from forge.autonomous_orchestration.models import (
    MissionSession,
    OrchestrationIteration,
    OrchestrationRequest,
    utc_now,
)
from forge.autonomous_orchestration.plan_loader import (
    InMemoryApprovedPlanStore,
)
from forge.autonomous_orchestration.policies import (
    AutonomousOrchestrationPolicy,
)
from forge.autonomous_orchestration.progress import evaluate_progress
from forge.autonomous_orchestration.states import IterationOutcome
from forge.autonomous_runtime.models import AutonomousMission


@dataclass(frozen=True, slots=True)
class CoordinationResult:
    """Result of one orchestration coordination cycle."""

    session: MissionSession
    iteration: OrchestrationIteration
    execution_request_id: str | None
    selected_step_id: str | None


@dataclass(slots=True)
class MissionStepCoordinator:
    """Select one next step and prepare one M5.2 execution request."""

    plan_store: InMemoryApprovedPlanStore
    planner: AutonomousExecutionPlanner
    policy: AutonomousOrchestrationPolicy

    def coordinate(
        self,
        request: OrchestrationRequest,
        session: MissionSession,
        mission: AutonomousMission,
    ) -> CoordinationResult:
        plan = self.plan_store.load(
            session.mission_id,
            expected_plan_id=session.plan_id,
            expected_version=session.plan_version,
        )

        budget = evaluate_budgets(session, self.policy)
        if not budget.allowed:
            iteration = self._iteration(
                session=session,
                outcome=IterationOutcome.ESCALATED,
                selected_step_id=None,
                execution_request_id=None,
            )
            return CoordinationResult(
                session=session,
                iteration=iteration,
                execution_request_id=None,
                selected_step_id=None,
            )

        progress = evaluate_progress(session, plan)
        if progress.complete:
            iteration = self._iteration(
                session=session,
                outcome=IterationOutcome.MISSION_COMPLETED,
                selected_step_id=None,
                execution_request_id=None,
            )
            return CoordinationResult(
                session=session,
                iteration=iteration,
                execution_request_id=None,
                selected_step_id=None,
            )

        selection = self.planner.select_next(
            mission,
            plan,
            completed_step_ids=frozenset(
                session.completed_step_ids
            ),
        )

        if selection.step is None:
            iteration = self._iteration(
                session=session,
                outcome=IterationOutcome.NO_ELIGIBLE_STEP,
                selected_step_id=None,
                execution_request_id=None,
            )
            return CoordinationResult(
                session=session,
                iteration=iteration,
                execution_request_id=None,
                selected_step_id=None,
            )

        execution_request = build_execution_request(
            request,
            session,
            selection.step,
        )
        updated_session = session.model_copy(
            update={
                "current_step_id": selection.step.step_id,
                "cycle_count": session.cycle_count + 1,
                "version": session.version + 1,
                "updated_at": utc_now(),
            }
        )
        iteration = self._iteration(
            session=updated_session,
            outcome=IterationOutcome.STEP_SELECTED,
            selected_step_id=selection.step.step_id,
            execution_request_id=execution_request.request_id,
        )

        return CoordinationResult(
            session=updated_session,
            iteration=iteration,
            execution_request_id=execution_request.request_id,
            selected_step_id=selection.step.step_id,
        )

    @staticmethod
    def _iteration(
        *,
        session: MissionSession,
        outcome: IterationOutcome,
        selected_step_id: str | None,
        execution_request_id: str | None,
    ) -> OrchestrationIteration:
        sequence = session.cycle_count + 1
        payload = {
            "session_id": session.session_id,
            "sequence": sequence,
            "selected_step_id": selected_step_id,
            "execution_request_id": execution_request_id,
            "outcome": outcome.value,
        }

        return OrchestrationIteration(
            iteration_id=orchestration_iteration_identifier(payload),
            session_id=session.session_id,
            sequence=sequence,
            mission_version_before=session.version,
            selected_step_id=selected_step_id,
            execution_request_id=execution_request_id,
            outcome=outcome,
        )