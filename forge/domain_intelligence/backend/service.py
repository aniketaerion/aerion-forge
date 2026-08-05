"""Backend discovery service for M4.2."""

from __future__ import annotations

from forge.domain_intelligence.backend.django import (
    detect_django,
    django_findings,
)
from forge.domain_intelligence.backend.fastapi import (
    detect_fastapi,
    fastapi_findings,
)
from forge.domain_intelligence.backend.identifiers import (
    backend_project_identifier,
    backend_report_identifier,
)
from forge.domain_intelligence.backend.models import (
    BackendAnalysisReport,
    BackendAnalysisRequest,
    BackendFramework,
    BackendProject,
    BackendRuntime,
)
from forge.domain_intelligence.backend.node import (
    detect_node_frameworks,
    detect_node_runtime,
    load_package_json,
    node_findings,
)
from forge.domain_intelligence.backend.policies import (
    BackendIntelligencePolicy,
    resolve_backend_repository_root,
    validate_backend_request,
)
from forge.domain_intelligence.backend.registry import (
    BackendAnalyzerRegistry,
)


def default_backend_registry() -> BackendAnalyzerRegistry:
    """Return the M4.2 Package 1 analyzer registry."""
    return BackendAnalyzerRegistry(
        (
            ("django", django_findings),
            ("fastapi", fastapi_findings),
            ("node", node_findings),
        )
    )


class BackendIntelligenceService:
    """Discover backend runtime and framework metadata safely."""

    def __init__(
        self,
        policy: BackendIntelligencePolicy | None = None,
        registry: BackendAnalyzerRegistry | None = None,
    ) -> None:
        self.policy = policy or BackendIntelligencePolicy()
        self.registry = registry or default_backend_registry()

    def analyze(
        self,
        request: BackendAnalysisRequest,
    ) -> BackendAnalysisReport:
        """Run backend framework discovery."""
        validate_backend_request(request, self.policy)

        repository_root = resolve_backend_repository_root(
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
                "resolved backend project root escaped repository"
            ) from exc

        runtimes: set[BackendRuntime] = set(
            detect_node_runtime(project_root)
        )
        frameworks: set[BackendFramework] = set(
            detect_node_frameworks(project_root)
        )

        if detect_fastapi(project_root):
            runtimes.add(BackendRuntime.PYTHON)
            frameworks.add(BackendFramework.FASTAPI)

        if detect_django(project_root):
            runtimes.add(BackendRuntime.PYTHON)
            frameworks.add(BackendFramework.DJANGO)

        package_manager: str | None = None

        if (project_root / "pnpm-lock.yaml").is_file():
            package_manager = "pnpm"
        elif (project_root / "yarn.lock").is_file():
            package_manager = "yarn"
        elif (project_root / "package-lock.json").is_file():
            package_manager = "npm"
        elif (project_root / "poetry.lock").is_file():
            package_manager = "poetry"
        elif (project_root / "Pipfile").is_file():
            package_manager = "pipenv"
        elif (project_root / "requirements.txt").is_file():
            package_manager = "pip"

        package_json = load_package_json(project_root)

        if (
            package_manager is None
            and isinstance(
                package_json.get("packageManager"),
                str,
            )
        ):
            value = str(package_json["packageManager"])
            package_manager = value.split("@", maxsplit=1)[0]

        configuration_names = (
            "package.json",
            "package-lock.json",
            "pnpm-lock.yaml",
            "yarn.lock",
            "requirements.txt",
            "pyproject.toml",
            "Pipfile",
            "poetry.lock",
            "manage.py",
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
                "apps",
                "server",
                "api",
                "backend",
            )
            if (project_root / name).is_dir()
        )

        findings = self.registry.analyze(project_root)

        project_payload = {
            "root": request.project_root,
            "runtimes": sorted(
                runtime.value for runtime in runtimes
            ),
            "frameworks": sorted(
                framework.value for framework in frameworks
            ),
            "package_manager": package_manager,
        }

        project = BackendProject(
            project_id=backend_project_identifier(
                project_payload
            ),
            root=request.project_root,
            runtimes=tuple(
                sorted(
                    runtimes,
                    key=lambda runtime: runtime.value,
                )
            )
            or (BackendRuntime.UNKNOWN,),
            frameworks=tuple(
                sorted(
                    frameworks,
                    key=lambda framework: framework.value,
                )
            )
            or (BackendFramework.UNKNOWN,),
            package_manager=package_manager,
            source_directories=source_directories,
            configuration_files=configuration_files,
        )

        return BackendAnalysisReport(
            report_id=backend_report_identifier(
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