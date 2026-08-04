[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Content
    )
    $FullPath = Join-Path $RepositoryRoot $Path
    $Directory = Split-Path $FullPath -Parent
    New-Item -ItemType Directory -Path $Directory -Force | Out-Null
    [System.IO.File]::WriteAllText(
        $FullPath,
        $Content,
        [System.Text.UTF8Encoding]::new($false)
    )
    Write-Host "WROTE $Path" -ForegroundColor Green
}

Write-Utf8NoBom "forge\safe_code_editing\operations.py" @'
"""Deterministic in-memory text edit application."""

from __future__ import annotations

from difflib import unified_diff

from forge.safe_code_editing.errors import (
    ExpectedTextMismatchError,
    OverlappingOperationsError,
)
from forge.safe_code_editing.identifiers import source_fingerprint
from forge.safe_code_editing.models import (
    EditOperation,
    EditOperationType,
    FileEditResult,
    LoadedTextFile,
)


def _validate_non_overlapping(operations: tuple[EditOperation, ...]) -> None:
    ordered = sorted(operations, key=lambda item: (item.start_offset, item.end_offset))
    previous_end = -1
    for operation in ordered:
        if operation.start_offset < previous_end:
            raise OverlappingOperationsError(
                f"operation overlaps previous edit: {operation.operation_id}"
            )
        previous_end = max(previous_end, operation.end_offset)


def _validate_range(content: str, operation: EditOperation) -> None:
    if operation.end_offset > len(content):
        raise ExpectedTextMismatchError(
            f"edit range exceeds file length: {operation.operation_id}"
        )

    actual = content[operation.start_offset : operation.end_offset]
    if operation.operation_type in {
        EditOperationType.REPLACE,
        EditOperationType.DELETE,
    } and actual != operation.expected_text:
        raise ExpectedTextMismatchError(
            f"expected text mismatch for operation {operation.operation_id}"
        )


def _normalize_newlines(value: str, newline: str) -> str:
    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    return normalized.replace("\n", newline)


def apply_operations_to_content(
    loaded: LoadedTextFile,
    operations: tuple[EditOperation, ...],
) -> tuple[str, FileEditResult]:
    """Apply validated edits in memory and return content plus evidence."""
    if not operations:
        return loaded.content, FileEditResult(
            relative_path=loaded.relative_path,
            original_fingerprint=loaded.fingerprint,
            resulting_fingerprint=loaded.fingerprint,
            unified_diff="",
            changed=False,
        )

    if any(operation.relative_path != loaded.relative_path for operation in operations):
        raise ValueError("all operations must target the loaded file")

    _validate_non_overlapping(operations)
    for operation in operations:
        _validate_range(loaded.content, operation)

    updated = loaded.content
    for operation in sorted(
        operations,
        key=lambda item: (item.start_offset, item.end_offset),
        reverse=True,
    ):
        replacement = _normalize_newlines(operation.replacement_text, loaded.newline)
        if operation.operation_type is EditOperationType.INSERT:
            updated = (
                updated[: operation.start_offset]
                + replacement
                + updated[operation.start_offset :]
            )
        elif operation.operation_type is EditOperationType.REPLACE:
            updated = (
                updated[: operation.start_offset]
                + replacement
                + updated[operation.end_offset :]
            )
        else:
            updated = updated[: operation.start_offset] + updated[operation.end_offset :]

    diff = "".join(
        unified_diff(
            loaded.content.splitlines(keepends=True),
            updated.splitlines(keepends=True),
            fromfile=f"a/{loaded.relative_path}",
            tofile=f"b/{loaded.relative_path}",
        )
    )
    result = FileEditResult(
        relative_path=loaded.relative_path,
        original_fingerprint=loaded.fingerprint,
        resulting_fingerprint=source_fingerprint(updated),
        unified_diff=diff,
        changed=updated != loaded.content,
    )
    return updated, result


def apply_operations(
    loaded: LoadedTextFile,
    operations: tuple[EditOperation, ...],
) -> FileEditResult:
    """Apply validated edits in memory and return deterministic evidence."""
    _, result = apply_operations_to_content(loaded, operations)
    return result
'@

Write-Utf8NoBom "forge\safe_code_editing\transaction.py" @'
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
'@

Write-Utf8NoBom "tests\test_safe_code_editing_transaction.py" @'
from pathlib import Path

import pytest

from forge.safe_code_editing.errors import (
    ApprovalRequiredError,
    SafeEditWriteError,
)
from forge.safe_code_editing.identifiers import source_fingerprint
from forge.safe_code_editing.models import (
    EditOperation,
    EditOperationType,
    FileEditPlan,
)
from forge.safe_code_editing.policies import SafeEditPolicy
from forge.safe_code_editing.transaction import execute_transaction


def plan(path: str, original: str, replacement: str) -> FileEditPlan:
    operation = EditOperation(
        operation_id=f"replace-{path}",
        operation_type=EditOperationType.REPLACE,
        relative_path=path,
        start_offset=0,
        end_offset=len(original),
        expected_text=original,
        replacement_text=replacement,
        source_fingerprint=source_fingerprint(original),
    )
    return FileEditPlan(
        relative_path=path,
        source_fingerprint=source_fingerprint(original),
        operations=(operation,),
    )


def test_dry_run_does_not_modify_file(tmp_path: Path) -> None:
    target = tmp_path / "one.txt"
    target.write_bytes(b"old\n")

    result = execute_transaction(
        tmp_path,
        (plan("one.txt", "old\n", "new\n"),),
        SafeEditPolicy(),
        dry_run=True,
    )

    assert result.applied is False
    assert result.file_results[0].changed is True
    assert target.read_bytes() == b"old\n"


def test_apply_requires_explicit_approval(tmp_path: Path) -> None:
    target = tmp_path / "one.txt"
    target.write_bytes(b"old\n")

    with pytest.raises(ApprovalRequiredError):
        execute_transaction(
            tmp_path,
            (plan("one.txt", "old\n", "new\n"),),
            SafeEditPolicy(),
            dry_run=False,
            approved=False,
        )


def test_single_file_transaction_applies_atomically(tmp_path: Path) -> None:
    target = tmp_path / "one.txt"
    target.write_bytes(b"old\n")

    result = execute_transaction(
        tmp_path,
        (plan("one.txt", "old\n", "new\n"),),
        SafeEditPolicy(),
        dry_run=False,
        approved=True,
    )

    assert result.applied is True
    assert result.rolled_back is False
    assert target.read_bytes() == b"new\n"


def test_utf8_bom_is_preserved(tmp_path: Path) -> None:
    target = tmp_path / "one.txt"
    target.write_text("old", encoding="utf-8-sig")

    result = execute_transaction(
        tmp_path,
        (plan("one.txt", "old", "new"),),
        SafeEditPolicy(),
        dry_run=False,
        approved=True,
    )

    assert result.applied is True
    assert target.read_bytes().startswith(b"\xef\xbb\xbf")
    assert target.read_text(encoding="utf-8-sig") == "new"


def test_partial_failure_rolls_back_previous_files(tmp_path: Path) -> None:
    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    first.write_bytes(b"one\n")
    second.write_bytes(b"two\n")
    calls = 0

    def failing_replace(source: Path, destination: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated second-file failure")
        source.replace(destination)

    with pytest.raises(SafeEditWriteError):
        execute_transaction(
            tmp_path,
            (
                plan("first.txt", "one\n", "ONE\n"),
                plan("second.txt", "two\n", "TWO\n"),
            ),
            SafeEditPolicy(),
            dry_run=False,
            approved=True,
            replace_file=failing_replace,
        )

    assert first.read_bytes() == b"one\n"
    assert second.read_bytes() == b"two\n"
'@

Write-Host ""
Write-Host "Package 2 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m mypy .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m pytest `
    .\tests\test_safe_code_editing_operations.py `
    .\tests\test_safe_code_editing_transaction.py `
    -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m pytest -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "M3.3 PACKAGE 2 COMPLETE" -ForegroundColor Green
git status --short