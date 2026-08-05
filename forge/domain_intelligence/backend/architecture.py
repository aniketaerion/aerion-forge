"""Backend architecture classification for M4.2."""

from __future__ import annotations

from pathlib import Path

from forge.domain_intelligence.backend.configuration import (
    discover_configuration_files,
)
from forge.domain_intelligence.backend.dependencies import (
    node_dependencies,
    python_dependencies,
)
from forge.domain_intelligence.backend.identifiers import (
    backend_finding_identifier,
)
from forge.domain_intelligence.backend.models import (
    BackendFinding,
    BackendFindingSeverity,
)
from forge.domain_intelligence.backend.services import (
    discover_service_files,
)
from forge.domain_intelligence.backend.workers import (
    discover_worker_files,
)


def classify_backend_architecture(
    project_root: Path,
) -> str:
    """Classify backend layout using conservative local evidence."""
    service_files = discover_service_files(project_root)
    worker_files = discover_worker_files(project_root)
    configurations = discover_configuration_files(
        project_root
    )
    dependencies = {
        *node_dependencies(project_root),
        *python_dependencies(project_root),
    }

    has_docker = any(
        path.endswith(
            (
                "Dockerfile",
                "docker-compose.yml",
                "docker-compose.yaml",
            )
        )
        for path in configurations
    )
    has_queue = bool(
        dependencies.intersection(
            {
                "celery",
                "redis",
                "bull",
                "bullmq",
                "rq",
                "dramatiq",
            }
        )
    )

    if len(service_files) >= 4 and (worker_files or has_queue):
        return "modular-service-oriented"

    if has_docker and len(service_files) >= 2:
        return "containerized-service"

    if service_files:
        return "layered-backend"

    return "undetermined"


def architecture_findings(
    project_root: Path,
) -> tuple[BackendFinding, ...]:
    """Produce a conservative backend architecture finding."""
    classification = classify_backend_architecture(project_root)

    finding_id = backend_finding_identifier(
        {
            "category": "architecture",
            "classification": classification,
        }
    )

    severity = (
        BackendFindingSeverity.INFO
        if classification != "undetermined"
        else BackendFindingSeverity.LOW
    )

    return (
        BackendFinding(
            finding_id=finding_id,
            category="architecture",
            severity=severity,
            message=(
                "Backend architecture classification: "
                f"{classification}"
            ),
            evidence={"classification": classification},
        ),
    )