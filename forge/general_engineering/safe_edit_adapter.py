"""Translate M5.9 edit proposals into existing Safe Code Editing requests."""

from __future__ import annotations

from pathlib import Path

from forge.general_engineering.errors import EngineeringContractError
from forge.general_engineering.models import (
    ChangePlan,
    EditOperation,
    EngineeringRequest,
    GeneratedChangeSet,
)
from forge.general_engineering.states import EditOperationType
from forge.safe_code_editing.models import (
    EditOperation as SafeEditOperation,
)
from forge.safe_code_editing.models import (
    EditOperationType as SafeEditOperationType,
)
from forge.safe_code_editing.models import FileEditPlan, SafeEditRequest


def _safe_operation_type(
    operation_type: EditOperationType,
) -> SafeEditOperationType:
    mapping = {
        EditOperationType.INSERT: SafeEditOperationType.INSERT,
        EditOperationType.REPLACE: SafeEditOperationType.REPLACE,
        EditOperationType.DELETE: SafeEditOperationType.DELETE,
    }
    try:
        return mapping[operation_type]
    except KeyError as exc:
        raise EngineeringContractError(
            f"Operation type is not executable by Safe Code Editing: "
            f"{operation_type.value}"
        ) from exc


def _build_safe_operation(
    *,
    repository_root: Path,
    operation: EditOperation,
) -> SafeEditOperation:
    path = repository_root / operation.target_path
    if not path.is_file():
        raise EngineeringContractError(
            f"Executable edit target does not exist: {operation.target_path}"
        )

    content = path.read_bytes().decode("utf-8")
    expected_text = content

    if operation.operation_type is EditOperationType.INSERT:
        start_offset = len(content)
        end_offset = len(content)
        expected_text = ""
    else:
        start_offset = 0
        end_offset = len(content)

    replacement_text = operation.proposed_content or ""
    if operation.operation_type is EditOperationType.DELETE:
        replacement_text = ""

    return SafeEditOperation(
        operation_id=operation.operation_id,
        operation_type=_safe_operation_type(operation.operation_type),
        relative_path=operation.target_path,
        start_offset=start_offset,
        end_offset=end_offset,
        expected_text=expected_text,
        replacement_text=replacement_text,
        source_fingerprint=operation.source_fingerprint or "",
    )


def build_safe_edit_request(
    *,
    request: EngineeringRequest,
    plan: ChangePlan,
    change_set: GeneratedChangeSet,
    approved: bool,
    dry_run: bool,
) -> SafeEditRequest:
    """Build one bounded SafeEditRequest from a validated change set."""
    if change_set.plan_id != plan.plan_id:
        raise EngineeringContractError(
            "Generated change set does not belong to the supplied change plan."
        )

    repository_root = Path(request.repository_root).resolve()
    grouped: dict[str, list[SafeEditOperation]] = {}

    for operation in change_set.operations:
        grouped.setdefault(operation.target_path, []).append(
            _build_safe_operation(
                repository_root=repository_root,
                operation=operation,
            )
        )

    file_plans: list[FileEditPlan] = []
    for path, operations in sorted(grouped.items()):
        fingerprints = {
            operation.source_fingerprint for operation in operations
        }
        if len(fingerprints) != 1:
            raise EngineeringContractError(
                f"Conflicting source fingerprints for {path}."
            )
        source_fingerprint = next(iter(fingerprints))
        file_plans.append(
            FileEditPlan(
                relative_path=path,
                source_fingerprint=source_fingerprint,
                operations=tuple(operations),
            )
        )

    return SafeEditRequest(
        request_id=f"general-engineering-{change_set.change_set_id}",
        change_plan_id=plan.plan_id,
        repository_root=str(repository_root),
        file_plans=tuple(file_plans),
        dry_run=dry_run,
        approved=approved,
    )