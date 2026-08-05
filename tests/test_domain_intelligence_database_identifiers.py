from forge.domain_intelligence.database.identifiers import (
    database_object_identifier,
    database_project_identifier,
)


def test_database_project_identifier_is_deterministic() -> None:
    first = database_project_identifier(
        {"root": "apps/erp", "engine": "postgresql"}
    )
    second = database_project_identifier(
        {"engine": "postgresql", "root": "apps/erp"}
    )

    assert first == second
    assert first.startswith("database-project-")


def test_database_object_identifier_changes_by_object() -> None:
    first = database_object_identifier(
        {"schema": "public", "table": "orders"}
    )
    second = database_object_identifier(
        {"schema": "public", "table": "inventory"}
    )

    assert first != second