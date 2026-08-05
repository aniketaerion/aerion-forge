import json
from pathlib import Path

from typer.testing import CliRunner

from forge.domain_intelligence.backend.cli import backend_app

runner = CliRunner()


def initialize_repository(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()


def initialize_backend(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "dependencies": {
                    "express": "^5.0.0",
                }
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "package-lock.json").write_text(
        "{}",
        encoding="utf-8",
    )


def test_backend_cli_help() -> None:
    result = runner.invoke(backend_app, ["--help"])

    assert result.exit_code == 0
    assert "backend architecture" in result.stdout


def test_backend_cli_analyze_json(tmp_path: Path) -> None:
    initialize_repository(tmp_path)
    initialize_backend(tmp_path)

    result = runner.invoke(
        backend_app,
        [
            "analyze",
            "--repository-root",
            str(tmp_path),
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert '"frameworks"' in result.stdout
    assert "express" in result.stdout
    assert "node" in result.stdout


def test_backend_cli_report_writes_bundle(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)
    initialize_backend(tmp_path)

    result = runner.invoke(
        backend_app,
        [
            "report",
            "--repository-root",
            str(tmp_path),
            "--destination",
            "reports/backend",
        ],
    )

    assert result.exit_code == 0
    assert (
        tmp_path
        / "reports"
        / "backend"
        / "BACKEND_ANALYSIS.json"
    ).is_file()
    assert (
        tmp_path
        / "reports"
        / "backend"
        / "BACKEND_ANALYSIS.md"
    ).is_file()


def test_backend_cli_validate(tmp_path: Path) -> None:
    initialize_repository(tmp_path)

    result = runner.invoke(
        backend_app,
        [
            "validate",
            "--repository-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "validation passed" in result.stdout.lower()