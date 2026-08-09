"""Validation for provider-proposed edit change sets."""

from __future__ import annotations

from forge.general_engineering.edit_evidence import (
    context_evidence_ids,
    evidence_fingerprint_map,
)
from forge.general_engineering.edit_synthesis_policy import (
    build_edit_synthesis_decision,
)
from forge.general_engineering.errors import EngineeringContractError
from forge.general_engineering.models import (
    ChangePlan,
    EngineeringContext,
    EngineeringRequest,
    GeneratedChangeSet,
)
from forge.general_engineering.states import EditOperationType

_DESTRUCTIVE_OPERATIONS = frozenset(
    {
        EditOperationType.REPLACE,
        EditOperationType.DELETE,
        EditOperationType.RENAME,
    }
)


def validate_generated_change_set(
    *,
    request: EngineeringRequest,
    context: EngineeringContext,
    plan: ChangePlan,
    change_set: GeneratedChangeSet,
) -> None:
    """Fail closed if an edit proposal escapes the approved change plan."""
    if change_set.plan_id != plan.plan_id:
        raise EngineeringContractError(
            "Generated change set belongs to another change plan."
        )

    decision = build_edit_synthesis_decision(request, plan)
    if len(change_set.operations) > decision.max_operations:
        raise EngineeringContractError(
            "Generated change set exceeds the maximum operation count."
        )

    allowed_paths = set(decision.allowed_paths)
    allowed_requirements = set(decision.allowed_requirement_ids)
    allowed_operation_types = set(decision.allowed_operation_types)
    evidence_ids = context_evidence_ids(context)
    fingerprints = evidence_fingerprint_map(context)

    for operation in change_set.operations:
        if operation.target_path not in allowed_paths:
            raise EngineeringContractError(
                f"Edit target is outside approved plan scope: "
                f"{operation.target_path}"
            )

        if operation.originating_requirement_id not in allowed_requirements:
            raise EngineeringContractError(
                "Edit operation references a requirement outside the plan."
            )

        if operation.operation_type not in allowed_operation_types:
            raise EngineeringContractError(
                "Edit operation type is not authorized by the file plan."
            )

        if not set(operation.evidence_ids).issubset(evidence_ids):
            raise EngineeringContractError(
                "Edit operation references evidence outside the engineering context."
            )

        if operation.operation_type in _DESTRUCTIVE_OPERATIONS:
            expected = fingerprints.get(operation.target_path)
            if not expected:
                raise EngineeringContractError(
                    "Destructive edit lacks a grounded source fingerprint."
                )
            if operation.source_fingerprint != expected:
                raise EngineeringContractError(
                    f"Source fingerprint mismatch for {operation.target_path}."
                )

        if operation.operation_type is EditOperationType.RENAME:
            assert operation.rename_target_path is not None
            if operation.rename_target_path not in allowed_paths:
                raise EngineeringContractError(
                    "Rename destination is outside approved plan scope."
                )