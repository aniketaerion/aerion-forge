"""Bounded repair authorization for M5.9 Package 6."""

from __future__ import annotations

from forge.general_engineering.errors import EngineeringRepairError
from forge.general_engineering.models import (
    ChangePlan,
    EngineeringRequest,
    RepairProposal,
    ValidationOutcome,
)
from forge.general_engineering.states import ValidationStatus


def validate_repair_proposal(
    *,
    request: EngineeringRequest,
    plan: ChangePlan,
    validation_outcome: ValidationOutcome,
    proposal: RepairProposal,
    attempt_number: int,
) -> None:
    if validation_outcome.status is not ValidationStatus.FAILED:
        raise EngineeringRepairError("Repair is permitted only after failed validation.")
    if proposal.request_id != request.request_id:
        raise EngineeringRepairError("Repair proposal belongs to another request.")
    if proposal.validation_outcome_id != validation_outcome.outcome_id:
        raise EngineeringRepairError("Repair proposal references another validation outcome.")
    if proposal.attempt_number != attempt_number:
        raise EngineeringRepairError("Repair attempt number mismatch.")
    if attempt_number > request.max_repair_attempts:
        raise EngineeringRepairError("Maximum repair attempts exceeded.")

    planned_paths = {item.path for item in plan.file_changes}
    repair_paths = set(proposal.target_paths)
    if not repair_paths.issubset(planned_paths):
        raise EngineeringRepairError(
            "Repair proposal expands beyond the approved change-plan scope."
        )
