"""Execution policy for M5.9 Package 5."""

from __future__ import annotations

from dataclasses import dataclass

from forge.general_engineering.models import (
    ChangePlan,
    EngineeringRequest,
    GeneratedChangeSet,
)


@dataclass(frozen=True)
class ExecutionDecision:
    approved: bool
    dry_run: bool
    affected_paths: tuple[str, ...]


def authorize_execution(
    *,
    request: EngineeringRequest,
    plan: ChangePlan,
    change_set: GeneratedChangeSet,
    approved: bool,
    dry_run: bool,
) -> ExecutionDecision:
    if not request.allow_code_changes and not dry_run:
        raise PermissionError(
            "Engineering request does not authorize repository mutation."
        )

    if not dry_run and not approved:
        raise PermissionError(
            "Apply mode requires explicit edit approval."
        )

    planned_paths = {item.path for item in plan.file_changes}
    affected_paths = tuple(
        dict.fromkeys(
            operation.target_path for operation in change_set.operations
        )
    )

    if not set(affected_paths).issubset(planned_paths):
        raise PermissionError(
            "Generated change set exceeds approved plan scope."
        )

    return ExecutionDecision(
        approved=approved,
        dry_run=dry_run,
        affected_paths=affected_paths,
    )