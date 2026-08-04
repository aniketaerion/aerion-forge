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