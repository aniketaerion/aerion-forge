from pathlib import Path

from forge.domain_intelligence.database.models import (
    DatabaseAnalysisRequest,
    DatabaseEngine,
    DatabaseObjectKind,
)
from forge.domain_intelligence.database.service import (
    DatabaseIntelligenceService,
    default_database_registry,
)


def initialize_repository(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()


def test_default_database_registry_is_complete() -> None:
    assert default_database_registry().names() == (
        "configuration",
        "discovery",
        "postgres",
    )


def test_service_runs_complete_database_pipeline(
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
        """
        CREATE TABLE public.customers (
            id uuid NOT NULL,
            PRIMARY KEY (id)
        );

        CREATE TABLE public.orders (
            id uuid NOT NULL,
            customer_id uuid NOT NULL,
            PRIMARY KEY (id),
            CONSTRAINT orders_customer_fkey
                FOREIGN KEY (customer_id)
                REFERENCES public.customers(id)
        );

        CREATE INDEX orders_customer_idx
        ON public.orders (customer_id);
        """,
        encoding="utf-8",
    )
    (migrations / "001_create_orders.sql").write_text(
        "CREATE TABLE audit_log(id uuid);",
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
    assert len(report.tables) == 2

    orders = next(
        table
        for table in report.tables
        if table.name == "orders"
    )

    assert any(
        constraint.kind is DatabaseObjectKind.FOREIGN_KEY
        for constraint in orders.constraints
    )
    assert any(
        index.name == "orders_customer_idx"
        for index in orders.indexes
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
    assert not report.tables