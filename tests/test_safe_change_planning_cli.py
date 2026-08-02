"""Safe Change Planning CLI tests."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

import forge.safe_change_planning.cli as safe_change_cli
from forge.cli import app
from forge.config.settings import Settings
from forge.safe_change_planning.builder import (
    SafeChangePlanningBuilder,
)
from forge.safe_change_planning.models import (
    ChangeActionType,
    ChangePlanningConfiguration,
    ChangeTargetType,
    PlanningPhaseType,
    SafeChangePlan,
    VerificationType,
)
from forge.safe_change_planning.renderer import (
    SAFE_CHANGE_REPORT_NAMES,
)
from forge.safe_change_planning.service import (
    SAFE_CHANGE_MEMORY_FILE,
    SAFE_CHANGE_REQUEST_FILE,
    SafeChangePlanningService,
)

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
        safe_change_cli,
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
        safe_change_cli.safe_change_app,
        [
            "request",
            "mission-123",
            "--objective",
            "Implement safe change",
            "--task",
            "task-a",
        ],
    )

    assert result.exit_code == 0

    return settings


def _lineage() -> dict[str, str]:
    return {
        "mission": "1",
        "tasks": "2",
        "impact": "3",
        "engineering_memory": "4",
        "mission_report": "5",
        "repository": "6",
        "index": "7",
        "knowledge_graph": "8",
    }


def _build_plan() -> SafeChangePlan:
    builder = SafeChangePlanningBuilder()

    request = builder.build_request(
        mission_id="mission-123",
        task_ids=("task-a",),
        objective="Implement safe change",
        source_fingerprints={
            "mission": "1",
            "tasks": "2",
        },
    )

    target = builder.build_target(
        target_type=ChangeTargetType.FILE,
        path="forge/example.py",
        component="example",
        reason="Required implementation",
        source_ids=("task-a",),
    )

    verification = builder.build_verification_step(
        request_id=request.request_id,
        verification_type=VerificationType.UNIT_TEST,
        description="Run unit tests",
        target_ids=(target.target_id,),
        command="python -m pytest",
    )

    rollback = builder.build_rollback_step(
        request_id=request.request_id,
        description="Restore previous implementation",
        target_ids=(target.target_id,),
    )

    action = builder.build_action(
        request_id=request.request_id,
        target_id=target.target_id,
        action_type=ChangeActionType.MODIFY,
        description="Modify implementation",
        verification_step_ids=(verification.step_id,),
        rollback_step_ids=(rollback.step_id,),
    )

    phase = builder.build_phase(
        request_id=request.request_id,
        phase_type=PlanningPhaseType.IMPLEMENTATION,
        sequence=1,
        title="Implementation",
        action_ids=(action.action_id,),
    )

    return builder.build_plan(
        request=request,
        targets=(target,),
        actions=(action,),
        dependencies=(),
        verification_steps=(verification,),
        rollback_steps=(rollback,),
        phases=(phase,),
        source_fingerprints=_lineage(),
        configuration=ChangePlanningConfiguration(),
    )


def _persist_plan(settings: Settings) -> SafeChangePlan:
    plan = _build_plan()
    service = SafeChangePlanningService()

    service.save_request(
        plan.request,
        settings.memory_path,
    )
    service.save_plan(
        plan,
        settings.memory_path,
    )

    return plan


def test_safe_change_help_contract() -> None:
    result = runner.invoke(
        safe_change_cli.safe_change_app,
        ["--help"],
    )

    assert result.exit_code == 0
    assert "request" in result.stdout
    assert "validate" in result.stdout
    assert "show" in result.stdout
    assert "render" in result.stdout
    assert "list" in result.stdout


def test_safe_change_registered_in_root_help() -> None:
    result = runner.invoke(
        app,
        ["--help"],
    )

    assert result.exit_code == 0
    assert "safe-change" in result.stdout


def test_request_creates_persisted_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _create_request(
        tmp_path,
        monkeypatch,
    )

    assert (settings.memory_path / SAFE_CHANGE_REQUEST_FILE).is_file()


def test_request_human_output_contains_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_settings(tmp_path, monkeypatch)

    result = runner.invoke(
        safe_change_cli.safe_change_app,
        [
            "request",
            "mission-123",
            "--objective",
            "Implement safe change",
            "--task",
            "task-a",
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
        safe_change_cli.safe_change_app,
        [
            "request",
            "mission-123",
            "--objective",
            "Implement safe change",
            "--task",
            "task-a",
            "--json",
        ],
    )

    assert result.exit_code == 0

    payload = json.loads(result.stdout)

    assert payload["mission_id"] == "mission-123"
    assert payload["task_ids"] == ["task-a"]


def test_request_repeated_output_is_deterministic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_settings(tmp_path, monkeypatch)

    arguments = [
        "request",
        "mission-123",
        "--objective",
        "Implement safe change",
        "--task",
        "task-a",
        "--json",
    ]

    first = runner.invoke(
        safe_change_cli.safe_change_app,
        arguments,
    )
    second = runner.invoke(
        safe_change_cli.safe_change_app,
        arguments,
    )

    assert first.exit_code == 0
    assert second.exit_code == 0
    assert json.loads(first.stdout) == json.loads(second.stdout)


def test_validate_matching_request_passes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _create_request(tmp_path, monkeypatch)

    result = runner.invoke(
        safe_change_cli.safe_change_app,
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
        safe_change_cli.safe_change_app,
        ["validate", "--json"],
    )

    assert result.exit_code == 0
    assert json.loads(result.stdout)["valid"] is True


def test_validate_mission_mismatch_returns_five(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _create_request(tmp_path, monkeypatch)

    result = runner.invoke(
        safe_change_cli.safe_change_app,
        [
            "validate",
            "--mission",
            "different-mission",
        ],
    )

    assert result.exit_code == 5


def test_validate_missing_request_returns_two(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_settings(tmp_path, monkeypatch)

    result = runner.invoke(
        safe_change_cli.safe_change_app,
        ["validate"],
    )

    assert result.exit_code == 2


def test_show_request(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _create_request(tmp_path, monkeypatch)

    result = runner.invoke(
        safe_change_cli.safe_change_app,
        ["show", "request"],
    )

    assert result.exit_code == 0
    assert "mission-123" in result.stdout


def test_show_request_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _create_request(tmp_path, monkeypatch)

    result = runner.invoke(
        safe_change_cli.safe_change_app,
        ["show", "request", "--json"],
    )

    assert result.exit_code == 0
    assert json.loads(result.stdout)["mission_id"] == "mission-123"


def test_show_missing_request_returns_two(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_settings(tmp_path, monkeypatch)

    result = runner.invoke(
        safe_change_cli.safe_change_app,
        ["show", "request"],
    )

    assert result.exit_code == 2


def test_show_plan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _patch_settings(
        tmp_path,
        monkeypatch,
    )
    plan = _persist_plan(settings)

    result = runner.invoke(
        safe_change_cli.safe_change_app,
        ["show", "plan"],
    )

    assert result.exit_code == 0
    assert plan.plan_id in result.stdout


def test_show_plan_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _patch_settings(
        tmp_path,
        monkeypatch,
    )
    plan = _persist_plan(settings)

    result = runner.invoke(
        safe_change_cli.safe_change_app,
        ["show", "plan", "--json"],
    )

    assert result.exit_code == 0
    assert json.loads(result.stdout)["plan_id"] == plan.plan_id


def test_show_missing_plan_returns_two(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_settings(tmp_path, monkeypatch)

    result = runner.invoke(
        safe_change_cli.safe_change_app,
        ["show", "plan"],
    )

    assert result.exit_code == 2


def test_list_empty_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_settings(tmp_path, monkeypatch)

    result = runner.invoke(
        safe_change_cli.safe_change_app,
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
        safe_change_cli.safe_change_app,
        ["list", "--json"],
    )

    assert result.exit_code == 0
    assert {artifact["artifact_type"] for artifact in json.loads(result.stdout)} == {"request"}


def test_list_contains_request_and_plan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _patch_settings(
        tmp_path,
        monkeypatch,
    )
    _persist_plan(settings)

    result = runner.invoke(
        safe_change_cli.safe_change_app,
        ["list", "--json"],
    )

    assert result.exit_code == 0
    assert {artifact["artifact_type"] for artifact in json.loads(result.stdout)} == {
        "request",
        "plan",
    }


def test_list_table_contains_plan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _patch_settings(
        tmp_path,
        monkeypatch,
    )
    _persist_plan(settings)

    result = runner.invoke(
        safe_change_cli.safe_change_app,
        ["list"],
    )

    assert result.exit_code == 0
    assert "plan" in result.stdout


def test_render_creates_complete_report_suite(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _patch_settings(
        tmp_path,
        monkeypatch,
    )
    _persist_plan(settings)

    result = runner.invoke(
        safe_change_cli.safe_change_app,
        ["render"],
    )

    assert result.exit_code == 0

    for name in SAFE_CHANGE_REPORT_NAMES:
        assert (settings.reports_path / name).is_file()


def test_render_json_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _patch_settings(
        tmp_path,
        monkeypatch,
    )
    plan = _persist_plan(settings)

    result = runner.invoke(
        safe_change_cli.safe_change_app,
        ["render", "--json"],
    )

    assert result.exit_code == 0

    payload = json.loads(result.stdout)

    assert payload["plan_id"] == plan.plan_id
    assert set(payload["reports"]) == set(SAFE_CHANGE_REPORT_NAMES)


def test_render_missing_plan_returns_two(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_settings(tmp_path, monkeypatch)

    result = runner.invoke(
        safe_change_cli.safe_change_app,
        ["render"],
    )

    assert result.exit_code == 2


def test_corrupt_request_returns_four(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _patch_settings(
        tmp_path,
        monkeypatch,
    )

    (settings.memory_path / SAFE_CHANGE_REQUEST_FILE).write_text(
        "{invalid",
        encoding="utf-8",
    )

    result = runner.invoke(
        safe_change_cli.safe_change_app,
        ["show", "request"],
    )

    assert result.exit_code == 4


def test_corrupt_plan_returns_four(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _patch_settings(
        tmp_path,
        monkeypatch,
    )

    (settings.memory_path / SAFE_CHANGE_MEMORY_FILE).write_text(
        "{invalid",
        encoding="utf-8",
    )

    result = runner.invoke(
        safe_change_cli.safe_change_app,
        ["show", "plan"],
    )

    assert result.exit_code == 4
