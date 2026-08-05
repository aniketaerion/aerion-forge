from pathlib import Path

from typer.testing import CliRunner

from forge.domain_intelligence.api.cli import api_app

runner = CliRunner()


def initialize_repository(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()


def initialize_api(tmp_path: Path) -> None:
    (tmp_path / "openapi.yaml").write_text(
        """
        openapi: 3.0.0
        info:
          title: ERP API
          version: 1.0.0
        paths:
          /v1/orders:
            get:
              operationId: listOrders
              responses:
                "200":
                  description: Success
        """,
        encoding="utf-8",
    )


def test_api_cli_help() -> None:
    result = runner.invoke(api_app, ["--help"])

    assert result.exit_code == 0
    assert "API architecture" in result.stdout


def test_api_cli_analyze_json(tmp_path: Path) -> None:
    initialize_repository(tmp_path)
    initialize_api(tmp_path)

    result = runner.invoke(
        api_app,
        [
            "analyze",
            "--repository-root",
            str(tmp_path),
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert '"styles"' in result.stdout
    assert "openapi" in result.stdout
    assert "/v1/orders" in result.stdout


def test_api_cli_report_writes_bundle(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)
    initialize_api(tmp_path)

    result = runner.invoke(
        api_app,
        [
            "report",
            "--repository-root",
            str(tmp_path),
            "--destination",
            "reports/api",
        ],
    )

    assert result.exit_code == 0
    assert (
        tmp_path / "reports" / "api" / "API_ANALYSIS.json"
    ).is_file()
    assert (
        tmp_path / "reports" / "api" / "API_ANALYSIS.md"
    ).is_file()


def test_api_cli_validate(tmp_path: Path) -> None:
    initialize_repository(tmp_path)

    result = runner.invoke(
        api_app,
        [
            "validate",
            "--repository-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "validation passed" in result.stdout.lower()