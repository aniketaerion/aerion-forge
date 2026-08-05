"""API discovery service for M4.4 Package 1."""

from __future__ import annotations

from forge.domain_intelligence.api.discovery import (
    discover_api_source_files,
    discovery_findings,
)
from forge.domain_intelligence.api.identifiers import (
    api_contract_identifier,
    api_project_identifier,
    api_report_identifier,
)
from forge.domain_intelligence.api.models import (
    ApiAnalysisReport,
    ApiAnalysisRequest,
    ApiContract,
    ApiProject,
    ApiStyle,
)
from forge.domain_intelligence.api.openapi import (
    discover_openapi_files,
    openapi_findings,
    parse_openapi_file,
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
    discover_rest_endpoints,
    rest_findings,
)


def default_api_registry() -> ApiAnalyzerRegistry:
    """Return the M4.4 Package 1 analyzer registry."""
    return ApiAnalyzerRegistry(
        (
            ("discovery", discovery_findings),
            ("openapi", openapi_findings),
            ("rest", rest_findings),
        )
    )


class ApiIntelligenceService:
    """Discover API contracts and source endpoints safely."""

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
        """Run REST and OpenAPI discovery without network calls."""
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

        contracts = [
            parse_openapi_file(project_root, relative_path)
            for relative_path in discover_openapi_files(
                project_root
            )
        ]

        rest_endpoints = discover_rest_endpoints(project_root)

        if rest_endpoints:
            contracts.append(
                ApiContract(
                    contract_id=api_contract_identifier(
                        {
                            "title": "Discovered REST API",
                            "source_path": "source",
                            "endpoint_ids": [
                                endpoint.endpoint_id
                                for endpoint in rest_endpoints
                            ],
                        }
                    ),
                    title="Discovered REST API",
                    style=ApiStyle.REST,
                    source_path="source",
                    endpoints=rest_endpoints,
                )
            )

        styles = {
            contract.style for contract in contracts
        }

        project_payload = {
            "root": request.project_root,
            "styles": sorted(style.value for style in styles),
            "contract_files": discover_openapi_files(
                project_root
            ),
            "source_files": discover_api_source_files(
                project_root
            ),
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
            contract_files=tuple(
                project_payload["contract_files"]
            ),
            source_files=tuple(
                project_payload["source_files"]
            ),
        )

        findings = self.registry.analyze(project_root)

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
            contracts=tuple(
                sorted(
                    contracts,
                    key=lambda contract: (
                        contract.style.value,
                        contract.source_path,
                    ),
                )
            ),
            findings=findings,
        )