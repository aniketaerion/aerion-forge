from pathlib import Path

from typer.testing import CliRunner

from forge.domain_intelligence.database.cli import database_app

runner = CliRunner()


def initialize_repository(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()


def initialize_database(tmp_path: Path) -> None:
    (tmp_path / "docker-compose.yml").write_text(
        "services:\n  db:\n    image: postgres:16\n",
        encoding="utf-8",
    )
    (tmp_path / "schema.sql").write_text(
        """
        CREATE TABLE public.orders (
            id uuid NOT NULL,
            PRIMARY KEY (id)
        );
        """,
        encoding="utf-8",
    )


def test_database_cli_help() -> None:
    result = runner.invoke(database_app, ["--help"])

    assert result.exit_code == 0
    assert "database architecture" in result.stdout


def test_database_cli_analyze_json(tmp_path: Path) -> None:
    initialize_repository(tmp_path)
    initialize_database(tmp_path)

    result = runner.invoke(
        database_app,
        [
            "analyze",
            "--repository-root",
            str(tmp_path),
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert '"engines"' in result.stdout
    assert "postgresql" in result.stdout
    assert "orders" in result.stdout


def test_database_cli_report_writes_bundle(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)
    initialize_database(tmp_path)

    result = runner.invoke(
        database_app,
        [
            "report",
            "--repository-root",
            str(tmp_path),
            "--destination",
            "reports/database",
        ],
    )

    assert result.exit_code == 0
    assert (
        tmp_path
        / "reports"
        / "database"
        / "DATABASE_ANALYSIS.json"
    ).is_file()
    assert (
        tmp_path
        / "reports"
        / "database"
        / "DATABASE_ANALYSIS.md"
    ).is_file()


def test_database_cli_validate(tmp_path: Path) -> None:
    initialize_repository(tmp_path)

    result = runner.invoke(
        database_app,
        [
            "validate",
            "--repository-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "validation passed" in result.stdout.lower()