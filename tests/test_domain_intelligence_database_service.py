from pathlib import Path

from forge.domain_intelligence.database.models import (
    DatabaseAnalysisRequest,
    DatabaseEngine,
)
from forge.domain_intelligence.database.service import (
    DatabaseIntelligenceService,
    default_database_registry,
)


def initialize_repository(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()


def test_default_database_registry() -> None:
    assert default_database_registry().names() == (
        "configuration",
        "discovery",
        "postgres",
    )


def test_service_discovers_postgresql_project(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    migrations = tmp_path / "migrations"
    migrations.mkdir()

    (tmp_path / "docker-compose.yml").write_text(
        "services:\n  db:\n    image: postgres:16\n",
        encoding="utf-8",
    )
    (tmp_path / "schema.sql").write_text(
        "CREATE TABLE orders(id uuid);",
        encoding="utf-8",
    )
    (migrations / "001_create_orders.sql").write_text(
        "CREATE TABLE orders(id uuid);",
        encoding="utf-8",
    )

    report = DatabaseIntelligenceService().analyze(
        DatabaseAnalysisRequest(
            repository_root=str(tmp_path),
        )
    )

    assert report.project.engines == (
        DatabaseEngine.POSTGRESQL,
    )
    assert report.project.schema_files == (
        "schema.sql",
    )
    assert report.project.migration_files == (
        "migrations/001_create_orders.sql",
    )


def test_service_reports_unknown_database(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    report = DatabaseIntelligenceService().analyze(
        DatabaseAnalysisRequest(
            repository_root=str(tmp_path),
        )
    )

    assert report.project.engines == (
        DatabaseEngine.UNKNOWN,
    )