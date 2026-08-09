"""Safety policy for M5.9 Package 4 edit synthesis."""

from __future__ import annotations

from dataclasses import dataclass

from forge.general_engineering.models import ChangePlan, EngineeringRequest
from forge.general_engineering.states import EditOperationType


@dataclass(frozen=True)
class EditSynthesisDecision:
    allowed_paths: tuple[str, ...]
    allowed_requirement_ids: tuple[str, ...]
    allowed_operation_types: tuple[EditOperationType, ...]
    max_operations: int


def build_edit_synthesis_decision(
    request: EngineeringRequest,
    plan: ChangePlan,
    *,
    max_operations: int = 100,
) -> EditSynthesisDecision:
    """Derive the exact authority envelope for proposed edits."""
    if plan.request_id != request.request_id:
        raise ValueError("Change plan belongs to another engineering request.")

    allowed_paths = tuple(item.path for item in plan.file_changes)
    allowed_requirements = tuple(
        item.requirement_id for item in plan.requirements
    )
    allowed_operations = tuple(
        sorted(
            {
                operation
                for file_change in plan.file_changes
                for operation in file_change.intended_operations
            },
            key=lambda item: item.value,
        )
    )

    return EditSynthesisDecision(
        allowed_paths=allowed_paths,
        allowed_requirement_ids=allowed_requirements,
        allowed_operation_types=allowed_operations,
        max_operations=max_operations,
    )