"""Database discovery service for M4.3 Package 1."""

from __future__ import annotations

from forge.domain_intelligence.database.configuration import (
    configuration_findings,
    discover_database_configuration_files,
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
from forge.domain_intelligence.database.models import (
    DatabaseAnalysisReport,
    DatabaseAnalysisRequest,
    DatabaseEngine,
    DatabaseProject,
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


def default_database_registry() -> DatabaseAnalyzerRegistry:
    """Return the M4.3 Package 1 analyzer registry."""
    return DatabaseAnalyzerRegistry(
        (
            ("configuration", configuration_findings),
            ("discovery", discovery_findings),
            ("postgres", postgres_findings),
        )
    )


class DatabaseIntelligenceService:
    """Discover database engines and repository artifacts safely."""

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
        """Run database discovery without live connections."""
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

        project_payload = {
            "root": request.project_root,
            "engines": sorted(engine.value for engine in engines),
            "schema_files": discover_schema_files(project_root),
            "migration_files": discover_migration_files(project_root),
            "query_files": discover_query_files(project_root),
            "configuration_files": (
                discover_database_configuration_files(project_root)
            ),
        }

        project = DatabaseProject(
            project_id=database_project_identifier(project_payload),
            root=request.project_root,
            engines=tuple(
                sorted(
                    engines,
                    key=lambda engine: engine.value,
                )
            )
            or (DatabaseEngine.UNKNOWN,),
            schema_files=tuple(project_payload["schema_files"]),
            migration_files=tuple(project_payload["migration_files"]),
            query_files=tuple(project_payload["query_files"]),
            configuration_files=tuple(project_payload["configuration_files"]),
        )

        findings = self.registry.analyze(project_root)

        return DatabaseAnalysisReport(
            report_id=database_report_identifier(
                {
                    "project_id": project.project_id,
                    "finding_ids": [
                        finding.finding_id
                        for finding in findings
                    ],
                }
            ),
            project=project,
            findings=findings,
        )