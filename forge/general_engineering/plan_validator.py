"""Change-plan validation for M5.9 Package 3."""

from __future__ import annotations

from forge.general_engineering.errors import EngineeringContractError
from forge.general_engineering.models import (
    ChangePlan,
    ChangeSpecification,
    EngineeringContext,
    EngineeringRequest,
)


def validate_change_plan(
    *,
    request: EngineeringRequest,
    specification: ChangeSpecification,
    context: EngineeringContext,
    plan: ChangePlan,
) -> None:
    """Fail closed when a plan escapes request, requirements, or evidence."""
    if plan.request_id != request.request_id:
        raise EngineeringContractError("Plan belongs to another engineering request.")

    expected_requirements = {item.requirement_id for item in specification.requirements}
    planned_requirements = {item.requirement_id for item in plan.requirements}
    if expected_requirements != planned_requirements:
        raise EngineeringContractError(
            "Plan does not cover exactly the normalized requirements."
        )

    relevant_paths = {item.path for item in context.relevant_files}
    planned_paths = {item.path for item in plan.file_changes}
    if not planned_paths.issubset(relevant_paths):
        raise EngineeringContractError(
            "Plan includes targets not justified by repository grounding."
        )

    context_evidence = {item.evidence_id for item in context.evidence}
    if not set(plan.evidence_ids).issubset(context_evidence):
        raise EngineeringContractError(
            "Plan references evidence outside the engineering context."
        )

    forbidden = set(request.forbidden_paths)
    for path in planned_paths:
        if any(
            path == item or path.startswith(f"{item.rstrip('/')}/")
            for item in forbidden
        ):
            raise EngineeringContractError(
                f"Plan includes forbidden repository path: {path}"
            )