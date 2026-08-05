from pathlib import Path

from typer.testing import CliRunner

from forge.domain_intelligence.business_domain.cli import (
    business_domain_app,
)

runner = CliRunner()


def initialize_repository(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()


def test_business_domain_analyze_command(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)
    procurement = tmp_path / "procurement"
    procurement.mkdir()
    (procurement / "models.py").write_text(
        "class PurchaseOrder:\n    pass\n",
        encoding="utf-8",
    )

    result = runner.invoke(
        business_domain_app,
        [
            "analyze",
            "--repository-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    normalized = " ".join(result.stdout.split())
    assert "Business Domain Intelligence" in normalized
def test_business_domain_summary_command(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    result = runner.invoke(
        business_domain_app,
        [
            "summary",
            "--repository-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert '"entity_count"' in result.stdout


def test_business_domain_report_command(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    result = runner.invoke(
        business_domain_app,
        [
            "report",
            "--repository-root",
            str(tmp_path),
            "--destination",
            "reports/business-domain",
        ],
    )

    assert result.exit_code == 0
    assert (
        tmp_path
        / "reports"
        / "business-domain"
        / "BUSINESS_DOMAIN_ANALYSIS.json"
    ).is_file()


def test_business_domain_validate_command(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    result = runner.invoke(
        business_domain_app,
        [
            "validate",
            "--repository-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "validation passed" in result.stdout.lower()