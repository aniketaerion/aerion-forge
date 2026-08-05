"""Backend dependency analysis for M4.2."""

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
from forge.domain_intelligence.backend.node import (
    load_package_json,
    package_dependencies,
)

_REQUIREMENT_PATTERN = re.compile(
    r"^\s*([A-Za-z0-9_.-]+)"
)


def python_dependencies(
    project_root: Path,
) -> dict[str, str]:
    """Read direct Python dependencies without resolving packages."""
    dependencies: dict[str, str] = {}

    requirements = project_root / "requirements.txt"
    if requirements.is_file():
        try:
            lines = requirements.read_text(
                encoding="utf-8-sig"
            ).splitlines()
        except OSError:
            lines = []

        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            match = _REQUIREMENT_PATTERN.match(stripped)
            if match is not None:
                dependencies[match.group(1).lower()] = stripped

    pyproject = project_root / "pyproject.toml"
    if pyproject.is_file():
        try:
            content = pyproject.read_text(
                encoding="utf-8-sig"
            )
        except OSError:
            content = ""

        for name in (
            "fastapi",
            "django",
            "flask",
            "sqlalchemy",
            "celery",
            "redis",
            "uvicorn",
            "gunicorn",
        ):
            if re.search(
                rf"(?im)^[^#\r\n]*\b{re.escape(name)}\b",
                content,
            ):
                dependencies.setdefault(name, "pyproject.toml")

    return dict(sorted(dependencies.items()))


def node_dependencies(
    project_root: Path,
) -> dict[str, str]:
    """Return direct Node.js dependencies."""
    return dict(
        sorted(
            package_dependencies(
                load_package_json(project_root)
            ).items()
        )
    )


def dependency_findings(
    project_root: Path,
) -> tuple[BackendFinding, ...]:
    """Produce findings summarizing backend dependencies."""
    findings: list[BackendFinding] = []

    dependency_sets = {
        "node": node_dependencies(project_root),
        "python": python_dependencies(project_root),
    }

    for runtime, dependencies in dependency_sets.items():
        if not dependencies:
            continue

        finding_id = backend_finding_identifier(
            {
                "category": "dependencies",
                "runtime": runtime,
                "dependencies": dependencies,
            }
        )

        findings.append(
            BackendFinding(
                finding_id=finding_id,
                category="dependencies",
                severity=BackendFindingSeverity.INFO,
                message=(
                    f"{runtime} backend dependencies detected."
                ),
                evidence={
                    "runtime": runtime,
                    "dependency_count": str(len(dependencies)),
                    "dependencies": ",".join(dependencies),
                },
            )
        )

    return tuple(
        sorted(findings, key=lambda finding: finding.finding_id)
    )