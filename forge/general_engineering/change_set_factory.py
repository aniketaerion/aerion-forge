"""Canonical GeneratedChangeSet construction for M5.9 Package 4."""

from __future__ import annotations

from forge.general_engineering.identifiers import change_set_identifier
from forge.general_engineering.models import (
    ChangePlan,
    EditOperation,
    GeneratedChangeSet,
)


def build_generated_change_set(
    *,
    plan: ChangePlan,
    operations: tuple[EditOperation, ...],
) -> GeneratedChangeSet:
    """Build a deterministic, canonically ordered GeneratedChangeSet."""
    ordered = tuple(
        sorted(
            operations,
            key=lambda item: (
                item.order,
                item.target_path,
                item.operation_id,
            ),
        )
    )
    evidence_ids = tuple(
        sorted(
            {
                evidence_id
                for operation in ordered
                for evidence_id in operation.evidence_ids
            }
        )
    )
    payload = {
        "plan_id": plan.plan_id,
        "operations": tuple(
            {
                "operation_id": operation.operation_id,
                "operation_type": operation.operation_type.value,
                "target_path": operation.target_path,
                "target_symbol": operation.target_symbol,
                "source_fingerprint": operation.source_fingerprint,
                "rename_target_path": operation.rename_target_path,
                "originating_requirement_id": (
                    operation.originating_requirement_id
                ),
                "order": operation.order,
            }
            for operation in ordered
        ),
        "evidence_ids": evidence_ids,
    }

    return GeneratedChangeSet(
        change_set_id=change_set_identifier(payload),
        plan_id=plan.plan_id,
        operations=ordered,
        evidence_ids=evidence_ids,
    )