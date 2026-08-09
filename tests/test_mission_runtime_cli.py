import json
from pathlib import Path

from typer.testing import CliRunner

from forge.mission_runtime.cli import app

runner = CliRunner()


def initialize_repository(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()


def test_mission_runtime_about_command() -> None:
    result = runner.invoke(app, ["about"])
    assert result.exit_code == 0
    assert "M5.8 Forge Mission Runtime" in result.stdout


def test_mission_runtime_help_exposes_public_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "run" in result.stdout
    assert "approve" in result.stdout
    assert "show" in result.stdout
    assert "list" in result.stdout


def test_mission_runtime_run_creates_persisted_session(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    result = runner.invoke(
        app,
        [
            "run",
            "Plan calculator change",
            "--repository-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "Session ID:" in result.stdout
    assert "Status: awaiting_approval" in result.stdout


def test_mission_runtime_run_and_approve(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    created = runner.invoke(
        app,
        [
            "run",
            "Plan calculator change",
            "--repository-root",
            str(tmp_path),
            "--json",
        ],
    )

    assert created.exit_code == 0
    payload = json.loads(created.stdout)

    approved = runner.invoke(
        app,
        [
            "approve",
            payload["session_id"],
            "--repository-root",
            str(tmp_path),
            "--reason",
            "approved for test",
        ],
    )

    assert approved.exit_code == 0
    assert "Status: completed" in approved.stdout