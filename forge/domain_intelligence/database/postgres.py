"""PostgreSQL discovery for M4.3 Database Domain Intelligence."""

from __future__ import annotations

import re
from pathlib import Path

from forge.domain_intelligence.database.identifiers import (
    database_finding_identifier,
)
from forge.domain_intelligence.database.models import (
    DatabaseEngine,
    DatabaseFinding,
    DatabaseFindingSeverity,
)

_POSTGRES_PATTERNS = (
    re.compile(r"\bpostgres(?:ql)?://", re.IGNORECASE),
    re.compile(r"\bpostgres(?:ql)?\b", re.IGNORECASE),
    re.compile(r"\bpsycopg(?:2)?\b", re.IGNORECASE),
    re.compile(r"\basyncpg\b", re.IGNORECASE),
)


def detect_postgresql(
    project_root: Path,
) -> tuple[DatabaseEngine, ...]:
    """Detect PostgreSQL through local configuration and dependency evidence."""
    conventional_files = (
        "postgresql.conf",
        "pg_hba.conf",
        "pg_ident.conf",
    )

    if any((project_root / name).is_file() for name in conventional_files):
        return (DatabaseEngine.POSTGRESQL,)

    candidates = (
        "requirements.txt",
        "pyproject.toml",
        "Pipfile",
        "poetry.lock",
        "package.json",
        "docker-compose.yml",
        "docker-compose.yaml",
        "compose.yml",
        "compose.yaml",
        "prisma/schema.prisma",
    )

    for name in candidates:
        path = project_root / name
        if not path.is_file():
            continue

        try:
            content = path.read_text(encoding="utf-8-sig")
        except OSError:
            continue

        if any(pattern.search(content) for pattern in _POSTGRES_PATTERNS):
            return (DatabaseEngine.POSTGRESQL,)

    for path in project_root.rglob("*"):
        if not path.is_file():
            continue

        if path.suffix.lower() not in {
            ".sql",
            ".py",
            ".ts",
            ".js",
            ".json",
            ".yaml",
            ".yml",
            ".toml",
            ".prisma",
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

        try:
            content = path.read_text(encoding="utf-8-sig")
        except OSError:
            continue

        if any(pattern.search(content) for pattern in _POSTGRES_PATTERNS):
            return (DatabaseEngine.POSTGRESQL,)

    return ()


def postgres_findings(
    project_root: Path,
) -> tuple[DatabaseFinding, ...]:
    """Produce deterministic PostgreSQL discovery findings."""
    if not detect_postgresql(project_root):
        return ()

    finding_id = database_finding_identifier(
        {
            "category": "engine",
            "engine": DatabaseEngine.POSTGRESQL.value,
            "root": project_root.as_posix(),
        }
    )

    return (
        DatabaseFinding(
            finding_id=finding_id,
            category="engine",
            severity=DatabaseFindingSeverity.INFO,
            message="Database engine detected: postgresql",
            evidence={"engine": DatabaseEngine.POSTGRESQL.value},
        ),
    )