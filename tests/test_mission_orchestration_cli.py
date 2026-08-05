from pathlib import Path

from pytest import MonkeyPatch
from typer.testing import CliRunner

from forge.mission_orchestration.cli import mission_orchestration_app

runner = CliRunner()


def test_cli_help() -> None:
    result = runner.invoke(mission_orchestration_app, ["--help"])

    assert result.exit_code == 0
    assert "bounded engineering missions" in result.stdout


def test_cli_create_and_show(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "sample.py").write_bytes(b"print('ok')\n")

    created = runner.invoke(
        mission_orchestration_app,
        [
            "create",
            "--objective",
            "test mission",
            "--path",
            "sample.py",
            "--json",
        ],
    )

    assert created.exit_code == 0
    assert "mission_id" in created.stdout


def test_cli_list_empty(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        mission_orchestration_app,
        ["list", "--json"],
    )

    assert result.exit_code == 0
    assert "[]" in result.stdout