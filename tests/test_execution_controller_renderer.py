"""Execution Controller renderer tests."""

import json
from pathlib import Path

import pytest

from forge.execution_controller.builder import (
    ExecutionControllerBuilder,
)
from forge.execution_controller.errors import (
    ExecutionReportError,
)
from forge.execution_controller.models import (
    ApprovalDecision,
    EvidenceType,
    ExecutionEvent,
    ExecutionSession,
    ExecutionState,
    OperationStatus,
)
from forge.execution_controller.renderer import (
    ExecutionControllerRenderer,
)


def _session() -> ExecutionSession:
    builder = ExecutionControllerBuilder()

    request = builder.build_request(
        mission_id="mission-123",
        task_ids=("task-a",),
        requested_operations=("edit",),
        dry_run=True,
        source_fingerprints={
            "mission": "a" * 64,
            "tasks": "b" * 64,
        },
    )

    approval = builder.build_approval(
        request,
        approver_id="engineering-lead",
        decision=ApprovalDecision.APPROVED,
        approved_operations=("edit",),
        evidence_reference="approval.json",
    )

    operation = builder.build_operation(
        request,
        task_id="task-a",
        tool_id="filesystem",
        operation_type="edit",
        arguments_fingerprint="c" * 64,
        status=OperationStatus.SUCCEEDED,
        result_reference="results/edit.json",
    )

    session = builder.build_session(
        request,
        approval=approval,
        current_state=ExecutionState.APPROVED,
        operations=(operation,),
    )

    session = builder.transition_session(
        session,
        ExecutionEvent.ENQUEUE,
    )

    session = builder.transition_session(
        session,
        ExecutionEvent.START,
    )

    evidence = builder.build_evidence(
        session_id_value=session.session_id,
        evidence_type=EvidenceType.TOOL_RESULT,
        source="filesystem",
        fingerprint="d" * 64,
        reference="results/edit.json",
        metadata={
            "operation": "edit",
            "result": "success",
        },
    )

    session = builder.append_evidence(
        session,
        evidence,
    )

    return builder.transition_session(
        session,
        ExecutionEvent.COMPLETE,
        evidence_ids=(evidence.evidence_id,),
    )


def test_render_json_is_valid() -> None:
    rendered = ExecutionControllerRenderer().render_json(_session())

    payload = json.loads(rendered)

    assert payload["request"]["mission_id"] == "mission-123"
    assert payload["current_state"] == "completed"


def test_render_json_contains_session_identity() -> None:
    session = _session()
    payload = json.loads(ExecutionControllerRenderer().render_json(session))

    assert payload["session_id"] == session.session_id
    assert payload["session_fingerprint"] == session.session_fingerprint


def test_render_json_is_deterministic() -> None:
    renderer = ExecutionControllerRenderer()
    session = _session()

    assert renderer.render_json(session) == renderer.render_json(session)


def test_render_json_uses_canonical_compact_format() -> None:
    rendered = ExecutionControllerRenderer().render_json(_session())

    assert ": " not in rendered
    assert rendered.endswith("\n")


def test_render_summary_contains_core_fields() -> None:
    session = _session()
    payload = json.loads(ExecutionControllerRenderer().render_summary_json(session))

    assert payload["session_id"] == session.session_id
    assert payload["mission_id"] == "mission-123"
    assert payload["current_state"] == "completed"
    assert payload["dry_run"] is True


def test_render_summary_contains_statistics() -> None:
    payload = json.loads(ExecutionControllerRenderer().render_summary_json(_session()))

    assert payload["statistics"]["operation_count"] == 1
    assert payload["statistics"]["succeeded_count"] == 1


def test_render_evidence_contains_evidence() -> None:
    session = _session()
    payload = json.loads(ExecutionControllerRenderer().render_evidence_json(session))

    assert payload["session_id"] == session.session_id
    assert len(payload["evidence"]) == 1
    assert payload["evidence"][0]["evidence_type"] == "tool_result"


def test_render_transitions_contains_history() -> None:
    session = _session()
    payload = json.loads(ExecutionControllerRenderer().render_transitions_json(session))

    assert payload["current_state"] == "completed"
    assert len(payload["transitions"]) == 3


def test_render_markdown_contains_heading() -> None:
    rendered = ExecutionControllerRenderer().render_markdown(_session())

    assert rendered.startswith("# Execution Controller Report\n")


def test_render_markdown_contains_session_details() -> None:
    session = _session()
    rendered = ExecutionControllerRenderer().render_markdown(session)

    assert session.session_id in rendered
    assert session.request.request_id in rendered
    assert "mission-123" in rendered
    assert "`completed`" in rendered


def test_render_markdown_contains_operation() -> None:
    session = _session()
    rendered = ExecutionControllerRenderer().render_markdown(session)

    assert session.operations[0].operation_id in rendered
    assert "status `succeeded`" in rendered


def test_render_markdown_contains_transitions() -> None:
    rendered = ExecutionControllerRenderer().render_markdown(_session())

    assert "## State transitions" in rendered
    assert "`approved` → `queued`" in rendered
    assert "`running` → `completed`" in rendered


def test_render_markdown_contains_evidence() -> None:
    session = _session()
    rendered = ExecutionControllerRenderer().render_markdown(session)

    assert "## Evidence" in rendered
    assert session.evidence[0].evidence_id in rendered


def test_render_markdown_contains_source_fingerprints() -> None:
    rendered = ExecutionControllerRenderer().render_markdown(_session())

    assert "## Source fingerprints" in rendered
    assert "`mission`:" in rendered
    assert "`tasks`:" in rendered


def test_render_suite_contains_exact_files() -> None:
    renderer = ExecutionControllerRenderer()
    suite = renderer.render_suite(_session())

    assert set(suite) == {
        "EXECUTION_CONTROLLER.json",
        "EXECUTION_CONTROLLER_SUMMARY.json",
        "EXECUTION_CONTROLLER_EVIDENCE.json",
        "EXECUTION_CONTROLLER_TRANSITIONS.json",
        "EXECUTION_CONTROLLER.md",
    }


def test_render_suite_is_deterministic() -> None:
    renderer = ExecutionControllerRenderer()
    session = _session()

    assert renderer.render_suite(session) == renderer.render_suite(session)


def test_write_suite_creates_all_files(
    tmp_path: Path,
) -> None:
    renderer = ExecutionControllerRenderer()

    paths = renderer.write_suite(
        _session(),
        tmp_path,
    )

    assert len(paths) == 5

    for name in renderer.render_suite(_session()):
        assert (tmp_path / name).is_file()


def test_written_files_match_rendered_suite(
    tmp_path: Path,
) -> None:
    renderer = ExecutionControllerRenderer()
    session = _session()
    expected = renderer.render_suite(session)

    renderer.write_suite(
        session,
        tmp_path,
    )

    for name, content in expected.items():
        assert (tmp_path / name).read_text(encoding="utf-8") == content


def test_write_suite_overwrites_existing_files(
    tmp_path: Path,
) -> None:
    renderer = ExecutionControllerRenderer()
    session = _session()

    for name in renderer.render_suite(session):
        (tmp_path / name).write_text(
            "stale",
            encoding="utf-8",
        )

    renderer.write_suite(
        session,
        tmp_path,
    )

    assert (tmp_path / renderer.REPORT_NAME).read_text(encoding="utf-8") != "stale"


def test_write_suite_removes_temporary_files(
    tmp_path: Path,
) -> None:
    renderer = ExecutionControllerRenderer()
    session = _session()

    renderer.write_suite(
        session,
        tmp_path,
    )

    assert not tuple(tmp_path.glob("*.tmp"))


def test_write_suite_wraps_os_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    renderer = ExecutionControllerRenderer()

    original = Path.write_text

    def fail_write(
        self: Path,
        data: str,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> int:
        if self.name.endswith(".tmp"):
            raise OSError("simulated write failure")

        return original(
            self,
            data,
            encoding=encoding,
            errors=errors,
            newline=newline,
        )

    monkeypatch.setattr(
        Path,
        "write_text",
        fail_write,
    )

    with pytest.raises(ExecutionReportError):
        renderer.write_suite(
            _session(),
            tmp_path,
        )


def test_write_failure_cleans_temporary_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    renderer = ExecutionControllerRenderer()

    def fail_write(
        self: Path,
        data: str,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> int:
        raise OSError("simulated failure")

    monkeypatch.setattr(
        Path,
        "write_text",
        fail_write,
    )

    with pytest.raises(ExecutionReportError):
        renderer.write_suite(
            _session(),
            tmp_path,
        )

    assert not tuple(tmp_path.glob("*.tmp"))
