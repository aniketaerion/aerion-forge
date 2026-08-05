"""API artifact discovery for M4.4."""

from __future__ import annotations

from pathlib import Path

from forge.domain_intelligence.api.identifiers import (
    api_finding_identifier,
)
from forge.domain_intelligence.api.models import (
    ApiFinding,
    ApiFindingSeverity,
)


def discover_api_source_files(
    project_root: Path,
) -> tuple[str, ...]:
    """Discover likely API source files."""
    files: set[str] = set()

    for path in project_root.rglob("*"):
        if not path.is_file():
            continue

        if path.suffix.lower() not in {
            ".py",
            ".ts",
            ".js",
            ".graphql",
            ".gql",
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

        relative = path.relative_to(project_root).as_posix()
        lowered = relative.lower()

        if any(
            token in lowered
            for token in (
                "api",
                "route",
                "router",
                "controller",
                "endpoint",
                "graphql",
                "schema",
            )
        ):
            files.add(relative)

    return tuple(sorted(files))


def discovery_findings(
    project_root: Path,
) -> tuple[ApiFinding, ...]:
    """Produce API source discovery findings."""
    files = discover_api_source_files(project_root)

    if not files:
        return ()

    finding_id = api_finding_identifier(
        {
            "category": "source",
            "files": files,
        }
    )

    return (
        ApiFinding(
            finding_id=finding_id,
            category="source",
            severity=ApiFindingSeverity.INFO,
            message="API source files detected.",
            evidence={
                "file_count": str(len(files)),
                "files": ",".join(files),
            },
        ),
    )