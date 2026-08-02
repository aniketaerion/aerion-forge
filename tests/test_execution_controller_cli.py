"""Execution Controller CLI tests."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

import forge.execution_controller.cli as execution_cli
from forge.cli import app
from forge.config.settings import Settings
from forge.execution_controller.builder import ExecutionControllerBuilder
from forge.execution_controller.models import ExecutionState

runner = CliRunner()


def _settings(tmp_path: Path) -> Settings:
    settings = Settings(
        repository_path=tmp_path,
        workspace_path=tmp_path / "workspaces",
        reports_path=tmp_path / "reports" / "latest",
        memory_path=tmp_path / "memory",
        logs_path=tmp_path / "logs",
    )
    settings.ensure_runtime_directories()
    return settings


def _patch_settings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Settings:
    settings = _settings(tmp_path)

    monkeypatch.setattr(
        execution_cli,
        "_settings",
        lambda: settings,
    )

    return settings


def _create_request(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Settings:
    settings = _patch_settings(
        tmp_path,
        monkeypatch,
    )

    result = runner.invoke(
        execution_cli.execution_app,
        [
            "request",
            "mission-123",
            "--task",
            "task-a",
            "--operation",
            "edit",
        ],
    )

    assert result.exit_code == 0

    return settings


def _write_session(settings: Settings) -> None:
    builder = ExecutionControllerBuilder()

    request = builder.build_request(
        mission_id="mission-123",
        task_ids=("task-a",),
        requested_operations=("edit",),
        dry_run=True,
        source_fingerprints={},
    )

    session = builder.build_session(
        request,
        current_state=ExecutionState.REQUESTED,
    )

    path = settings.memory_path / execution_cli.SESSION_FILE

    path.write_text(
        session.model_dump_json(),
        encoding="utf-8",
        newline="\n",
    )


def test_execution_help_contract() -> None:
    result = runner.invoke(
        execution_cli.execution_app,
        ["--help"],
    )

    assert result.exit_code == 0
    assert "request" in result.stdout
    assert "validate" in result.stdout
    assert "show" in result.stdout
    assert "list" in result.stdout


def test_execution_registered_in_root_help() -> None:
    result = runner.invoke(
        app,
        ["--help"],
    )

    assert result.exit_code == 0
    assert "execution" in result.stdout


def test_request_creates_persisted_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _create_request(
        tmp_path,
        monkeypatch,
    )

    assert (settings.memory_path / execution_cli.REQUEST_FILE).is_file()


def test_request_output_contains_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_settings(tmp_path, monkeypatch)

    result = runner.invoke(
        execution_cli.execution_app,
        [
            "request",
            "mission-123",
            "--task",
            "task-a",
            "--operation",
            "edit",
        ],
    )

    assert result.exit_code == 0
    assert "Request ID:" in result.stdout
    assert "Mission ID:" in result.stdout
    assert "mission-123" in result.stdout


def test_request_json_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_settings(tmp_path, monkeypatch)

    result = runner.invoke(
        execution_cli.execution_app,
        [
            "request",
            "mission-123",
            "--task",
            "task-a",
            "--operation",
            "edit",
            "--json",
        ],
    )

    assert result.exit_code == 0

    payload = json.loads(result.stdout)

    assert payload["mission_id"] == "mission-123"
    assert payload["dry_run"] is True


def test_request_execute_flag_sets_non_dry_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_settings(tmp_path, monkeypatch)

    result = runner.invoke(
        execution_cli.execution_app,
        [
            "request",
            "mission-123",
            "--task",
            "task-a",
            "--operation",
            "edit",
            "--execute",
            "--json",
        ],
    )

    assert result.exit_code == 0

    payload = json.loads(result.stdout)

    assert payload["dry_run"] is False


def test_repeated_request_is_deterministic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _patch_settings(
        tmp_path,
        monkeypatch,
    )

    arguments = [
        "request",
        "mission-123",
        "--task",
        "task-a",
        "--operation",
        "edit",
        "--json",
    ]

    first = runner.invoke(
        execution_cli.execution_app,
        arguments,
    )
    second = runner.invoke(
        execution_cli.execution_app,
        arguments,
    )

    assert first.exit_code == 0
    assert second.exit_code == 0
    assert json.loads(first.stdout) == json.loads(second.stdout)

    persisted = json.loads(
        (settings.memory_path / execution_cli.REQUEST_FILE).read_text(encoding="utf-8")
    )

    assert persisted == json.loads(second.stdout)


def test_show_request(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _create_request(tmp_path, monkeypatch)

    result = runner.invoke(
        execution_cli.execution_app,
        ["show"],
    )

    assert result.exit_code == 0
    assert "mission-123" in result.stdout
    assert "Request ID:" in result.stdout


def test_show_request_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _create_request(tmp_path, monkeypatch)

    result = runner.invoke(
        execution_cli.execution_app,
        ["show", "--json"],
    )

    assert result.exit_code == 0

    payload = json.loads(result.stdout)

    assert payload["mission_id"] == "mission-123"


def test_show_missing_request_returns_five(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_settings(tmp_path, monkeypatch)

    result = runner.invoke(
        execution_cli.execution_app,
        ["show"],
    )

    assert result.exit_code == 5
    assert "No persisted execution request" in result.stdout


def test_show_rejects_unknown_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_settings(tmp_path, monkeypatch)

    result = runner.invoke(
        execution_cli.execution_app,
        ["show", "--artifact", "unknown"],
    )

    assert result.exit_code == 5
    assert "request' or 'session" in result.stdout


def test_show_corrupt_request_returns_five(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _patch_settings(
        tmp_path,
        monkeypatch,
    )

    (settings.memory_path / execution_cli.REQUEST_FILE).write_text(
        "{broken",
        encoding="utf-8",
    )

    result = runner.invoke(
        execution_cli.execution_app,
        ["show"],
    )

    assert result.exit_code == 5
    assert "Persisted execution request is invalid" in result.stdout


def test_validate_matching_request_passes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _create_request(tmp_path, monkeypatch)

    result = runner.invoke(
        execution_cli.execution_app,
        ["validate"],
    )

    assert result.exit_code == 0
    assert "Valid:" in result.stdout
    assert "yes" in result.stdout


def test_validate_json_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _create_request(tmp_path, monkeypatch)

    result = runner.invoke(
        execution_cli.execution_app,
        ["validate", "--json"],
    )

    assert result.exit_code == 0

    payload = json.loads(result.stdout)

    assert payload["valid"] is True
    assert payload["findings"] == []


def test_validate_mission_mismatch_returns_five(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _create_request(tmp_path, monkeypatch)

    result = runner.invoke(
        execution_cli.execution_app,
        [
            "validate",
            "--mission",
            "mission-other",
        ],
    )

    assert result.exit_code == 5
    assert "mission-id-mismatch" in result.stdout


def test_validate_missing_request_returns_five(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_settings(tmp_path, monkeypatch)

    result = runner.invoke(
        execution_cli.execution_app,
        ["validate"],
    )

    assert result.exit_code == 5


def test_list_empty_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_settings(tmp_path, monkeypatch)

    result = runner.invoke(
        execution_cli.execution_app,
        ["list", "--json"],
    )

    assert result.exit_code == 0
    assert json.loads(result.stdout) == []


def test_list_contains_request(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _create_request(tmp_path, monkeypatch)

    result = runner.invoke(
        execution_cli.execution_app,
        ["list", "--json"],
    )

    assert result.exit_code == 0

    payload = json.loads(result.stdout)

    assert len(payload) == 1
    assert payload[0]["artifact_type"] == "request"
    assert payload[0]["size"] > 0


def test_list_table_contains_request(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _create_request(tmp_path, monkeypatch)

    result = runner.invoke(
        execution_cli.execution_app,
        ["list"],
    )

    assert result.exit_code == 0
    assert "Execution Controller Artifacts" in result.stdout
    assert "request" in result.stdout


def test_show_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _patch_settings(
        tmp_path,
        monkeypatch,
    )
    _write_session(settings)

    result = runner.invoke(
        execution_cli.execution_app,
        ["show", "--artifact", "session"],
    )

    assert result.exit_code == 0
    assert "Session ID:" in result.stdout
    assert "requested" in result.stdout


def test_show_session_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _patch_settings(
        tmp_path,
        monkeypatch,
    )
    _write_session(settings)

    result = runner.invoke(
        execution_cli.execution_app,
        [
            "show",
            "--artifact",
            "session",
            "--json",
        ],
    )

    assert result.exit_code == 0

    payload = json.loads(result.stdout)

    assert payload["current_state"] == "requested"
    assert payload["request"]["mission_id"] == "mission-123"


def test_show_missing_session_returns_five(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_settings(tmp_path, monkeypatch)

    result = runner.invoke(
        execution_cli.execution_app,
        ["show", "--artifact", "session"],
    )

    assert result.exit_code == 5
    assert "No persisted execution session" in result.stdout


def test_list_contains_request_and_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _create_request(
        tmp_path,
        monkeypatch,
    )
    _write_session(settings)

    result = runner.invoke(
        execution_cli.execution_app,
        ["list", "--json"],
    )

    assert result.exit_code == 0

    payload = json.loads(result.stdout)

    assert {item["artifact_type"] for item in payload} == {"request", "session"}
