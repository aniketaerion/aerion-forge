from pathlib import Path

from typer.testing import CliRunner

from forge.domain_intelligence.embedded.cli import embedded_app

runner = CliRunner()


def initialize_repository(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()


def initialize_px4_project(tmp_path: Path) -> None:
    module = tmp_path / "src" / "modules" / "navigator"
    module.mkdir(parents=True)
    (tmp_path / "CMakeLists.txt").write_text(
        "project(px4)",
        encoding="utf-8",
    )
    (module / "navigator.cpp").write_text(
        "UART_Init();\n",
        encoding="utf-8",
    )


def test_embedded_analyze_command(tmp_path: Path) -> None:
    initialize_repository(tmp_path)
    initialize_px4_project(tmp_path)

    result = runner.invoke(
        embedded_app,
        [
            "analyze",
            "--repository-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    normalized = " ".join(result.stdout.split())
    assert "Embedded Domain Intelligence" in normalized
    assert "px4" in normalized.lower()


def test_embedded_summary_command(tmp_path: Path) -> None:
    initialize_repository(tmp_path)

    result = runner.invoke(
        embedded_app,
        [
            "summary",
            "--repository-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert '"component_count"' in result.stdout
    assert '"finding_count"' in result.stdout


def test_embedded_report_command(tmp_path: Path) -> None:
    initialize_repository(tmp_path)

    result = runner.invoke(
        embedded_app,
        [
            "report",
            "--repository-root",
            str(tmp_path),
            "--destination",
            "reports/embedded",
        ],
    )

    assert result.exit_code == 0
    assert (
        tmp_path
        / "reports"
        / "embedded"
        / "EMBEDDED_ANALYSIS.json"
    ).is_file()
    assert (
        tmp_path
        / "reports"
        / "embedded"
        / "EMBEDDED_SUMMARY.json"
    ).is_file()
    assert (
        tmp_path
        / "reports"
        / "embedded"
        / "EMBEDDED_ANALYSIS.md"
    ).is_file()


def test_embedded_validate_command(tmp_path: Path) -> None:
    initialize_repository(tmp_path)

    result = runner.invoke(
        embedded_app,
        [
            "validate",
            "--repository-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "validation passed" in result.stdout.lower()