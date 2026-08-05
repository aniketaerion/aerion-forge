"""Backend configuration discovery for M4.2."""

from __future__ import annotations

from pathlib import Path

from forge.domain_intelligence.backend.identifiers import (
    backend_finding_identifier,
)
from forge.domain_intelligence.backend.models import (
    BackendFinding,
    BackendFindingSeverity,
)

_CONFIGURATION_NAMES = (
    "package.json",
    "tsconfig.json",
    "nest-cli.json",
    "requirements.txt",
    "pyproject.toml",
    "Pipfile",
    "poetry.lock",
    "manage.py",
    "alembic.ini",
    "gunicorn.conf.py",
    "docker-compose.yml",
    "docker-compose.yaml",
    "Dockerfile",
)

_SECRET_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
}


def discover_configuration_files(
    project_root: Path,
) -> tuple[str, ...]:
    """Discover safe backend configuration file names."""
    discovered = {
        name
        for name in _CONFIGURATION_NAMES
        if (project_root / name).is_file()
    }

    for path in project_root.rglob("*"):
        if not path.is_file():
            continue

        if any(
            excluded in path.parts
            for excluded in (
                ".git",
                ".venv",
                "venv",
                "node_modules",
                "__pycache__",
            )
        ):
            continue

        if path.name in _SECRET_NAMES:
            continue

        if path.name in _CONFIGURATION_NAMES:
            discovered.add(
                path.relative_to(project_root).as_posix()
            )

    return tuple(sorted(discovered))


def configuration_findings(
    project_root: Path,
) -> tuple[BackendFinding, ...]:
    """Produce a configuration inventory finding."""
    files = discover_configuration_files(project_root)

    if not files:
        return ()

    finding_id = backend_finding_identifier(
        {
            "category": "configuration",
            "files": files,
        }
    )

    return (
        BackendFinding(
            finding_id=finding_id,
            category="configuration",
            severity=BackendFindingSeverity.INFO,
            message="Backend configuration files detected.",
            evidence={
                "file_count": str(len(files)),
                "files": ",".join(files),
            },
        ),
    )