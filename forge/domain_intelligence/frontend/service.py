"""Frontend project discovery service for M4.1."""

from __future__ import annotations

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
    return FrontendAnalyzerRegistry(
        (
            ("nextjs", nextjs_findings),
            ("react", react_findings),
            ("vite", vite_findings),
        )
    )


class FrontendIntelligenceService:
    """Discover and classify frontend projects safely."""

    def __init__(
        self,
        policy: DomainIntelligencePolicy | None = None,
        registry: FrontendAnalyzerRegistry | None = None,
    ) -> None:
        self.policy = policy or DomainIntelligencePolicy()
        self.registry = registry or default_frontend_registry()

    def analyze(
        self,
        request: FrontendAnalysisRequest,
    ) -> FrontendAnalysisReport:
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
        )
        configuration_files = tuple(
            name
            for name in configuration_names
            if (project_root / name).is_file()
        )

        source_directories = tuple(
            name
            for name in ("src", "app", "pages", "components")
            if (project_root / name).is_dir()
        )

        project_payload = {
            "root": request.project_root,
            "frameworks": sorted(
                framework.value for framework in frameworks
            ),
            "package_manager": package_manager,
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
            configuration_files=configuration_files,
        )

        findings = self.registry.analyze(project_root)

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