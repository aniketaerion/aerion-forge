import pytest
from pydantic import ValidationError

from forge.domain_intelligence.database.models import (
    DatabaseAnalysisReport,
    DatabaseColumn,
    DatabaseConstraint,
    DatabaseEngine,
    DatabaseFinding,
    DatabaseFindingSeverity,
    DatabaseObjectKind,
    DatabaseProject,
    DatabaseTable,
)


def test_database_table_supports_constraints() -> None:
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
        constraints=(
            DatabaseConstraint(
                constraint_id="constraint-1",
                name="orders_pkey",
                kind=DatabaseObjectKind.PRIMARY_KEY,
                columns=("id",),
            ),
        ),
    )

    assert table.constraints[0].kind is DatabaseObjectKind.PRIMARY_KEY


def test_database_table_rejects_duplicate_columns() -> None:
    column = DatabaseColumn(
        column_id="column-1",
        name="id",
        data_type="uuid",
        ordinal_position=1,
    )

    with pytest.raises(ValidationError):
        DatabaseTable(
            table_id="table-1",
            schema_name="public",
            name="orders",
            columns=(column, column),
        )


def test_database_report_rejects_duplicate_findings() -> None:
    project = DatabaseProject(
        project_id="database-project-1",
        root="apps/erp",
        engines=(DatabaseEngine.POSTGRESQL,),
    )
    finding = DatabaseFinding(
        finding_id="database-finding-1",
        category="schema",
        severity=DatabaseFindingSeverity.INFO,
        message="Schema detected.",
    )

    with pytest.raises(ValidationError):
        DatabaseAnalysisReport(
            report_id="database-report-1",
            project=project,
            findings=(finding, finding),
        )