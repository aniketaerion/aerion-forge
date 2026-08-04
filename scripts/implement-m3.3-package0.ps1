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

Write-Utf8NoBom "forge\safe_code_editing\errors.py" @'
"""Typed errors for safe code editing."""


class SafeCodeEditingError(RuntimeError):
    """Base error for safe code editing."""


class InvalidEditPathError(SafeCodeEditingError):
    """Raised when an edit path is invalid."""


class RepositoryPathEscapeError(SafeCodeEditingError):
    """Raised when a path resolves outside the repository root."""


class BinaryFileError(SafeCodeEditingError):
    """Raised when a binary file is supplied for text editing."""


class OversizedFileError(SafeCodeEditingError):
    """Raised when a file exceeds the configured size limit."""


class UnsupportedEncodingError(SafeCodeEditingError):
    """Raised when text encoding is unsupported."""


class FingerprintMismatchError(SafeCodeEditingError):
    """Raised when file contents changed after planning."""


class ExpectedTextMismatchError(SafeCodeEditingError):
    """Raised when expected source text does not match."""


class OverlappingOperationsError(SafeCodeEditingError):
    """Raised when edit operations overlap."""


class ApprovalRequiredError(SafeCodeEditingError):
    """Raised when apply mode lacks explicit approval."""


class SafeEditWriteError(SafeCodeEditingError):
    """Raised when an atomic file write fails."""


class SafeEditRollbackError(SafeCodeEditingError):
    """Raised when rollback cannot restore repository state."""
'@

Write-Utf8NoBom "forge\safe_code_editing\identifiers.py" @'
"""Deterministic identifiers and fingerprints for safe code editing."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any


def sha256_text(value: str) -> str:
    """Return the SHA-256 digest for UTF-8 text."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def source_fingerprint(content: str) -> str:
    """Return a deterministic source-content fingerprint."""
    return sha256_text(content)


def stable_identifier(prefix: str, payload: Mapping[str, Any] | Sequence[Any] | str) -> str:
    """Build a stable identifier from canonical JSON."""
    if isinstance(payload, str):
        canonical = payload
    else:
        canonical = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            default=str,
        )
    return f"{prefix}_{sha256_text(canonical)[:24]}"


def operation_identifier(payload: Mapping[str, Any]) -> str:
    """Return a stable operation identifier."""
    return stable_identifier("editop", payload)


def request_identifier(payload: Mapping[str, Any]) -> str:
    """Return a stable request identifier."""
    return stable_identifier("editreq", payload)


def transaction_identifier(payload: Mapping[str, Any]) -> str:
    """Return a stable transaction identifier."""
    return stable_identifier("edittxn", payload)
'@

Write-Utf8NoBom "forge\safe_code_editing\models.py" @'
"""Immutable contracts for Safe Code Editing v1."""

from __future__ import annotations

from enum import StrEnum
from pathlib import PurePosixPath
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EditOperationType(StrEnum):
    """Supported bounded edit operations."""

    INSERT = "insert"
    REPLACE = "replace"
    DELETE = "delete"


def _validate_relative_path(value: str) -> str:
    normalized = value.replace("\\", "/").strip()
    path = PurePosixPath(normalized)
    if not normalized or path.is_absolute():
        raise ValueError("path must be relative")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("path may not contain empty, current, or parent traversal segments")
    return path.as_posix()


class FrozenModel(BaseModel):
    """Base class for immutable Forge contracts."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class EditOperation(FrozenModel):
    """One deterministic text edit."""

    operation_id: str
    operation_type: EditOperationType
    relative_path: str
    start_offset: Annotated[int, Field(ge=0)]
    end_offset: Annotated[int, Field(ge=0)]
    expected_text: str = ""
    replacement_text: str = ""
    source_fingerprint: str

    @model_validator(mode="after")
    def validate_operation(self) -> "EditOperation":
        object.__setattr__(self, "relative_path", _validate_relative_path(self.relative_path))
        if self.end_offset < self.start_offset:
            raise ValueError("end_offset may not precede start_offset")
        if self.operation_type is EditOperationType.INSERT:
            if self.start_offset != self.end_offset:
                raise ValueError("INSERT requires equal start_offset and end_offset")
            if self.expected_text:
                raise ValueError("INSERT must not require expected_text")
        elif self.operation_type is EditOperationType.DELETE:
            if self.replacement_text:
                raise ValueError("DELETE requires empty replacement_text")
            if not self.expected_text:
                raise ValueError("DELETE requires expected_text")
        elif self.operation_type is EditOperationType.REPLACE:
            if not self.expected_text:
                raise ValueError("REPLACE requires expected_text")
        return self


class FileEditPlan(FrozenModel):
    """Ordered edits for one file."""

    relative_path: str
    source_fingerprint: str
    operations: tuple[EditOperation, ...]

    @model_validator(mode="after")
    def validate_plan(self) -> "FileEditPlan":
        object.__setattr__(self, "relative_path", _validate_relative_path(self.relative_path))
        if not self.operations:
            raise ValueError("file edit plan requires at least one operation")
        if any(operation.relative_path != self.relative_path for operation in self.operations):
            raise ValueError("all operations must target the file edit plan path")
        operation_ids = [operation.operation_id for operation in self.operations]
        if len(operation_ids) != len(set(operation_ids)):
            raise ValueError("duplicate operation IDs are not allowed")
        return self


class SafeEditRequest(FrozenModel):
    """Approved or dry-run request derived from an M3.2 change plan."""

    request_id: str
    change_plan_id: str
    repository_root: str
    file_plans: tuple[FileEditPlan, ...]
    dry_run: bool = True
    approved: bool = False

    @model_validator(mode="after")
    def validate_request(self) -> "SafeEditRequest":
        if not self.file_plans:
            raise ValueError("request requires at least one file plan")
        if not self.dry_run and not self.approved:
            raise ValueError("apply mode requires explicit approval")
        paths = [plan.relative_path for plan in self.file_plans]
        if len(paths) != len(set(paths)):
            raise ValueError("duplicate file plans are not allowed")
        return self


class LoadedTextFile(FrozenModel):
    """Safely loaded text-file state."""

    relative_path: str
    content: str
    encoding: str
    newline: str
    size_bytes: int = Field(ge=0)
    fingerprint: str


class FileSnapshot(FrozenModel):
    """Original state used for transaction rollback."""

    relative_path: str
    content: str
    encoding: str
    newline: str
    fingerprint: str


class FileEditResult(FrozenModel):
    """Result for one edited file."""

    relative_path: str
    original_fingerprint: str
    resulting_fingerprint: str
    unified_diff: str
    changed: bool


class EditTransactionResult(FrozenModel):
    """Atomic transaction outcome."""

    transaction_id: str
    applied: bool
    rolled_back: bool
    file_results: tuple[FileEditResult, ...]
    errors: tuple[str, ...] = ()


class SafeEditReport(FrozenModel):
    """Complete auditable output for one request."""

    request_id: str
    transaction_id: str
    dry_run: bool
    approved: bool
    file_results: tuple[FileEditResult, ...]
    validation_messages: tuple[str, ...] = ()
'@

Write-Utf8NoBom "forge\safe_code_editing\policies.py" @'
"""Safety policy for bounded code editing."""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from pydantic import Field

from forge.safe_code_editing.errors import (
    ApprovalRequiredError,
    InvalidEditPathError,
    RepositoryPathEscapeError,
)

from .models import FrozenModel


class SafeEditPolicy(FrozenModel):
    """Immutable editing policy."""

    max_file_bytes: int = Field(default=1_000_000, gt=0)
    allowed_encodings: tuple[str, ...] = ("utf-8", "utf-8-sig")
    protected_paths: tuple[str, ...] = (
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "reports",
        "audit",
        "memory",
    )
    dry_run_default: bool = True
    require_explicit_approval: bool = True
    reject_symlink_escape: bool = True

    def validate_apply_mode(self, *, dry_run: bool, approved: bool) -> None:
        """Reject unapproved apply requests."""
        if not dry_run and self.require_explicit_approval and not approved:
            raise ApprovalRequiredError("apply mode requires explicit approval")

    def validate_relative_path(self, relative_path: str) -> str:
        """Normalize and validate a repository-relative path."""
        normalized = relative_path.replace("\\", "/").strip()
        path = PurePosixPath(normalized)
        if not normalized or path.is_absolute() or ".." in path.parts:
            raise InvalidEditPathError(f"invalid relative path: {relative_path}")
        if path.parts and path.parts[0] in self.protected_paths:
            raise InvalidEditPathError(f"protected path: {relative_path}")
        return path.as_posix()

    def resolve_path(self, repository_root: Path, relative_path: str) -> Path:
        """Resolve a path and guarantee repository containment."""
        normalized = self.validate_relative_path(relative_path)
        root = repository_root.resolve()
        candidate = (root / normalized).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise RepositoryPathEscapeError(
                f"path resolves outside repository: {relative_path}"
            ) from exc
        if self.reject_symlink_escape and candidate.exists() and candidate.is_symlink():
            resolved = candidate.resolve()
            try:
                resolved.relative_to(root)
            except ValueError as exc:
                raise RepositoryPathEscapeError(
                    f"symlink resolves outside repository: {relative_path}"
                ) from exc
        return candidate
'@

Write-Utf8NoBom "forge\safe_code_editing\__init__.py" @'
"""Safe Code Editing v1 contracts."""

from forge.safe_code_editing.identifiers import (
    operation_identifier,
    request_identifier,
    source_fingerprint,
    stable_identifier,
    transaction_identifier,
)
from forge.safe_code_editing.models import (
    EditOperation,
    EditOperationType,
    EditTransactionResult,
    FileEditPlan,
    FileEditResult,
    FileSnapshot,
    LoadedTextFile,
    SafeEditReport,
    SafeEditRequest,
)
from forge.safe_code_editing.policies import SafeEditPolicy

__all__ = [
    "EditOperation",
    "EditOperationType",
    "EditTransactionResult",
    "FileEditPlan",
    "FileEditResult",
    "FileSnapshot",
    "LoadedTextFile",
    "SafeEditPolicy",
    "SafeEditReport",
    "SafeEditRequest",
    "operation_identifier",
    "request_identifier",
    "source_fingerprint",
    "stable_identifier",
    "transaction_identifier",
]
'@

Write-Utf8NoBom "tests\test_safe_code_editing_identifiers.py" @'
from forge.safe_code_editing.identifiers import (
    operation_identifier,
    source_fingerprint,
    stable_identifier,
)


def test_source_fingerprint_is_deterministic() -> None:
    assert source_fingerprint("alpha") == source_fingerprint("alpha")
    assert source_fingerprint("alpha") != source_fingerprint("beta")


def test_stable_identifier_is_order_independent_for_mappings() -> None:
    left = stable_identifier("item", {"a": 1, "b": 2})
    right = stable_identifier("item", {"b": 2, "a": 1})
    assert left == right


def test_operation_identifier_has_expected_prefix() -> None:
    assert operation_identifier({"path": "forge/app.py"}).startswith("editop_")
'@

Write-Utf8NoBom "tests\test_safe_code_editing_models.py" @'
import pytest
from pydantic import ValidationError

from forge.safe_code_editing.models import (
    EditOperation,
    EditOperationType,
    FileEditPlan,
    SafeEditRequest,
)


def operation(**overrides: object) -> EditOperation:
    values: dict[str, object] = {
        "operation_id": "editop_1",
        "operation_type": EditOperationType.REPLACE,
        "relative_path": "forge/app.py",
        "start_offset": 0,
        "end_offset": 3,
        "expected_text": "old",
        "replacement_text": "new",
        "source_fingerprint": "a" * 64,
    }
    values.update(overrides)
    return EditOperation.model_validate(values)


def test_models_are_immutable() -> None:
    item = operation()
    with pytest.raises(ValidationError):
        item.start_offset = 2  # type: ignore[misc]


def test_insert_requires_equal_offsets() -> None:
    with pytest.raises(ValidationError):
        operation(
            operation_type=EditOperationType.INSERT,
            start_offset=1,
            end_offset=2,
            expected_text="",
        )


def test_delete_requires_empty_replacement() -> None:
    with pytest.raises(ValidationError):
        operation(
            operation_type=EditOperationType.DELETE,
            replacement_text="not-empty",
        )


def test_relative_path_rejects_traversal() -> None:
    with pytest.raises(ValidationError):
        operation(relative_path="../secret.py")


def test_request_requires_approval_for_apply() -> None:
    item = operation()
    plan = FileEditPlan(
        relative_path="forge/app.py",
        source_fingerprint="a" * 64,
        operations=(item,),
    )
    with pytest.raises(ValidationError):
        SafeEditRequest(
            request_id="editreq_1",
            change_plan_id="plan_1",
            repository_root=".",
            file_plans=(plan,),
            dry_run=False,
            approved=False,
        )
'@

Write-Utf8NoBom "tests\test_safe_code_editing_policies.py" @'
from pathlib import Path

import pytest

from forge.safe_code_editing.errors import (
    ApprovalRequiredError,
    InvalidEditPathError,
)
from forge.safe_code_editing.policies import SafeEditPolicy


def test_policy_defaults_are_safe() -> None:
    policy = SafeEditPolicy()
    assert policy.dry_run_default is True
    assert policy.require_explicit_approval is True
    assert "utf-8" in policy.allowed_encodings


def test_policy_rejects_unapproved_apply() -> None:
    policy = SafeEditPolicy()
    with pytest.raises(ApprovalRequiredError):
        policy.validate_apply_mode(dry_run=False, approved=False)


def test_policy_rejects_protected_path() -> None:
    policy = SafeEditPolicy()
    with pytest.raises(InvalidEditPathError):
        policy.validate_relative_path(".git/config")


def test_policy_resolves_repository_path(tmp_path: Path) -> None:
    policy = SafeEditPolicy()
    resolved = policy.resolve_path(tmp_path, "forge/app.py")
    assert resolved == (tmp_path / "forge/app.py").resolve()
'@

Write-Utf8NoBom "docs\safe_code_editing\ARCHITECTURE.md" @'
# M3.3 Safe Code Editing Architecture

## Objective

Convert an approved M3.2 change plan into deterministic, reviewable and reversible text edits.

## Components

1. **Identifiers** generate stable SHA-256-based IDs and fingerprints.
2. **Models** define immutable requests, plans, operations, snapshots and results.
3. **Policies** enforce repository containment, protected paths, size limits and approval.
4. **Loader** will safely load text while preserving encoding and newline conventions.
5. **Operations** will apply bounded insert, replace and delete edits in memory.
6. **Transaction** will snapshot files, write atomically and roll back on failure.
7. **Service** will orchestrate dry-run and apply execution.
8. **CLI** will expose explicit dry-run and approved apply commands.

## Flow

Approved change plan → policy validation → safe load → fingerprint check → in-memory edits → diff → dry-run or atomic transaction → report.

## Boundaries

M3.3 v1 does not perform semantic refactoring, repository-wide renames, Git commits, shell execution or autonomous merges.
'@

Write-Utf8NoBom "docs\safe_code_editing\SPECIFICATION.md" @'
# M3.3 Safe Code Editing Specification

## Supported operations

- `insert`: add text at one verified offset.
- `replace`: replace verified expected text within one range.
- `delete`: remove verified expected text within one range.

## Required guarantees

- Every path remains inside the repository.
- Protected and generated paths are rejected.
- Dry-run is the default.
- Apply mode requires explicit approval.
- Source fingerprints detect stale plans.
- Overlapping edits are rejected.
- Unified diffs are generated before writes.
- Multi-file writes are atomic from the user perspective.
- Failures trigger rollback.

## Explicit exclusions

AST refactoring, symbol graph rewrites, dependency installation, autonomous commits and unrestricted commands are outside M3.3 v1.
'@

Write-Utf8NoBom "docs\safe_code_editing\DATA_MODEL.md" @'
# M3.3 Data Model

## EditOperation

Describes one bounded text mutation with operation type, repository-relative path, offsets, expected text, replacement text and source fingerprint.

## FileEditPlan

Groups ordered operations for one source file and binds them to one source fingerprint.

## SafeEditRequest

Groups file plans, references an approved M3.2 change plan and distinguishes dry-run from approved apply mode.

## LoadedTextFile and FileSnapshot

Capture encoding, newline convention, content and fingerprints required for safe processing and rollback.

## Results

`FileEditResult`, `EditTransactionResult` and `SafeEditReport` provide immutable evidence including unified diffs, resulting fingerprints, rollback state and validation messages.
'@

Write-Utf8NoBom "docs\safe_code_editing\SECURITY_AND_TRANSACTION_MODEL.md" @'
# M3.3 Security and Transaction Model

## Security controls

- Repository-relative paths only.
- Parent traversal and absolute paths are rejected.
- Protected directories are rejected.
- Resolved paths must remain within the repository.
- Symlink escapes are rejected.
- Binary and oversized files will be rejected by the loader.
- Apply requests require explicit approval.

## Transaction rules

1. Load and fingerprint all target files.
2. Validate every operation before any write.
3. Produce all edited contents and diffs in memory.
4. Snapshot every target.
5. Write through temporary files.
6. Replace targets atomically where supported.
7. On any failure, restore every file already changed.
8. Report both the original failure and any rollback failure.
'@

Write-Utf8NoBom "docs\safe_code_editing\ACCEPTANCE_CRITERIA.md" @'
# M3.3 Acceptance Criteria

M3.3 is complete when:

- immutable contracts cover requests, operations, plans, snapshots and results;
- deterministic IDs and source fingerprints are implemented;
- only insert, replace and delete operations are supported;
- invalid paths and traversal are rejected;
- protected paths and symlink escapes are rejected;
- binary and oversized files are rejected;
- stale fingerprints and expected-text mismatches are rejected;
- overlapping edits are rejected;
- dry-run never writes;
- apply mode requires explicit approval;
- multi-file writes roll back on failure;
- unified diffs and structured reports are generated;
- Ruff, MyPy, the full pytest suite and M3.3 validation scripts pass.
'@

Write-Host ""
Write-Host "Package 0 files written. Running validation..." -ForegroundColor Cyan
python -m ruff check .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m mypy .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m pytest -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "M3.3 PACKAGE 0 COMPLETE" -ForegroundColor Green
git status --short
