"""Database risk analysis for M4.3 Database Domain Intelligence."""

from __future__ import annotations

from forge.domain_intelligence.database.identifiers import (
    database_finding_identifier,
)
from forge.domain_intelligence.database.models import (
    DatabaseFinding,
    DatabaseFindingSeverity,
    DatabaseObjectKind,
    DatabaseTable,
)


def database_risk_findings(
    tables: tuple[DatabaseTable, ...],
) -> tuple[DatabaseFinding, ...]:
    """Identify conservative schema risks."""
    findings: list[DatabaseFinding] = []

    for table in tables:
        has_primary_key = any(
            constraint.kind is DatabaseObjectKind.PRIMARY_KEY
            for constraint in table.constraints
        )

        if not has_primary_key:
            finding_id = database_finding_identifier(
                {
                    "category": "missing_primary_key",
                    "schema": table.schema_name,
                    "table": table.name,
                }
            )
            findings.append(
                DatabaseFinding(
                    finding_id=finding_id,
                    category="missing_primary_key",
                    severity=DatabaseFindingSeverity.HIGH,
                    message=(
                        "Table has no detected primary key: "
                        f"{table.schema_name}.{table.name}"
                    ),
                    evidence={
                        "schema": table.schema_name,
                        "table": table.name,
                    },
                )
            )

        indexed_columns = {
            column
            for index in table.indexes
            for column in index.columns
        }

        for constraint in table.constraints:
            if constraint.kind is not DatabaseObjectKind.FOREIGN_KEY:
                continue

            missing = tuple(
                column
                for column in constraint.columns
                if column not in indexed_columns
            )

            if not missing:
                continue

            finding_id = database_finding_identifier(
                {
                    "category": "unindexed_foreign_key",
                    "schema": table.schema_name,
                    "table": table.name,
                    "constraint": constraint.name,
                    "columns": missing,
                }
            )
            findings.append(
                DatabaseFinding(
                    finding_id=finding_id,
                    category="unindexed_foreign_key",
                    severity=DatabaseFindingSeverity.MEDIUM,
                    message=(
                        "Foreign-key columns have no detected index: "
                        f"{table.schema_name}.{table.name}"
                    ),
                    evidence={
                        "constraint": constraint.name,
                        "columns": ",".join(missing),
                    },
                )
            )

    return tuple(
        sorted(findings, key=lambda finding: finding.finding_id)
    )