[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Content
    )

    $FullPath = Join-Path $RepositoryRoot $Path
    $Directory = Split-Path $FullPath -Parent
    New-Item -ItemType Directory -Path $Directory -Force | Out-Null

    [System.IO.File]::WriteAllText(
        $FullPath,
        $Content,
        [System.Text.UTF8Encoding]::new($false)
    )

    Write-Host "WROTE $Path" -ForegroundColor Green
}

function Assert-CommandSuccess {
    param([Parameter(Mandatory)][string]$Name)

    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

Write-Utf8NoBom "forge\domain_intelligence\database\reporting.py" @'
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
'@

Write-Utf8NoBom "forge\domain_intelligence\database\service.py" @'
"""Complete database analysis service for M4.3."""

from __future__ import annotations

from pathlib import Path

from forge.domain_intelligence.database.configuration import (
    configuration_findings,
    discover_database_configuration_files,
)
from forge.domain_intelligence.database.constraints import (
    extract_constraints,
)
from forge.domain_intelligence.database.discovery import (
    discover_migration_files,
    discover_query_files,
    discover_schema_files,
    discovery_findings,
)
from forge.domain_intelligence.database.identifiers import (
    database_project_identifier,
    database_report_identifier,
)
from forge.domain_intelligence.database.indexes import (
    extract_indexes,
)
from forge.domain_intelligence.database.models import (
    DatabaseAnalysisReport,
    DatabaseAnalysisRequest,
    DatabaseEngine,
    DatabaseProject,
    DatabaseTable,
)
from forge.domain_intelligence.database.policies import (
    DatabaseIntelligencePolicy,
    resolve_database_repository_root,
    validate_database_request,
)
from forge.domain_intelligence.database.postgres import (
    detect_postgresql,
    postgres_findings,
)
from forge.domain_intelligence.database.registry import (
    DatabaseAnalyzerRegistry,
)
from forge.domain_intelligence.database.risk import (
    database_risk_findings,
)
from forge.domain_intelligence.database.schema import (
    parse_schema_file,
)


def default_database_registry() -> DatabaseAnalyzerRegistry:
    """Return the complete M4.3 analyzer registry."""
    return DatabaseAnalyzerRegistry(
        (
            ("configuration", configuration_findings),
            ("discovery", discovery_findings),
            ("postgres", postgres_findings),
        )
    )


def _parse_database_tables(
    project_root: Path,
    schema_files: tuple[str, ...],
) -> tuple[DatabaseTable, ...]:
    tables: list[DatabaseTable] = []

    for relative in schema_files:
        path = project_root / relative

        if not path.is_file() or path.suffix.lower() != ".sql":
            continue

        sql = path.read_text(encoding="utf-8-sig")

        for table in parse_schema_file(path):
            constraints = extract_constraints(
                sql,
                schema_name=table.schema_name,
                table_name=table.name,
            )
            indexes = tuple(
                index
                for index in extract_indexes(sql)
                if index.name
            )

            tables.append(
                table.model_copy(
                    update={
                        "constraints": constraints,
                        "indexes": indexes,
                    }
                )
            )

    unique: dict[tuple[str, str], DatabaseTable] = {}

    for table in tables:
        key = (
            table.schema_name.lower(),
            table.name.lower(),
        )
        unique[key] = table

    return tuple(
        sorted(
            unique.values(),
            key=lambda table: (
                table.schema_name,
                table.name,
            ),
        )
    )


class DatabaseIntelligenceService:
    """Discover, parse, classify, and report database architecture."""

    def __init__(
        self,
        policy: DatabaseIntelligencePolicy | None = None,
        registry: DatabaseAnalyzerRegistry | None = None,
    ) -> None:
        self.policy = policy or DatabaseIntelligencePolicy()
        self.registry = registry or default_database_registry()

    def analyze(
        self,
        request: DatabaseAnalysisRequest,
    ) -> DatabaseAnalysisReport:
        """Run the complete M4.3 database-analysis pipeline."""
        validate_database_request(request, self.policy)

        repository_root = resolve_database_repository_root(
            request.repository_root,
            self.policy,
        )
        project_root = (
            repository_root / request.project_root
        ).resolve()

        try:
            project_root.relative_to(repository_root)
        except ValueError as exc:
            raise ValueError(
                "resolved database project root escaped repository"
            ) from exc

        engines = set(detect_postgresql(project_root))
        schema_files = discover_schema_files(project_root)
        migration_files = discover_migration_files(project_root)
        query_files = discover_query_files(project_root)
        configuration_files = (
            discover_database_configuration_files(project_root)
        )
        tables = _parse_database_tables(
            project_root,
            schema_files,
        )

        project_payload = {
            "root": request.project_root,
            "engines": sorted(
                engine.value for engine in engines
            ),
            "schema_files": schema_files,
            "migration_files": migration_files,
            "query_files": query_files,
            "configuration_files": configuration_files,
        }

        project = DatabaseProject(
            project_id=database_project_identifier(
                project_payload
            ),
            root=request.project_root,
            engines=tuple(
                sorted(
                    engines,
                    key=lambda engine: engine.value,
                )
            )
            or (DatabaseEngine.UNKNOWN,),
            schema_files=schema_files,
            migration_files=migration_files,
            query_files=query_files,
            configuration_files=configuration_files,
        )

        findings = (
            *self.registry.analyze(project_root),
            *database_risk_findings(tables),
        )

        return DatabaseAnalysisReport(
            report_id=database_report_identifier(
                {
                    "project_id": project.project_id,
                    "table_ids": [
                        table.table_id for table in tables
                    ],
                    "finding_ids": [
                        finding.finding_id
                        for finding in findings
                    ],
                }
            ),
            project=project,
            tables=tables,
            findings=tuple(
                sorted(
                    findings,
                    key=lambda finding: finding.finding_id,
                )
            ),
        )
'@

Write-Utf8NoBom "tests\test_domain_intelligence_database_reporting.py" @'
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
'@

Write-Utf8NoBom "tests\test_domain_intelligence_database_service.py" @'
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
'@

Write-Host ""
Write-Host "M4.3 Package 3 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_domain_intelligence_database_reporting.py `
    .\tests\test_domain_intelligence_database_service.py `
    -p no:cacheprovider
Assert-CommandSuccess "M4.3 Package 3 tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M4.3 PACKAGE 3 COMPLETE" -ForegroundColor Green

git status --short
