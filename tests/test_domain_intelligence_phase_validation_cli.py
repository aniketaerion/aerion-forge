from pathlib import Path

from typer.testing import CliRunner

from forge.domain_intelligence.phase_validation.cli import (
    phase_validation_app,
)

runner = CliRunner()


def initialize_repository(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    path = (
        tmp_path
        / "docs"
        / "domain_intelligence"
        / "phase_validation"
    )
    path.mkdir(parents=True)
    (path / "ARCHITECTURE.md").write_text(
        "# Architecture",
        encoding="utf-8",
    )
    (path / "ACCEPTANCE_CRITERIA.md").write_text(
        "# Acceptance\n\n- Architecture exists.\n",
        encoding="utf-8",
    )


def test_phase_validation_validate_command(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    result = runner.invoke(
        phase_validation_app,
        [
            "validate",
            "--repository-root",
            str(tmp_path),
            "--phase",
            "4",
            "--milestone",
            "M4.8",
        ],
    )

    assert result.exit_code == 0
    normalized = " ".join(result.stdout.split())
    assert "Phase Validation Intelligence" in normalized
    assert "PASS" in normalized


def test_phase_validation_summary_command(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    result = runner.invoke(
        phase_validation_app,
        [
            "summary",
            "--repository-root",
            str(tmp_path),
            "--phase",
            "4",
        ],
    )

    assert result.exit_code == 0
    assert '"check_count"' in result.stdout
    assert '"passed"' in result.stdout


def test_phase_validation_report_command(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    result = runner.invoke(
        phase_validation_app,
        [
            "report",
            "--repository-root",
            str(tmp_path),
            "--phase",
            "4",
            "--destination",
            "reports/phase-validation",
        ],
    )

    assert result.exit_code == 0

    report_root = tmp_path / "reports" / "phase-validation"

    assert (
        report_root / "PHASE_VALIDATION_REPORT.json"
    ).is_file()
    assert (
        report_root / "PHASE_VALIDATION_SUMMARY.json"
    ).is_file()
    assert (
        report_root / "PHASE_VALIDATION_REPORT.md"
    ).is_file()