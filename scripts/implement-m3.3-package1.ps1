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

Write-Utf8NoBom "forge\safe_code_editing\loader.py" @'
"""Safe text-file loading for M3.3."""

from __future__ import annotations

from pathlib import Path

from forge.safe_code_editing.errors import (
    BinaryFileError,
    FingerprintMismatchError,
    OversizedFileError,
    UnsupportedEncodingError,
)
from forge.safe_code_editing.identifiers import source_fingerprint
from forge.safe_code_editing.models import LoadedTextFile
from forge.safe_code_editing.policies import SafeEditPolicy


def _detect_newline(text: str) -> str:
    if "\r\n" in text:
        return "\r\n"
    if "\r" in text:
        return "\r"
    return "\n"


def _decode_text(data: bytes, allowed_encodings: tuple[str, ...]) -> tuple[str, str]:
    if b"\x00" in data:
        raise BinaryFileError("binary file detected")

    for encoding in allowed_encodings:
        try:
            return data.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise UnsupportedEncodingError(
        f"unable to decode file with allowed encodings: {allowed_encodings}"
    )


def load_text_file(
    repository_root: Path,
    relative_path: str,
    policy: SafeEditPolicy,
    *,
    expected_fingerprint: str | None = None,
) -> LoadedTextFile:
    """Load a bounded repository text file and verify its fingerprint."""
    path = policy.resolve_path(repository_root, relative_path)
    stat = path.stat()
    if stat.st_size > policy.max_file_bytes:
        raise OversizedFileError(
            f"file exceeds {policy.max_file_bytes} bytes: {relative_path}"
        )

    data = path.read_bytes()
    text, encoding = _decode_text(data, policy.allowed_encodings)
    fingerprint = source_fingerprint(text)
    if expected_fingerprint is not None and fingerprint != expected_fingerprint:
        raise FingerprintMismatchError(
            f"source fingerprint mismatch for {relative_path}"
        )

    return LoadedTextFile(
        relative_path=policy.validate_relative_path(relative_path),
        content=text,
        encoding=encoding,
        newline=_detect_newline(text),
        size_bytes=len(data),
        fingerprint=fingerprint,
    )
'@

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


def apply_operations(
    loaded: LoadedTextFile,
    operations: tuple[EditOperation, ...],
) -> FileEditResult:
    """Apply validated edits in memory and return a deterministic diff."""
    if not operations:
        return FileEditResult(
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
        if operation.operation_type is EditOperationType.INSERT:
            updated = (
                updated[: operation.start_offset]
                + operation.replacement_text
                + updated[operation.start_offset :]
            )
        elif operation.operation_type is EditOperationType.REPLACE:
            updated = (
                updated[: operation.start_offset]
                + operation.replacement_text
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
    resulting_fingerprint = source_fingerprint(updated)
    return FileEditResult(
        relative_path=loaded.relative_path,
        original_fingerprint=loaded.fingerprint,
        resulting_fingerprint=resulting_fingerprint,
        unified_diff=diff,
        changed=updated != loaded.content,
    )
'@

Write-Utf8NoBom "tests\test_safe_code_editing_loader.py" @'
from pathlib import Path

import pytest

from forge.safe_code_editing.errors import (
    BinaryFileError,
    FingerprintMismatchError,
    OversizedFileError,
)
from forge.safe_code_editing.identifiers import source_fingerprint
from forge.safe_code_editing.loader import load_text_file
from forge.safe_code_editing.policies import SafeEditPolicy


def test_loader_reads_utf8_and_detects_lf(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_text("a\nb\n", encoding="utf-8")

    loaded = load_text_file(tmp_path, "sample.py", SafeEditPolicy())

    assert loaded.content == "a\nb\n"
    assert loaded.newline == "\n"
    assert loaded.fingerprint == source_fingerprint("a\nb\n")


def test_loader_reads_utf8_bom(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_text("hello", encoding="utf-8-sig")

    loaded = load_text_file(tmp_path, "sample.py", SafeEditPolicy())

    assert loaded.content == "hello"


def test_loader_rejects_binary(tmp_path: Path) -> None:
    target = tmp_path / "binary.bin"
    target.write_bytes(b"abc\x00def")

    with pytest.raises(BinaryFileError):
        load_text_file(tmp_path, "binary.bin", SafeEditPolicy())


def test_loader_rejects_oversized_file(tmp_path: Path) -> None:
    target = tmp_path / "large.txt"
    target.write_text("abcdef", encoding="utf-8")

    with pytest.raises(OversizedFileError):
        load_text_file(
            tmp_path,
            "large.txt",
            SafeEditPolicy(max_file_bytes=3),
        )


def test_loader_rejects_fingerprint_mismatch(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_text("current", encoding="utf-8")

    with pytest.raises(FingerprintMismatchError):
        load_text_file(
            tmp_path,
            "sample.py",
            SafeEditPolicy(),
            expected_fingerprint=source_fingerprint("planned"),
        )
'@

Write-Utf8NoBom "tests\test_safe_code_editing_operations.py" @'
import pytest

from forge.safe_code_editing.errors import (
    ExpectedTextMismatchError,
    OverlappingOperationsError,
)
from forge.safe_code_editing.identifiers import source_fingerprint
from forge.safe_code_editing.models import (
    EditOperation,
    EditOperationType,
    LoadedTextFile,
)
from forge.safe_code_editing.operations import apply_operations


def loaded(content: str = "abc\ndef\n") -> LoadedTextFile:
    return LoadedTextFile(
        relative_path="sample.py",
        content=content,
        encoding="utf-8",
        newline="\n",
        size_bytes=len(content.encode("utf-8")),
        fingerprint=source_fingerprint(content),
    )


def operation(
    operation_id: str,
    operation_type: EditOperationType,
    start: int,
    end: int,
    expected: str = "",
    replacement: str = "",
) -> EditOperation:
    return EditOperation(
        operation_id=operation_id,
        operation_type=operation_type,
        relative_path="sample.py",
        start_offset=start,
        end_offset=end,
        expected_text=expected,
        replacement_text=replacement,
        source_fingerprint=source_fingerprint("abc\ndef\n"),
    )


def test_insert_operation() -> None:
    result = apply_operations(
        loaded(),
        (operation("insert-1", EditOperationType.INSERT, 3, 3, replacement="X"),),
    )

    assert result.changed is True
    assert "+abcX" in result.unified_diff


def test_replace_operation() -> None:
    result = apply_operations(
        loaded(),
        (
            operation(
                "replace-1",
                EditOperationType.REPLACE,
                0,
                3,
                expected="abc",
                replacement="xyz",
            ),
        ),
    )

    assert result.changed is True
    assert "-abc" in result.unified_diff
    assert "+xyz" in result.unified_diff


def test_delete_operation() -> None:
    result = apply_operations(
        loaded(),
        (
            operation(
                "delete-1",
                EditOperationType.DELETE,
                0,
                4,
                expected="abc\n",
            ),
        ),
    )

    assert result.changed is True
    assert "-abc" in result.unified_diff


def test_expected_text_mismatch_is_rejected() -> None:
    with pytest.raises(ExpectedTextMismatchError):
        apply_operations(
            loaded(),
            (
                operation(
                    "replace-1",
                    EditOperationType.REPLACE,
                    0,
                    3,
                    expected="wrong",
                    replacement="xyz",
                ),
            ),
        )


def test_overlapping_operations_are_rejected() -> None:
    with pytest.raises(OverlappingOperationsError):
        apply_operations(
            loaded(),
            (
                operation(
                    "replace-1",
                    EditOperationType.REPLACE,
                    0,
                    3,
                    expected="abc",
                    replacement="xyz",
                ),
                operation(
                    "replace-2",
                    EditOperationType.REPLACE,
                    2,
                    5,
                    expected="c\nd",
                    replacement="123",
                ),
            ),
        )
'@

Write-Host ""
Write-Host "Package 1 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m mypy .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m pytest -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "M3.3 PACKAGE 1 COMPLETE" -ForegroundColor Green
git status --short