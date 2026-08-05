from pathlib import Path

from forge.domain_intelligence.database.discovery import (
    discover_migration_files,
    discover_query_files,
    discover_schema_files,
)


def test_database_artifact_discovery(tmp_path: Path) -> None:
    migrations = tmp_path / "migrations"
    migrations.mkdir()

    (tmp_path / "schema.sql").write_text(
        "CREATE TABLE orders(id uuid);",
        encoding="utf-8",
    )
    (migrations / "001_create_orders.sql").write_text(
        "CREATE TABLE orders(id uuid);",
        encoding="utf-8",
    )
    (tmp_path / "queries.sql").write_text(
        "SELECT * FROM orders;",
        encoding="utf-8",
    )

    assert discover_schema_files(tmp_path) == (
        "schema.sql",
    )
    assert discover_migration_files(tmp_path) == (
        "migrations/001_create_orders.sql",
    )
    assert discover_query_files(tmp_path) == (
        "migrations/001_create_orders.sql",
        "queries.sql",
        "schema.sql",
    )