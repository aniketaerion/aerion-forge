import json
from pathlib import Path

from forge.domain_intelligence.backend.models import (
    BackendAnalysisRequest,
    BackendFramework,
    BackendRuntime,
)
from forge.domain_intelligence.backend.service import (
    BackendIntelligenceService,
    default_backend_registry,
)


def initialize_repository(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()


def test_default_backend_registry() -> None:
    assert default_backend_registry().names() == (
        "django",
        "fastapi",
        "node",
    )


def test_service_discovers_node_and_fastapi(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "dependencies": {
                    "express": "^5.0.0",
                }
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "package-lock.json").write_text(
        "{}",
        encoding="utf-8",
    )
    (tmp_path / "requirements.txt").write_text(
        "fastapi==0.116.0\n",
        encoding="utf-8",
    )

    report = BackendIntelligenceService().analyze(
        BackendAnalysisRequest(
            repository_root=str(tmp_path),
        )
    )

    assert report.project.runtimes == (
        BackendRuntime.NODEJS,
        BackendRuntime.PYTHON,
    )
    assert report.project.frameworks == (
        BackendFramework.EXPRESS,
        BackendFramework.FASTAPI,
        BackendFramework.NODE,
    )
    assert report.project.package_manager == "npm"


def test_service_reports_unknown_project(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    report = BackendIntelligenceService().analyze(
        BackendAnalysisRequest(
            repository_root=str(tmp_path),
        )
    )

    assert report.project.runtimes == (
        BackendRuntime.UNKNOWN,
    )
    assert report.project.frameworks == (
        BackendFramework.UNKNOWN,
    )
    assert not report.findings