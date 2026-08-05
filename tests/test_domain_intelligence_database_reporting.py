import json
from pathlib import Path

from forge.domain_intelligence.database.models import (
    DatabaseAnalysisReport,
    DatabaseColumn,
    DatabaseEngine,
    DatabaseFinding,
    DatabaseFindingSeverity,
    DatabaseProject,
    DatabaseTable,
)
from forge.domain_intelligence.database.reporting import (
    database_report_summary,
    render_database_markdown,
    write_database_report_bundle,
)


def report_for() -> DatabaseAnalysisReport:
    project = DatabaseProject(
        project_id="database-project-1",
        root="apps/erp",
        engines=(DatabaseEngine.POSTGRESQL,),
        schema_files=("schema.sql",),
        migration_files=("migrations/001.sql",),
        query_files=("queries.sql",),
        configuration_files=("docker-compose.yml",),
    )
    table = DatabaseTable(
        table_id="table-1",
        schema_name="public",
        name="orders",
        columns=(
            DatabaseColumn(
                column_id="column-1",
                name="id",
                data_type="uuid",
                nullable=False,
                ordinal_position=1,
            ),
        ),
    )
    finding = DatabaseFinding(
        finding_id="finding-1",
        category="missing_primary_key",
        severity=DatabaseFindingSeverity.HIGH,
        message="Primary key missing.",
    )

    return DatabaseAnalysisReport(
        report_id="database-report-1",
        project=project,
        tables=(table,),
        findings=(finding,),
    )


def test_database_report_summary() -> None:
    summary = database_report_summary(report_for())

    assert summary["table_count"] == 1
    assert summary["column_count"] == 1
    assert summary["finding_categories"] == {
        "missing_primary_key": 1
    }


def test_database_markdown_contains_table() -> None:
    rendered = render_database_markdown(report_for())

    assert "Database Intelligence Report" in rendered
    assert "public.orders" in rendered
    assert "schema.sql" in rendered


def test_database_report_bundle_writes_files(
    tmp_path: Path,
) -> None:
    written = write_database_report_bundle(
        report_for(),
        tmp_path / "reports",
    )

    assert set(written) == {
        "DATABASE_ANALYSIS.json",
        "DATABASE_SUMMARY.json",
        "DATABASE_ANALYSIS.md",
    }

    summary = json.loads(
        written["DATABASE_SUMMARY.json"].read_text(
            encoding="utf-8"
        )
    )
    assert summary["finding_count"] == 1