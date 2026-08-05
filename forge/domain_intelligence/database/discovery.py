"""Database artifact discovery for M4.3."""

from __future__ import annotations

from pathlib import Path

from forge.domain_intelligence.database.identifiers import (
    database_finding_identifier,
)
from forge.domain_intelligence.database.models import (
    DatabaseFinding,
    DatabaseFindingSeverity,
)


def discover_schema_files(
    project_root: Path,
) -> tuple[str, ...]:
    """Discover schema-definition files."""
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

        relative = path.relative_to(project_root).as_posix().lower()

        if (
            path.suffix.lower() == ".sql"
            and any(
                token in relative
                for token in (
                    "schema",
                    "ddl",
                    "init",
                    "bootstrap",
                )
            )
        ) or relative.endswith("schema.prisma"):
            files.add(path.relative_to(project_root).as_posix())

    return tuple(sorted(files))


def discover_migration_files(
    project_root: Path,
) -> tuple[str, ...]:
    """Discover migration artifacts."""
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

        relative = path.relative_to(project_root).as_posix()
        lowered = relative.lower()

        if (
            lowered.startswith("migrations/")
            or lowered.startswith("migration/")
            or "/migrations/" in lowered
            or "/migration/" in lowered
            or "alembic/versions/" in lowered
            or "prisma/migrations/" in lowered
        ):
            files.add(relative)

    return tuple(sorted(files))


def discover_query_files(
    project_root: Path,
) -> tuple[str, ...]:
    """Discover SQL and query-bearing application files."""
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

        if path.suffix.lower() == ".sql":
            files.add(path.relative_to(project_root).as_posix())
            continue

        if path.suffix.lower() in {".py", ".ts", ".js"}:
            try:
                content = path.read_text(encoding="utf-8-sig")
            except OSError:
                continue

            lowered = content.lower()
            if any(
                keyword in lowered
                for keyword in (
                    "select ",
                    "insert into ",
                    "update ",
                    "delete from ",
                )
            ):
                files.add(path.relative_to(project_root).as_posix())

    return tuple(sorted(files))


def discovery_findings(
    project_root: Path,
) -> tuple[DatabaseFinding, ...]:
    """Produce findings for discovered database artifacts."""
    artifact_sets = {
        "schema_files": discover_schema_files(project_root),
        "migration_files": discover_migration_files(project_root),
        "query_files": discover_query_files(project_root),
    }

    findings: list[DatabaseFinding] = []

    for category, files in artifact_sets.items():
        if not files:
            continue

        finding_id = database_finding_identifier(
            {
                "category": category,
                "files": files,
            }
        )

        findings.append(
            DatabaseFinding(
                finding_id=finding_id,
                category=category,
                severity=DatabaseFindingSeverity.INFO,
                message=f"Database {category.replace('_', ' ')} detected.",
                evidence={
                    "file_count": str(len(files)),
                    "files": ",".join(files),
                },
            )
        )

    return tuple(
        sorted(findings, key=lambda finding: finding.finding_id)
    )