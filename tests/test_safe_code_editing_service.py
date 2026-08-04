import json
from pathlib import Path

import pytest

from forge.safe_code_editing.errors import ApprovalRequiredError
from forge.safe_code_editing.identifiers import source_fingerprint
from forge.safe_code_editing.models import (
    EditOperation,
    EditOperationType,
    FileEditPlan,
    SafeEditRequest,
)
from forge.safe_code_editing.service import (
    SafeCodeEditingService,
    SafeEditRequestLoadError,
)


def request_for(root: Path, *, dry_run: bool = True, approved: bool = False) -> SafeEditRequest:
    original = "old\n"
    operation = EditOperation(
        operation_id="replace-one",
        operation_type=EditOperationType.REPLACE,
        relative_path="one.txt",
        start_offset=0,
        end_offset=len(original),
        expected_text=original,
        replacement_text="new\n",
        source_fingerprint=source_fingerprint(original),
    )
    plan = FileEditPlan(
        relative_path="one.txt",
        source_fingerprint=source_fingerprint(original),
        operations=(operation,),
    )
    return SafeEditRequest(
        request_id="editreq_one",
        change_plan_id="plan_one",
        repository_root=str(root),
        file_plans=(plan,),
        dry_run=dry_run,
        approved=approved,
    )


def test_service_dry_run_preserves_file(tmp_path: Path) -> None:
    target = tmp_path / "one.txt"
    target.write_bytes(b"old\n")

    report = SafeCodeEditingService().execute(request_for(tmp_path))

    assert report.dry_run is True
    assert report.file_results[0].changed is True
    assert target.read_bytes() == b"old\n"


def test_service_apply_changes_file(tmp_path: Path) -> None:
    target = tmp_path / "one.txt"
    target.write_bytes(b"old\n")

    report = SafeCodeEditingService().execute(
        request_for(tmp_path, dry_run=False, approved=True)
    )

    assert report.approved is True
    assert target.read_bytes() == b"new\n"


def test_execute_file_overrides_to_dry_run(tmp_path: Path) -> None:
    target = tmp_path / "one.txt"
    target.write_bytes(b"old\n")
    request_path = tmp_path / "request.json"
    request_path.write_text(
        request_for(tmp_path, dry_run=False, approved=True).model_dump_json(),
        encoding="utf-8",
    )

    report = SafeCodeEditingService().execute_file(request_path)

    assert report.dry_run is True
    assert target.read_bytes() == b"old\n"


def test_execute_file_requires_approval_for_apply(tmp_path: Path) -> None:
    target = tmp_path / "one.txt"
    target.write_bytes(b"old\n")
    request_path = tmp_path / "request.json"
    request_path.write_text(request_for(tmp_path).model_dump_json(), encoding="utf-8")

    with pytest.raises(ApprovalRequiredError):
        SafeCodeEditingService().execute_file(request_path, apply=True, approved=False)


def test_invalid_request_file_is_rejected(tmp_path: Path) -> None:
    request_path = tmp_path / "request.json"
    request_path.write_text(json.dumps({"invalid": True}), encoding="utf-8")

    with pytest.raises(SafeEditRequestLoadError):
        SafeCodeEditingService().load_request(request_path)


def test_service_writes_json_report(tmp_path: Path) -> None:
    target = tmp_path / "one.txt"
    target.write_bytes(b"old\n")
    report = SafeCodeEditingService().execute(request_for(tmp_path))
    destination = tmp_path / "reports" / "safe-edit.json"

    written = SafeCodeEditingService.write_report(report, destination)

    assert written == destination
    assert json.loads(destination.read_text(encoding="utf-8"))["request_id"] == "editreq_one"