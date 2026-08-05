"""Complete backend analysis service for M4.2."""

from __future__ import annotations

from forge.domain_intelligence.backend.architecture import (
    architecture_findings,
)
from forge.domain_intelligence.backend.configuration import (
    configuration_findings,
    discover_configuration_files,
)
from forge.domain_intelligence.backend.dependencies import (
    dependency_findings,
)
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
from forge.domain_intelligence.backend.services import (
    discover_service_files,
    service_findings,
)
from forge.domain_intelligence.backend.workers import (
    discover_worker_files,
    worker_findings,
)


def default_backend_registry() -> BackendAnalyzerRegistry:
    """Return the complete M4.2 backend analyzer registry."""
    return BackendAnalyzerRegistry(
        (
            ("architecture", architecture_findings),
            ("configuration", configuration_findings),
            ("dependencies", dependency_findings),
            ("django", django_findings),
            ("fastapi", fastapi_findings),
            ("node", node_findings),
            ("services", service_findings),
            ("workers", worker_findings),
        )
    )


class BackendIntelligenceService:
    """Discover, classify, and report backend architecture."""

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
        """Run the complete M4.2 backend-analysis pipeline."""
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

        configuration_files = discover_configuration_files(
            project_root
        )
        service_files = discover_service_files(project_root)
        worker_files = discover_worker_files(project_root)
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
            "configuration_files": configuration_files,
            "service_files": service_files,
            "worker_files": worker_files,
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
            service_files=service_files,
            worker_files=worker_files,
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