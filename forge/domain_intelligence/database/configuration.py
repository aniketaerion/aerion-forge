"""Database configuration discovery for M4.3."""

from __future__ import annotations

from pathlib import Path

from forge.domain_intelligence.database.identifiers import (
    database_finding_identifier,
)
from forge.domain_intelligence.database.models import (
    DatabaseFinding,
    DatabaseFindingSeverity,
)

_CONFIGURATION_NAMES = (
    "postgresql.conf",
    "pg_hba.conf",
    "pg_ident.conf",
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yml",
    "compose.yaml",
    "prisma/schema.prisma",
    "alembic.ini",
    "knexfile.js",
    "knexfile.ts",
    "ormconfig.json",
    "drizzle.config.ts",
)

_SECRET_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
}


def discover_database_configuration_files(
    project_root: Path,
) -> tuple[str, ...]:
    """Discover safe database configuration artifacts."""
    files: set[str] = set()

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
                "dist",
                "build",
            )
        ):
            continue

        if path.name in _SECRET_NAMES:
            continue

        relative = path.relative_to(project_root).as_posix()

        if relative in _CONFIGURATION_NAMES or path.name in {
            Path(name).name for name in _CONFIGURATION_NAMES
        }:
            files.add(relative)

    return tuple(sorted(files))


def configuration_findings(
    project_root: Path,
) -> tuple[DatabaseFinding, ...]:
    """Produce a database configuration inventory finding."""
    files = discover_database_configuration_files(project_root)

    if not files:
        return ()

    finding_id = database_finding_identifier(
        {
            "category": "configuration",
            "files": files,
        }
    )

    return (
        DatabaseFinding(
            finding_id=finding_id,
            category="configuration",
            severity=DatabaseFindingSeverity.INFO,
            message="Database configuration files detected.",
            evidence={
                "file_count": str(len(files)),
                "files": ",".join(files),
            },
        ),
    )