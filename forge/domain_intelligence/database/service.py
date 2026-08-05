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