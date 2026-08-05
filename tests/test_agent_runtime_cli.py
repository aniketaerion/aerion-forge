from pathlib import Path

from pytest import MonkeyPatch
from typer.testing import CliRunner

from forge.agent_runtime.cli import agent_app

runner = CliRunner()


def initialize_repository(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()


def test_agent_cli_help() -> None:
    result = runner.invoke(agent_app, ["--help"])

    assert result.exit_code == 0
    assert "unified engineering-agent" in result.stdout


def test_agent_cli_create_and_list(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    initialize_repository(tmp_path)
    monkeypatch.chdir(tmp_path)

    created = runner.invoke(
        agent_app,
        [
            "create",
            "--objective",
            "Plan feature",
            "--repository-root",
            str(tmp_path),
        ],
    )

    listed = runner.invoke(
        agent_app,
        [
            "list",
            "--repository-root",
            str(tmp_path),
        ],
    )

    assert created.exit_code == 0
    assert listed.exit_code == 0
    assert "agent-session-" in listed.stdout