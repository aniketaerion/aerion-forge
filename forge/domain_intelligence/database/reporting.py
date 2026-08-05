"""Reporting for M4.3 Database Domain Intelligence."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from forge.domain_intelligence.database.errors import (
    DatabaseIntelligenceError,
)
from forge.domain_intelligence.database.models import (
    DatabaseAnalysisReport,
)


def database_report_summary(
    report: DatabaseAnalysisReport,
) -> dict[str, object]:
    """Return a deterministic database summary."""
    categories = Counter(
        finding.category for finding in report.findings
    )

    relationship_count = sum(
        1
        for table in report.tables
        for constraint in table.constraints
        if constraint.referenced_table is not None
    )

    return {
        "report_id": report.report_id,
        "project_id": report.project.project_id,
        "project_root": report.project.root,
        "engines": [
            engine.value for engine in report.project.engines
        ],
        "schema_file_count": len(
            report.project.schema_files
        ),
        "migration_file_count": len(
            report.project.migration_files
        ),
        "query_file_count": len(
            report.project.query_files
        ),
        "configuration_file_count": len(
            report.project.configuration_files
        ),
        "table_count": len(report.tables),
        "column_count": sum(
            len(table.columns) for table in report.tables
        ),
        "constraint_count": sum(
            len(table.constraints) for table in report.tables
        ),
        "index_count": sum(
            len(table.indexes) for table in report.tables
        ),
        "relationship_count": relationship_count,
        "finding_count": len(report.findings),
        "finding_categories": dict(
            sorted(categories.items())
        ),
    }


def render_database_markdown(
    report: DatabaseAnalysisReport,
) -> str:
    """Render a stable Markdown database-intelligence report."""
    summary = database_report_summary(report)

    lines = [
        "# Database Intelligence Report",
        "",
        f"- Report ID: `{report.report_id}`",
        f"- Project ID: `{report.project.project_id}`",
        f"- Project root: `{report.project.root}`",
        (
            "- Engines: "
            + ", ".join(
                engine.value
                for engine in report.project.engines
            )
        ),
        f"- Tables: `{summary['table_count']}`",
        f"- Columns: `{summary['column_count']}`",
        f"- Constraints: `{summary['constraint_count']}`",
        f"- Indexes: `{summary['index_count']}`",
        f"- Relationships: `{summary['relationship_count']}`",
        f"- Findings: `{summary['finding_count']}`",
        "",
        "## Database Artifacts",
        "",
        (
            "- Schema files: "
            + (
                ", ".join(report.project.schema_files)
                if report.project.schema_files
                else "none detected"
            )
        ),
        (
            "- Migration files: "
            + (
                ", ".join(report.project.migration_files)
                if report.project.migration_files
                else "none detected"
            )
        ),
        (
            "- Query files: "
            + (
                ", ".join(report.project.query_files)
                if report.project.query_files
                else "none detected"
            )
        ),
        (
            "- Configuration files: "
            + (
                ", ".join(
                    report.project.configuration_files
                )
                if report.project.configuration_files
                else "none detected"
            )
        ),
        "",
        "## Tables",
        "",
    ]

    if not report.tables:
        lines.append("No database tables were parsed.")
        lines.append("")
    else:
        for table in report.tables:
            lines.extend(
                [
                    (
                        f"### {table.schema_name}."
                        f"{table.name}"
                    ),
                    "",
                    f"- Columns: `{len(table.columns)}`",
                    (
                        "- Constraints: "
                        f"`{len(table.constraints)}`"
                    ),
                    f"- Indexes: `{len(table.indexes)}`",
                    "",
                ]
            )

            if table.columns:
                lines.append("| Column | Type | Nullable | Default |")
                lines.append("|---|---|---:|---|")

                for column in table.columns:
                    lines.append(
                        "| "
                        f"{column.name} | "
                        f"{column.data_type} | "
                        f"{'yes' if column.nullable else 'no'} | "
                        f"{column.default or ''} |"
                    )

                lines.append("")

    lines.extend(
        [
            "## Findings",
            "",
        ]
    )

    if not report.findings:
        lines.append("No database findings were produced.")
    else:
        for finding in report.findings:
            lines.extend(
                [
                    f"### {finding.category}",
                    "",
                    f"- Finding ID: `{finding.finding_id}`",
                    f"- Severity: `{finding.severity.value}`",
                    f"- Message: {finding.message}",
                    (
                        f"- Path: `{finding.path}`"
                        if finding.path is not None
                        else "- Path: not applicable"
                    ),
                ]
            )

            if finding.evidence:
                lines.append("- Evidence:")
                for key, value in sorted(
                    finding.evidence.items()
                ):
                    lines.append(
                        f"  - `{key}`: `{value}`"
                    )

            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_database_report_bundle(
    report: DatabaseAnalysisReport,
    destination: Path,
) -> dict[str, Path]:
    """Write JSON, summary JSON, and Markdown reports."""
    try:
        destination.mkdir(parents=True, exist_ok=True)

        raw_json = destination / "DATABASE_ANALYSIS.json"
        summary_json = destination / "DATABASE_SUMMARY.json"
        markdown = destination / "DATABASE_ANALYSIS.md"

        raw_json.write_text(
            json.dumps(
                report.model_dump(mode="json"),
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        summary_json.write_text(
            json.dumps(
                database_report_summary(report),
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        markdown.write_text(
            render_database_markdown(report),
            encoding="utf-8",
        )
    except OSError as exc:
        raise DatabaseIntelligenceError(
            f"unable to write database report bundle: {destination}"
        ) from exc

    return {
        raw_json.name: raw_json,
        summary_json.name: summary_json,
        markdown.name: markdown,
    }