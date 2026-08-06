"""Embedded analysis service for M4.6 Package 1."""

from __future__ import annotations

from forge.domain_intelligence.embedded.build_systems import (
    discover_embedded_build_files,
)
from forge.domain_intelligence.embedded.identifiers import (
    embedded_finding_identifier,
    embedded_project_identifier,
    embedded_report_identifier,
)
from forge.domain_intelligence.embedded.interfaces import (
    discover_embedded_interfaces,
)
from forge.domain_intelligence.embedded.messages import (
    discover_embedded_messages,
)
from forge.domain_intelligence.embedded.models import (
    EmbeddedAnalysisReport,
    EmbeddedAnalysisRequest,
    EmbeddedFinding,
    EmbeddedFindingSeverity,
    EmbeddedPlatformKind,
    EmbeddedProject,
)
from forge.domain_intelligence.embedded.policies import (
    EmbeddedIntelligencePolicy,
    resolve_embedded_repository_root,
    validate_embedded_request,
)
from forge.domain_intelligence.embedded.registry import (
    EmbeddedAnalyzerRegistry,
)
from forge.domain_intelligence.embedded.safety import (
    analyze_embedded_safety,
)


class EmbeddedIntelligenceService:
    """Perform deterministic, offline embedded analysis."""

    def __init__(
        self,
        *,
        policy: EmbeddedIntelligencePolicy | None = None,
        registry: EmbeddedAnalyzerRegistry | None = None,
    ) -> None:
        self._policy = policy or EmbeddedIntelligencePolicy()
        self._registry = (
            registry or EmbeddedAnalyzerRegistry.default()
        )

    def analyze(
        self,
        request: EmbeddedAnalysisRequest,
    ) -> EmbeddedAnalysisReport:
        validate_embedded_request(request, self._policy)
        repository_root = resolve_embedded_repository_root(
            request.repository_root,
            self._policy,
        )
        project_root = (
            repository_root / request.project_root
        ).resolve()

        if not project_root.is_dir():
            raise ValueError(
                f"embedded project root does not exist: {project_root}"
            )

        platforms = self._registry.detect(project_root)
        if not platforms:
            platforms = (EmbeddedPlatformKind.UNKNOWN,)

        components = self._registry.discover_components(
            project_root,
            tuple(
                platform
                for platform in platforms
                if platform is not EmbeddedPlatformKind.UNKNOWN
            ),
        )
        build_files = discover_embedded_build_files(project_root)
        interfaces = discover_embedded_interfaces(project_root)
        messages = discover_embedded_messages(project_root)
        interfaces = discover_embedded_interfaces(project_root)
        messages = discover_embedded_messages(project_root)

        relative_root = project_root.relative_to(
            repository_root
        ).as_posix()
        project_payload = {
            "root": relative_root,
            "platforms": tuple(
                platform.value for platform in platforms
            ),
            "build_files": build_files,
        }

        findings = analyze_embedded_safety(project_root)

        if platforms == (EmbeddedPlatformKind.UNKNOWN,):
            finding_payload = {
                "category": "platform",
                "path": relative_root,
                "message": "No supported embedded platform detected.",
            }
            findings = (
                *findings,
                EmbeddedFinding(
                    finding_id=embedded_finding_identifier(
                        finding_payload
                    ),
                    category="platform",
                    severity=EmbeddedFindingSeverity.INFO,
                    message=(
                        "No supported embedded platform detected."
                    ),
                    path=relative_root,
                ),
            )

        project = EmbeddedProject(
            project_id=embedded_project_identifier(
                project_payload
            ),
            root=relative_root,
            platforms=platforms,
            build_files=build_files,
        )

        report_payload = {
            "project_id": project.project_id,
            "component_ids": tuple(
                component.component_id
                for component in components
            ),
            "finding_ids": tuple(
                finding.finding_id for finding in findings
            ),
        }

        return EmbeddedAnalysisReport(
            report_id=embedded_report_identifier(
                report_payload
            ),
            project=project,
            components=components,
            interfaces=interfaces,
            messages=messages,
            findings=findings,
        )