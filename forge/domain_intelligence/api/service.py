"""Complete API analysis service for M4.4."""

from __future__ import annotations

from forge.domain_intelligence.api.compatibility import (
    compatibility_findings,
)
from forge.domain_intelligence.api.contracts import (
    discover_api_contracts,
)
from forge.domain_intelligence.api.dependencies import (
    dependency_findings,
    discover_api_dependencies,
)
from forge.domain_intelligence.api.discovery import (
    discover_api_source_files,
    discovery_findings,
)
from forge.domain_intelligence.api.graphql import (
    discover_graphql_files,
    graphql_findings,
)
from forge.domain_intelligence.api.identifiers import (
    api_project_identifier,
    api_report_identifier,
)
from forge.domain_intelligence.api.models import (
    ApiAnalysisReport,
    ApiAnalysisRequest,
    ApiProject,
    ApiStyle,
)
from forge.domain_intelligence.api.openapi import (
    discover_openapi_files,
    openapi_findings,
)
from forge.domain_intelligence.api.policies import (
    ApiIntelligencePolicy,
    resolve_api_repository_root,
    validate_api_request,
)
from forge.domain_intelligence.api.registry import (
    ApiAnalyzerRegistry,
)
from forge.domain_intelligence.api.rest import (
    rest_findings,
)
from forge.domain_intelligence.api.security import (
    security_findings,
)
from forge.domain_intelligence.api.versioning import (
    versioning_findings,
)


def default_api_registry() -> ApiAnalyzerRegistry:
    """Return the complete M4.4 analyzer registry."""
    return ApiAnalyzerRegistry(
        (
            ("dependencies", dependency_findings),
            ("discovery", discovery_findings),
            ("graphql", graphql_findings),
            ("openapi", openapi_findings),
            ("rest", rest_findings),
        )
    )


class ApiIntelligenceService:
    """Discover, analyze, and report API architecture."""

    def __init__(
        self,
        policy: ApiIntelligencePolicy | None = None,
        registry: ApiAnalyzerRegistry | None = None,
    ) -> None:
        self.policy = policy or ApiIntelligencePolicy()
        self.registry = registry or default_api_registry()

    def analyze(
        self,
        request: ApiAnalysisRequest,
    ) -> ApiAnalysisReport:
        """Run the complete M4.4 API-analysis pipeline."""
        validate_api_request(request, self.policy)

        repository_root = resolve_api_repository_root(
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
                "resolved API project root escaped repository"
            ) from exc

        contracts = discover_api_contracts(project_root)
        styles = {
            contract.style for contract in contracts
        }
        contract_files = discover_openapi_files(project_root)
        source_files = discover_api_source_files(project_root)
        graphql_files = discover_graphql_files(project_root)
        dependencies = discover_api_dependencies(project_root)

        configuration_files = tuple(
            sorted(
                {
                    *contract_files,
                    *(
                        ("package.json",)
                        if (project_root / "package.json").is_file()
                        else ()
                    ),
                    *(
                        ("requirements.txt",)
                        if (
                            project_root
                            / "requirements.txt"
                        ).is_file()
                        else ()
                    ),
                }
            )
        )

        project_payload = {
            "root": request.project_root,
            "styles": sorted(style.value for style in styles),
            "contract_files": contract_files,
            "source_files": source_files,
            "graphql_files": graphql_files,
            "dependencies": dependencies,
            "configuration_files": configuration_files,
        }

        project = ApiProject(
            project_id=api_project_identifier(project_payload),
            root=request.project_root,
            styles=tuple(
                sorted(
                    styles,
                    key=lambda style: style.value,
                )
            )
            or (ApiStyle.UNKNOWN,),
            contract_files=contract_files,
            source_files=source_files,
            configuration_files=configuration_files,
        )

        findings = (
            *self.registry.analyze(project_root),
            *versioning_findings(contracts),
            *compatibility_findings(contracts),
            *security_findings(contracts),
        )

        return ApiAnalysisReport(
            report_id=api_report_identifier(
                {
                    "project_id": project.project_id,
                    "contract_ids": [
                        contract.contract_id
                        for contract in contracts
                    ],
                    "finding_ids": [
                        finding.finding_id
                        for finding in findings
                    ],
                }
            ),
            project=project,
            contracts=contracts,
            findings=tuple(
                sorted(
                    findings,
                    key=lambda finding: finding.finding_id,
                )
            ),
        )