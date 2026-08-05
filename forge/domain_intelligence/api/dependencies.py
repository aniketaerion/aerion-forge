"""API dependency analysis for M4.4."""

from __future__ import annotations

import json
from pathlib import Path

from forge.domain_intelligence.api.identifiers import (
    api_finding_identifier,
)
from forge.domain_intelligence.api.models import (
    ApiFinding,
    ApiFindingSeverity,
)

_API_DEPENDENCIES = {
    "apollo-server",
    "@apollo/server",
    "express",
    "fastapi",
    "flask",
    "graphene",
    "graphql",
    "nestjs",
    "strawberry-graphql",
}


def discover_api_dependencies(
    project_root: Path,
) -> tuple[str, ...]:
    """Discover known API framework dependencies."""
    dependencies: set[str] = set()

    package_json = project_root / "package.json"

    if package_json.is_file():
        try:
            document = json.loads(
                package_json.read_text(encoding="utf-8-sig")
            )
        except (OSError, json.JSONDecodeError):
            document = {}

        for section_name in (
            "dependencies",
            "devDependencies",
            "peerDependencies",
        ):
            section = document.get(section_name)

            if not isinstance(section, dict):
                continue

            dependencies.update(
                name
                for name in section
                if name in _API_DEPENDENCIES
            )

    for requirements_name in (
        "requirements.txt",
        "requirements-dev.txt",
    ):
        path = project_root / requirements_name

        if not path.is_file():
            continue

        try:
            lines = path.read_text(
                encoding="utf-8-sig"
            ).splitlines()
        except OSError:
            continue

        for line in lines:
            normalized = (
                line.split("==", maxsplit=1)[0]
                .split(">=", maxsplit=1)[0]
                .strip()
                .lower()
            )

            if normalized in _API_DEPENDENCIES:
                dependencies.add(normalized)

    return tuple(sorted(dependencies))


def dependency_findings(
    project_root: Path,
) -> tuple[ApiFinding, ...]:
    """Produce API dependency findings."""
    dependencies = discover_api_dependencies(project_root)

    if not dependencies:
        return ()

    finding_id = api_finding_identifier(
        {
            "category": "dependencies",
            "dependencies": dependencies,
        }
    )

    return (
        ApiFinding(
            finding_id=finding_id,
            category="dependencies",
            severity=ApiFindingSeverity.INFO,
            message="API framework dependencies detected.",
            evidence={
                "dependency_count": str(len(dependencies)),
                "dependencies": ",".join(dependencies),
            },
        ),
    )