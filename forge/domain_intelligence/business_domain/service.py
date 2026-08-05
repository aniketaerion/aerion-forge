"""Business-domain analysis service for M4.5 Package 1."""

from __future__ import annotations

from forge.domain_intelligence.business_domain.crm import (
    crm_findings,
)
from forge.domain_intelligence.business_domain.erp import (
    erp_findings,
)
from forge.domain_intelligence.business_domain.identifiers import (
    business_domain_project_identifier,
    business_report_identifier,
)
from forge.domain_intelligence.business_domain.manifest import (
    business_domain_manifest,
)
from forge.domain_intelligence.business_domain.models import (
    BusinessDomainAnalysisReport,
    BusinessDomainAnalysisRequest,
    BusinessDomainProject,
)
from forge.domain_intelligence.business_domain.policies import (
    BusinessDomainIntelligencePolicy,
    resolve_business_domain_repository_root,
    validate_business_domain_request,
)
from forge.domain_intelligence.business_domain.registry import (
    BusinessDomainAnalyzerRegistry,
)


def default_business_domain_registry() -> (
    BusinessDomainAnalyzerRegistry
):
    """Return the M4.5 Package 1 analyzer registry."""
    return BusinessDomainAnalyzerRegistry(
        (
            ("crm", crm_findings),
            ("erp", erp_findings),
        )
    )


class BusinessDomainIntelligenceService:
    """Discover business domains, modules, and entities safely."""

    def __init__(
        self,
        policy: BusinessDomainIntelligencePolicy | None = None,
        registry: BusinessDomainAnalyzerRegistry | None = None,
    ) -> None:
        self.policy = (
            policy or BusinessDomainIntelligencePolicy()
        )
        self.registry = (
            registry or default_business_domain_registry()
        )

    def analyze(
        self,
        request: BusinessDomainAnalysisRequest,
    ) -> BusinessDomainAnalysisReport:
        validate_business_domain_request(
            request,
            self.policy,
        )

        repository_root = (
            resolve_business_domain_repository_root(
                request.repository_root,
                self.policy,
            )
        )
        project_root = (
            repository_root / request.project_root
        ).resolve()

        try:
            project_root.relative_to(repository_root)
        except ValueError as exc:
            raise ValueError(
                "resolved business-domain project root "
                "escaped repository"
            ) from exc

        manifest = business_domain_manifest(project_root)
        domains = manifest["domains"]
        modules = manifest["modules"]
        entities = manifest["entities"]

        source_files = tuple(
            sorted(
                {
                    source_path
                    for entity in entities
                    for source_path in entity.source_paths
                }
            )
        )

        project_payload = {
            "root": request.project_root,
            "domains": [
                domain.value for domain in domains
            ],
            "modules": modules,
            "source_files": source_files,
        }

        project = BusinessDomainProject(
            project_id=business_domain_project_identifier(
                project_payload
            ),
            root=request.project_root,
            domains=domains,
            modules=modules,
            source_files=source_files,
        )

        findings = self.registry.analyze(project_root)

        return BusinessDomainAnalysisReport(
            report_id=business_report_identifier(
                {
                    "project_id": project.project_id,
                    "entity_ids": [
                        entity.entity_id
                        for entity in entities
                    ],
                    "finding_ids": [
                        finding.finding_id
                        for finding in findings
                    ],
                }
            ),
            project=project,
            entities=entities,
            findings=findings,
        )