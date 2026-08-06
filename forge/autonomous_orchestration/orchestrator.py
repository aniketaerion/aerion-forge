"""Top-level bounded autonomous mission orchestrator."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from forge.autonomous_execution.models import ExecutionRequest
from forge.autonomous_execution.runtime import StepExecutionOutcome
from forge.autonomous_orchestration.coordinator import (
    CoordinationResult,
    MissionStepCoordinator,
)
from forge.autonomous_orchestration.iteration_service import (
    OrchestrationIterationService,
)
from forge.autonomous_orchestration.models import (
    MissionSession,
    OrchestrationIteration,
    OrchestrationRequest,
)
from forge.autonomous_runtime.models import AutonomousMission

ExecutionRunner = Callable[[ExecutionRequest], StepExecutionOutcome]


@dataclass(frozen=True, slots=True)
class OrchestrationCycleResult:
    """Result of one bounded orchestration cycle."""

    session: MissionSession
    coordination: CoordinationResult
    iteration: OrchestrationIteration
    execution_performed: bool


@dataclass(slots=True)
class AutonomousMissionOrchestrator:
    """Coordinate and process at most one execution per call."""

    coordinator: MissionStepCoordinator
    iteration_service: OrchestrationIterationService
    execution_runner: ExecutionRunner

    def run_cycle(
        self,
        request: OrchestrationRequest,
        session: MissionSession,
        mission: AutonomousMission,
        execution_request: ExecutionRequest | None = None,
    ) -> OrchestrationCycleResult:
        coordination = self.coordinator.coordinate(
            request,
            session,
            mission,
        )

        if coordination.execution_request_id is None:
            return OrchestrationCycleResult(
                session=coordination.session,
                coordination=coordination,
                iteration=coordination.iteration,
                execution_performed=False,
            )

        if execution_request is None:
            raise ValueError(
                "Execution request is required for selected step."
            )

        outcome = self.execution_runner(execution_request)
        updated, iteration = self.iteration_service.process(
            coordination.session,
            outcome,
            mission_version_before=mission.version,
            execution_request_id=execution_request.request_id,
        )

        return OrchestrationCycleResult(
            session=updated,
            coordination=coordination,
            iteration=iteration,
            execution_performed=True,
        )