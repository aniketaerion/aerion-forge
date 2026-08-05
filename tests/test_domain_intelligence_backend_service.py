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


def test_default_backend_registry_is_complete() -> None:
    assert default_backend_registry().names() == (
        "architecture",
        "configuration",
        "dependencies",
        "django",
        "fastapi",
        "node",
        "services",
        "workers",
    )


def test_service_runs_complete_backend_pipeline(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    source = tmp_path / "src"
    services = source / "services"
    workers = source / "workers"
    services.mkdir(parents=True)
    workers.mkdir(parents=True)

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
        "fastapi==0.116.0\nredis>=6\n",
        encoding="utf-8",
    )
    (services / "orders_service.ts").write_text(
        "export const ordersService = {}",
        encoding="utf-8",
    )
    (workers / "invoice_worker.ts").write_text(
        "export const invoiceWorker = {}",
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
    assert report.project.service_files == (
        "src/services/orders_service.ts",
    )
    assert report.project.worker_files == (
        "src/workers/invoice_worker.ts",
    )

    categories = {
        finding.category
        for finding in report.findings
    }
    assert {
        "architecture",
        "configuration",
        "dependencies",
        "framework",
        "services",
        "workers",
    }.issubset(categories)


def test_service_reports_unknown_backend(
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