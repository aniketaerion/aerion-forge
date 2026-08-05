"""Frontend project analysis service for M4.1."""

from __future__ import annotations

from pathlib import Path

from forge.domain_intelligence.frontend.components import (
    component_findings,
)
from forge.domain_intelligence.frontend.hooks import (
    hook_findings,
)
from forge.domain_intelligence.frontend.nextjs import (
    detect_nextjs,
    nextjs_findings,
)
from forge.domain_intelligence.frontend.react import (
    detect_react,
    load_package_json,
    react_findings,
)
from forge.domain_intelligence.frontend.registry import (
    FrontendAnalyzerRegistry,
)
from forge.domain_intelligence.frontend.routing import (
    route_findings,
)
from forge.domain_intelligence.frontend.state_management import (
    state_management_findings,
)
from forge.domain_intelligence.frontend.styling import (
    styling_findings,
)
from forge.domain_intelligence.frontend.vite import (
    detect_vite,
    vite_findings,
)
from forge.domain_intelligence.identifiers import (
    frontend_project_identifier,
    frontend_report_identifier,
)
from forge.domain_intelligence.models import (
    FrontendAnalysisReport,
    FrontendAnalysisRequest,
    FrontendFramework,
    FrontendProject,
)
from forge.domain_intelligence.policies import (
    DomainIntelligencePolicy,
    resolve_repository_root,
    validate_frontend_request,
)


def default_frontend_registry() -> FrontendAnalyzerRegistry:
    """Return the complete M4.1 analyzer registry."""
    return FrontendAnalyzerRegistry(
        (
            ("components", component_findings),
            ("hooks", hook_findings),
            ("nextjs", nextjs_findings),
            ("react", react_findings),
            ("routing", route_findings),
            (
                "state-management",
                state_management_findings,
            ),
            ("styling", styling_findings),
            ("vite", vite_findings),
        )
    )


class FrontendIntelligenceService:
    """Discover, classify, analyze, and report frontend projects."""

    def __init__(
        self,
        policy: DomainIntelligencePolicy | None = None,
        registry: FrontendAnalyzerRegistry | None = None,
    ) -> None:
        self.policy = policy or DomainIntelligencePolicy()
        self.registry = registry or default_frontend_registry()

    def resolve_project_root(
        self,
        request: FrontendAnalysisRequest,
    ) -> tuple[Path, Path]:
        """Resolve repository and project roots safely."""
        validate_frontend_request(request, self.policy)

        repository_root = resolve_repository_root(
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
                "resolved frontend project root escaped repository"
            ) from exc

        return repository_root, project_root

    def analyze(
        self,
        request: FrontendAnalysisRequest,
    ) -> FrontendAnalysisReport:
        """Run the complete M4.1 frontend-analysis pipeline."""
        _, project_root = self.resolve_project_root(request)

        package_json = load_package_json(project_root)
        frameworks = {
            *detect_react(project_root),
            *detect_vite(project_root),
            *detect_nextjs(project_root),
        }

        package_manager: str | None = None

        if (project_root / "pnpm-lock.yaml").is_file():
            package_manager = "pnpm"
        elif (project_root / "yarn.lock").is_file():
            package_manager = "yarn"
        elif (project_root / "package-lock.json").is_file():
            package_manager = "npm"
        elif "packageManager" in package_json:
            value = package_json["packageManager"]
            if isinstance(value, str):
                package_manager = value.split("@", maxsplit=1)[0]

        configuration_names = (
            "package.json",
            "vite.config.js",
            "vite.config.ts",
            "next.config.js",
            "next.config.mjs",
            "next.config.ts",
            "tsconfig.json",
            "jsconfig.json",
            "tailwind.config.js",
            "tailwind.config.ts",
        )
        configuration_files = tuple(
            name
            for name in configuration_names
            if (project_root / name).is_file()
        )

        source_directories = tuple(
            name
            for name in (
                "src",
                "app",
                "pages",
                "components",
            )
            if (project_root / name).is_dir()
        )

        findings = self.registry.analyze(project_root)

        route_files = tuple(
            sorted(
                {
                    finding.path
                    for finding in findings
                    if finding.category == "routing"
                    and finding.path is not None
                }
            )
        )

        component_files = tuple(
            sorted(
                {
                    finding.path
                    for finding in findings
                    if finding.category == "component"
                    and finding.path is not None
                }
            )
        )

        project_payload = {
            "root": request.project_root,
            "frameworks": sorted(
                framework.value for framework in frameworks
            ),
            "package_manager": package_manager,
            "source_directories": source_directories,
            "configuration_files": configuration_files,
            "route_files": route_files,
            "component_files": component_files,
        }

        project = FrontendProject(
            project_id=frontend_project_identifier(project_payload),
            root=request.project_root,
            frameworks=tuple(
                sorted(
                    frameworks,
                    key=lambda framework: framework.value,
                )
            )
            or (FrontendFramework.UNKNOWN,),
            package_manager=package_manager,
            source_directories=source_directories,
            route_files=route_files,
            component_files=component_files,
            configuration_files=configuration_files,
        )

        return FrontendAnalysisReport(
            report_id=frontend_report_identifier(
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