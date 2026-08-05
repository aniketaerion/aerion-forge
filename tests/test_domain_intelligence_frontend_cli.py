import json
from pathlib import Path

from typer.testing import CliRunner

from forge.domain_intelligence.frontend.cli import frontend_app

runner = CliRunner()


def initialize_repository(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()


def initialize_frontend(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "dependencies": {
                    "react": "^19.0.0",
                },
                "devDependencies": {
                    "vite": "^7.0.0",
                },
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "package-lock.json").write_text(
        "{}",
        encoding="utf-8",
    )


def test_frontend_cli_help() -> None:
    result = runner.invoke(frontend_app, ["--help"])

    assert result.exit_code == 0
    assert "frontend architecture" in result.stdout


def test_frontend_cli_analyze_json(tmp_path: Path) -> None:
    initialize_repository(tmp_path)
    initialize_frontend(tmp_path)

    result = runner.invoke(
        frontend_app,
        [
            "analyze",
            "--repository-root",
            str(tmp_path),
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert '"frameworks"' in result.stdout
    assert "react" in result.stdout
    assert "vite" in result.stdout


def test_frontend_cli_report_writes_bundle(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)
    initialize_frontend(tmp_path)

    result = runner.invoke(
        frontend_app,
        [
            "report",
            "--repository-root",
            str(tmp_path),
            "--destination",
            "reports/frontend",
        ],
    )

    assert result.exit_code == 0
    assert (
        tmp_path
        / "reports"
        / "frontend"
        / "FRONTEND_ANALYSIS.json"
    ).is_file()
    assert (
        tmp_path
        / "reports"
        / "frontend"
        / "FRONTEND_ANALYSIS.md"
    ).is_file()


def test_frontend_cli_validate(tmp_path: Path) -> None:
    initialize_repository(tmp_path)

    result = runner.invoke(
        frontend_app,
        [
            "validate",
            "--repository-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "validation passed" in result.stdout.lower()