"""One approved bounded repair attempt for M5.9 Package 6."""

from __future__ import annotations

from dataclasses import dataclass

from forge.general_engineering.edit_synthesis_service import (
    EngineeringEditSynthesisService,
)
from forge.general_engineering.execution_service import EngineeringExecutionService
from forge.general_engineering.models import (
    ChangePlan,
    EngineeringContext,
    EngineeringRequest,
    RepairProposal,
    ValidationOutcome,
)
from forge.general_engineering.protocols import EngineeringProvider
from forge.general_engineering.repair_plan import build_repair_change_plan
from forge.general_engineering.repair_policy import validate_repair_proposal
from forge.general_engineering.repository_grounding import RepositoryGroundingService
from forge.general_engineering.validation_executor import EngineeringValidationExecutor


@dataclass(frozen=True)
class RepairAttemptResult:
    proposal: RepairProposal
    repair_plan: ChangePlan
    validation_outcome: ValidationOutcome


class EngineeringRepairService:
    """Perform one explicitly approved repair within the original plan scope."""

    def __init__(
        self,
        *,
        grounding: RepositoryGroundingService | None = None,
        synthesis: EngineeringEditSynthesisService | None = None,
        execution: EngineeringExecutionService | None = None,
        validation: EngineeringValidationExecutor | None = None,
    ) -> None:
        self.grounding = grounding or RepositoryGroundingService()
        self.synthesis = synthesis or EngineeringEditSynthesisService()
        self.execution = execution or EngineeringExecutionService()
        self.validation = validation or EngineeringValidationExecutor()

    def repair_once(
        self,
        *,
        provider: EngineeringProvider,
        request: EngineeringRequest,
        original_plan: ChangePlan,
        previous_context: EngineeringContext,
        validation_outcome: ValidationOutcome,
        attempt_number: int,
        approved: bool,
    ) -> RepairAttemptResult:
        if not approved:
            raise PermissionError("Repair execution requires explicit approval.")

        proposal = provider.propose_repair(
            request=request,
            context=previous_context,
            plan=original_plan,
            validation_outcome=validation_outcome,
            attempt_number=attempt_number,
        )
        validate_repair_proposal(
            request=request,
            plan=original_plan,
            validation_outcome=validation_outcome,
            proposal=proposal,
            attempt_number=attempt_number,
        )

        refreshed_context = self.grounding.ground(request).context
        repair_plan = build_repair_change_plan(
            original_plan=original_plan,
            refreshed_context=refreshed_context,
            proposal=proposal,
        )
        synthesis = self.synthesis.synthesize(
            provider=provider,
            request=request,
            context=refreshed_context,
            plan=repair_plan,
        )
        self.execution.execute(
            request=request,
            plan=repair_plan,
            change_set=synthesis.change_set,
            approved=True,
            dry_run=False,
        )
        outcome = self.validation.validate(
            request=request,
            plan=original_plan,
        )
        return RepairAttemptResult(
            proposal=proposal,
            repair_plan=repair_plan,
            validation_outcome=outcome,
        )
