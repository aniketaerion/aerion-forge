"""Construct evidence-refreshed bounded repair plans."""

from __future__ import annotations

from forge.general_engineering.errors import EngineeringRepairError
from forge.general_engineering.identifiers import change_plan_identifier
from forge.general_engineering.models import (
    ChangePlan,
    EngineeringContext,
    RepairProposal,
)


def build_repair_change_plan(
    *,
    original_plan: ChangePlan,
    refreshed_context: EngineeringContext,
    proposal: RepairProposal,
) -> ChangePlan:
    relevant = {item.path: item for item in refreshed_context.relevant_files}
    original = {item.path: item for item in original_plan.file_changes}
    selected = []

    for path in proposal.target_paths:
        if path not in original:
            raise EngineeringRepairError(f"Repair target is outside original plan: {path}")
        grounded = relevant.get(path)
        if grounded is None:
            raise EngineeringRepairError(f"Repair target is no longer repository-grounded: {path}")
        selected.append(
            original[path].model_copy(
                update={
                    "evidence_ids": grounded.evidence_ids,
                    "rationale": (
                        f"Repair attempt {proposal.attempt_number}: {proposal.diagnosis}"
                    ),
                }
            )
        )

    evidence_ids = tuple(
        sorted({evidence_id for item in selected for evidence_id in item.evidence_ids})
    )
    payload = {
        "original_plan_id": original_plan.plan_id,
        "repair_id": proposal.repair_id,
        "attempt_number": proposal.attempt_number,
        "paths": proposal.target_paths,
        "evidence_ids": evidence_ids,
    }

    return original_plan.model_copy(
        update={
            "plan_id": change_plan_identifier(payload),
            "file_changes": tuple(selected),
            "evidence_ids": evidence_ids,
            "expected_effect": (f"Repair validation failure: {proposal.diagnosis}"),
        }
    )
