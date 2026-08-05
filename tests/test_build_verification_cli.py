from pathlib import Path

from pytest import MonkeyPatch
from typer.testing import CliRunner

from forge.build_verification.cli import build_verification_app

runner = CliRunner()


def initialize_git_repository(tmp_path: Path) -> None:
    import subprocess

    subprocess.run(
        ("git", "init"),
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ("git", "config", "user.email", "test@example.com"),
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ("git", "config", "user.name", "Test User"),
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    (tmp_path / "sample.py").write_text(
        "value = 1\n",
        encoding="utf-8",
    )
    subprocess.run(
        ("git", "add", "sample.py"),
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ("git", "commit", "-m", "initial"),
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )


def test_cli_help() -> None:
    result = runner.invoke(build_verification_app, ["--help"])

    assert result.exit_code == 0
    assert "bounded build verification" in result.stdout


def test_cli_list_empty(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        build_verification_app,
        ["list", "--json"],
    )

    assert result.exit_code == 0
    assert "[]" in result.stdout


def test_cli_run_approves_valid_python_file(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    initialize_git_repository(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        build_verification_app,
        [
            "run",
            "--objective",
            "verify sample",
            "--tool",
            "ruff",
            "--path",
            "sample.py",
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert '"decision":"approved"' in result.stdout.replace(" ", "")