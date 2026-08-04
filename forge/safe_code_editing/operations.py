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