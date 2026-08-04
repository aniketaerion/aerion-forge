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