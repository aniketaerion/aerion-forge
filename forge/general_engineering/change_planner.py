"""Repository-grounded deterministic change planning for M5.9 Package 3."""

from __future__ import annotations

from forge.general_engineering.identifiers import change_plan_identifier
from forge.general_engineering.models import (
    ChangePlan,
    ChangeSpecification,
    EngineeringContext,
    EngineeringRequest,
    FileChangePlan,
)
from forge.general_engineering.planning_policy import select_planning_targets
from forge.general_engineering.states import EditOperationType, EngineeringRisk
from forge.general_engineering.validation_planner import build_validation_plan


def _file_risk(path: str) -> EngineeringRisk:
    lowered = path.casefold()
    if lowered.startswith("tests/") or "/test" in lowered:
        return EngineeringRisk.LOW
    if any(token in lowered for token in ("migration", "schema", "security", "auth")):
        return EngineeringRisk.HIGH
    return EngineeringRisk.MEDIUM


def build_change_plan(
    *,
    request: EngineeringRequest,
    specification: ChangeSpecification,
    context: EngineeringContext,
) -> ChangePlan:
    """Create an evidence-backed, non-mutating ChangePlan."""
    if request.request_id != specification.request_id:
        raise ValueError("Specification does not belong to the engineering request.")
    if request.request_id != context.request_id:
        raise ValueError("Engineering context does not belong to the request.")

    decision = select_planning_targets(request, context.relevant_files)
    by_path = {item.path: item for item in context.relevant_files}
    file_changes: list[FileChangePlan] = []

    for path in decision.selected_paths:
        relevant = by_path[path]
        symbols = tuple(symbol.name for symbol in relevant.symbols)
        file_changes.append(
            FileChangePlan(
                path=path,
                rationale=relevant.rationale,
                evidence_ids=relevant.evidence_ids,
                relevant_symbols=symbols,
                intended_operations=(EditOperationType.REPLACE,),
                expected_effect=(
                    "Implement the approved requirements affecting this "
                    "repository-grounded target while preserving unrelated behavior."
                ),
                risk=_file_risk(path),
            )
        )

    validation_plan = build_validation_plan(request, decision.selected_paths)
    evidence_ids = tuple(
        sorted(
            {
                evidence_id
                for item in file_changes
                for evidence_id in item.evidence_ids
            }
        )
    )
    payload = {
        "request_id": request.request_id,
        "objective": request.objective,
        "requirements": tuple(
            requirement.requirement_id for requirement in specification.requirements
        ),
        "paths": decision.selected_paths,
        "evidence_ids": evidence_ids,
        "validation_plan_id": validation_plan.validation_plan_id,
    }

    return ChangePlan(
        plan_id=change_plan_identifier(payload),
        request_id=request.request_id,
        objective=request.objective,
        requirements=specification.requirements,
        file_changes=tuple(file_changes),
        validation_plan=validation_plan,
        expected_effect=(
            "Satisfy the normalized engineering requirements using only "
            "repository-grounded approved targets."
        ),
        aggregate_risk=decision.aggregate_risk,
        evidence_ids=evidence_ids,
    )