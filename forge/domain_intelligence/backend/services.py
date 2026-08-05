"""Backend service topology discovery for M4.2."""

from __future__ import annotations

import re
from pathlib import Path

from forge.domain_intelligence.backend.identifiers import (
    backend_finding_identifier,
)
from forge.domain_intelligence.backend.models import (
    BackendFinding,
    BackendFindingSeverity,
)

_SERVICE_NAME_PATTERN = re.compile(
    r"(?:^|[_\-.])(service|controller|router|handler|repository)(?:[_\-.]|$)",
    re.IGNORECASE,
)


def discover_service_files(
    project_root: Path,
) -> tuple[str, ...]:
    """Discover likely backend service-layer files."""
    files: set[str] = set()

    for path in project_root.rglob("*"):
        if not path.is_file():
            continue

        if path.suffix.lower() not in {
            ".js",
            ".mjs",
            ".cjs",
            ".ts",
            ".py",
        }:
            continue

        if any(
            excluded in path.parts
            for excluded in (
                ".git",
                ".venv",
                "venv",
                "node_modules",
                "__pycache__",
                "dist",
                "build",
            )
        ):
            continue

        stem = path.stem.lower()
        parent_names = {
            part.lower() for part in path.parent.parts
        }

        if (
            _SERVICE_NAME_PATTERN.search(path.name)
            or stem in {
                "app",
                "main",
                "server",
                "api",
                "routes",
                "urls",
                "views",
            }
            or parent_names.intersection(
                {
                    "services",
                    "controllers",
                    "routers",
                    "handlers",
                    "repositories",
                }
            )
        ):
            files.add(
                path.relative_to(project_root).as_posix()
            )

    return tuple(sorted(files))


def service_findings(
    project_root: Path,
) -> tuple[BackendFinding, ...]:
    """Produce a backend service-topology finding."""
    files = discover_service_files(project_root)

    if not files:
        return ()

    finding_id = backend_finding_identifier(
        {
            "category": "services",
            "files": files,
        }
    )

    return (
        BackendFinding(
            finding_id=finding_id,
            category="services",
            severity=BackendFindingSeverity.INFO,
            message="Backend service-layer files detected.",
            evidence={
                "service_file_count": str(len(files)),
                "service_files": ",".join(files),
            },
        ),
    )