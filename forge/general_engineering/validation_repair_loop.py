"""Bounded validation-and-repair orchestration for M5.9 Package 6."""

from __future__ import annotations

from dataclasses import dataclass

from forge.general_engineering.models import (
    ChangePlan,
    EngineeringContext,
    EngineeringRequest,
    RepairProposal,
    ValidationOutcome,
)
from forge.general_engineering.protocols import EngineeringProvider
from forge.general_engineering.repair_service import EngineeringRepairService
from forge.general_engineering.states import ValidationStatus
from forge.general_engineering.validation_executor import EngineeringValidationExecutor


@dataclass(frozen=True)
class ValidationRepairResult:
    final_outcome: ValidationOutcome
    repairs: tuple[RepairProposal, ...]
    completed: bool
    exhausted: bool


class ValidationRepairLoop:
    """Validate, repair only when approved, and stop at the request limit."""

    def __init__(
        self,
        *,
        validation: EngineeringValidationExecutor | None = None,
        repair: EngineeringRepairService | None = None,
    ) -> None:
        self.validation = validation or EngineeringValidationExecutor()
        self.repair = repair or EngineeringRepairService(validation=self.validation)

    def run(
        self,
        *,
        provider: EngineeringProvider,
        request: EngineeringRequest,
        context: EngineeringContext,
        plan: ChangePlan,
        approve_repairs: bool,
    ) -> ValidationRepairResult:
        outcome = self.validation.validate(request=request, plan=plan)
        repairs: list[RepairProposal] = []

        if outcome.status is ValidationStatus.PASSED:
            return ValidationRepairResult(
                final_outcome=outcome,
                repairs=(),
                completed=True,
                exhausted=False,
            )

        if outcome.status is not ValidationStatus.FAILED or not approve_repairs:
            return ValidationRepairResult(
                final_outcome=outcome,
                repairs=(),
                completed=False,
                exhausted=False,
            )

        for attempt_number in range(1, request.max_repair_attempts + 1):
            attempted = self.repair.repair_once(
                provider=provider,
                request=request,
                original_plan=plan,
                previous_context=context,
                validation_outcome=outcome,
                attempt_number=attempt_number,
                approved=True,
            )
            repairs.append(attempted.proposal)
            outcome = attempted.validation_outcome
            if outcome.status is ValidationStatus.PASSED:
                return ValidationRepairResult(
                    final_outcome=outcome,
                    repairs=tuple(repairs),
                    completed=True,
                    exhausted=False,
                )
            if outcome.status is not ValidationStatus.FAILED:
                return ValidationRepairResult(
                    final_outcome=outcome,
                    repairs=tuple(repairs),
                    completed=False,
                    exhausted=False,
                )

        return ValidationRepairResult(
            final_outcome=outcome,
            repairs=tuple(repairs),
            completed=False,
            exhausted=True,
        )


validation_repair_loop = ValidationRepairLoop()
