"""Atomic multi-file transactions for Safe Code Editing v1."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import TypeAlias

from forge.safe_code_editing.errors import (
    SafeEditRollbackError,
    SafeEditWriteError,
)
from forge.safe_code_editing.identifiers import transaction_identifier
from forge.safe_code_editing.loader import load_text_file
from forge.safe_code_editing.models import (
    EditTransactionResult,
    FileEditPlan,
    FileEditResult,
)
from forge.safe_code_editing.operations import apply_operations_to_content
from forge.safe_code_editing.policies import SafeEditPolicy

ReplaceFunction: TypeAlias = Callable[[Path, Path], None]


def _default_replace(source: Path, destination: Path) -> None:
    os.replace(source, destination)


def _encode_text(content: str, encoding: str) -> bytes:
    return content.encode(encoding)


def _write_temporary(target: Path, data: bytes) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.forge-",
        suffix=".tmp",
        dir=target.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return temporary


def execute_transaction(
    repository_root: Path,
    file_plans: tuple[FileEditPlan, ...],
    policy: SafeEditPolicy,
    *,
    dry_run: bool = True,
    approved: bool = False,
    replace_file: ReplaceFunction = _default_replace,
) -> EditTransactionResult:
    """Validate, stage and atomically apply a bounded multi-file transaction."""
    policy.validate_apply_mode(dry_run=dry_run, approved=approved)
    root = repository_root.resolve()
    transaction_id = transaction_identifier(
        {
            "repository": str(root),
            "files": [
                {
                    "path": plan.relative_path,
                    "fingerprint": plan.source_fingerprint,
                    "operations": [operation.operation_id for operation in plan.operations],
                }
                for plan in file_plans
            ],
        }
    )

    prepared: list[tuple[Path, bytes, bytes, FileEditResult]] = []
    for plan in file_plans:
        loaded = load_text_file(
            root,
            plan.relative_path,
            policy,
            expected_fingerprint=plan.source_fingerprint,
        )
        updated_content, result = apply_operations_to_content(loaded, plan.operations)
        target = policy.resolve_path(root, plan.relative_path)
        prepared.append(
            (
                target,
                target.read_bytes(),
                _encode_text(updated_content, loaded.encoding),
                result,
            )
        )

    results = tuple(item[3] for item in prepared)
    if dry_run:
        return EditTransactionResult(
            transaction_id=transaction_id,
            applied=False,
            rolled_back=False,
            file_results=results,
        )

    staged: dict[Path, Path] = {}
    applied: list[tuple[Path, bytes]] = []
    try:
        for target, _, updated_bytes, _ in prepared:
            staged[target] = _write_temporary(target, updated_bytes)

        for target, original_bytes, _, _ in prepared:
            replace_file(staged[target], target)
            staged.pop(target, None)
            applied.append((target, original_bytes))

        for target, _, _, result in prepared:
            verified = load_text_file(root, target.relative_to(root).as_posix(), policy)
            if verified.fingerprint != result.resulting_fingerprint:
                raise SafeEditWriteError(
                    f"post-write fingerprint mismatch: {target.relative_to(root)}"
                )

        return EditTransactionResult(
            transaction_id=transaction_id,
            applied=True,
            rolled_back=False,
            file_results=results,
        )
    except Exception as exc:
        rollback_errors: list[str] = []
        for target, original_bytes in reversed(applied):
            rollback_temporary: Path | None = None
            try:
                rollback_temporary = _write_temporary(target, original_bytes)
                replace_file(rollback_temporary, target)
            except Exception as rollback_exc:
                rollback_errors.append(f"{target}: {rollback_exc}")
                if rollback_temporary is not None:
                    rollback_temporary.unlink(missing_ok=True)

        if rollback_errors:
            raise SafeEditRollbackError(
                "transaction failed and rollback was incomplete: "
                + "; ".join(rollback_errors)
            ) from exc
        raise SafeEditWriteError(
            f"transaction failed and applied files were rolled back: {exc}"
        ) from exc
    finally:
        for temporary in staged.values():
            temporary.unlink(missing_ok=True)