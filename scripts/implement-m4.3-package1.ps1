[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Content
    )

    $FullPath = Join-Path $RepositoryRoot $Path
    $Directory = Split-Path $FullPath -Parent
    New-Item -ItemType Directory -Path $Directory -Force | Out-Null

    [System.IO.File]::WriteAllText(
        $FullPath,
        $Content,
        [System.Text.UTF8Encoding]::new($false)
    )

    Write-Host "WROTE $Path" -ForegroundColor Green
}

function Assert-CommandSuccess {
    param([Parameter(Mandatory)][string]$Name)

    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

Write-Utf8NoBom "forge\domain_intelligence\database\postgres.py" @'
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
'@

Write-Utf8NoBom "forge\domain_intelligence\database\configuration.py" @'
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
'@

Write-Utf8NoBom "forge\domain_intelligence\database\discovery.py" @'
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

        relative = path.relative_to(project_root).as_posix().lower()

        if any(
            token in relative
            for token in (
                "/migrations/",
                "/migration/",
                "alembic/versions/",
                "prisma/migrations/",
            )
        ):
            files.add(path.relative_to(project_root).as_posix())

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
'@

Write-Utf8NoBom "forge\domain_intelligence\database\registry.py" @'
"""Analyzer registry for M4.3 Database Domain Intelligence."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path

from forge.domain_intelligence.database.errors import (
    DatabaseConfigurationError,
)
from forge.domain_intelligence.database.models import DatabaseFinding

DatabaseAnalyzer = Callable[[Path], tuple[DatabaseFinding, ...]]


class DatabaseAnalyzerRegistry:
    """Deterministic registry of named database analyzers."""

    def __init__(
        self,
        analyzers: Iterable[
            tuple[str, DatabaseAnalyzer]
        ] = (),
    ) -> None:
        self._analyzers: dict[str, DatabaseAnalyzer] = {}

        for name, analyzer in analyzers:
            self.register(name, analyzer)

    def register(
        self,
        name: str,
        analyzer: DatabaseAnalyzer,
    ) -> None:
        normalized = name.strip().lower()

        if not normalized:
            raise DatabaseConfigurationError(
                "database analyzer name cannot be empty"
            )

        if normalized in self._analyzers:
            raise DatabaseConfigurationError(
                f"duplicate database analyzer: {normalized}"
            )

        self._analyzers[normalized] = analyzer

    def names(self) -> tuple[str, ...]:
        """Return analyzer names in deterministic order."""
        return tuple(sorted(self._analyzers))

    def analyze(
        self,
        project_root: Path,
    ) -> tuple[DatabaseFinding, ...]:
        """Run all analyzers and return stable findings."""
        findings: list[DatabaseFinding] = []

        for name in self.names():
            findings.extend(
                self._analyzers[name](project_root)
            )

        return tuple(
            sorted(
                findings,
                key=lambda finding: finding.finding_id,
            )
        )
'@

Write-Utf8NoBom "forge\domain_intelligence\database\service.py" @'
"""Database discovery service for M4.3 Package 1."""

from __future__ import annotations

from forge.domain_intelligence.database.configuration import (
    configuration_findings,
    discover_database_configuration_files,
)
from forge.domain_intelligence.database.discovery import (
    discovery_findings,
    discover_migration_files,
    discover_query_files,
    discover_schema_files,
)
from forge.domain_intelligence.database.identifiers import (
    database_project_identifier,
    database_report_identifier,
)
from forge.domain_intelligence.database.models import (
    DatabaseAnalysisReport,
    DatabaseAnalysisRequest,
    DatabaseEngine,
    DatabaseProject,
)
from forge.domain_intelligence.database.policies import (
    DatabaseIntelligencePolicy,
    resolve_database_repository_root,
    validate_database_request,
)
from forge.domain_intelligence.database.postgres import (
    detect_postgresql,
    postgres_findings,
)
from forge.domain_intelligence.database.registry import (
    DatabaseAnalyzerRegistry,
)


def default_database_registry() -> DatabaseAnalyzerRegistry:
    """Return the M4.3 Package 1 analyzer registry."""
    return DatabaseAnalyzerRegistry(
        (
            ("configuration", configuration_findings),
            ("discovery", discovery_findings),
            ("postgres", postgres_findings),
        )
    )


class DatabaseIntelligenceService:
    """Discover database engines and repository artifacts safely."""

    def __init__(
        self,
        policy: DatabaseIntelligencePolicy | None = None,
        registry: DatabaseAnalyzerRegistry | None = None,
    ) -> None:
        self.policy = policy or DatabaseIntelligencePolicy()
        self.registry = registry or default_database_registry()

    def analyze(
        self,
        request: DatabaseAnalysisRequest,
    ) -> DatabaseAnalysisReport:
        """Run database discovery without live connections."""
        validate_database_request(request, self.policy)

        repository_root = resolve_database_repository_root(
            request.repository_root,
            self.policy,
        )
        project_root = (
            repository_root / request.project_root
        ).resolve()

        try:
            project_root.relative_to(repository_root)
        except ValueError as exc:
            raise ValueError(
                "resolved database project root escaped repository"
            ) from exc

        engines = set(detect_postgresql(project_root))

        project_payload = {
            "root": request.project_root,
            "engines": sorted(engine.value for engine in engines),
            "schema_files": discover_schema_files(project_root),
            "migration_files": discover_migration_files(project_root),
            "query_files": discover_query_files(project_root),
            "configuration_files": (
                discover_database_configuration_files(project_root)
            ),
        }

        project = DatabaseProject(
            project_id=database_project_identifier(project_payload),
            root=request.project_root,
            engines=tuple(
                sorted(
                    engines,
                    key=lambda engine: engine.value,
                )
            )
            or (DatabaseEngine.UNKNOWN,),
            schema_files=project_payload["schema_files"],
            migration_files=project_payload["migration_files"],
            query_files=project_payload["query_files"],
            configuration_files=project_payload[
                "configuration_files"
            ],
        )

        findings = self.registry.analyze(project_root)

        return DatabaseAnalysisReport(
            report_id=database_report_identifier(
                {
                    "project_id": project.project_id,
                    "finding_ids": [
                        finding.finding_id
                        for finding in findings
                    ],
                }
            ),
            project=project,
            findings=findings,
        )
'@

Write-Utf8NoBom "tests\test_domain_intelligence_database_postgres.py" @'
from pathlib import Path

from forge.domain_intelligence.database.models import DatabaseEngine
from forge.domain_intelligence.database.postgres import (
    detect_postgresql,
)


def test_detect_postgresql_from_compose(tmp_path: Path) -> None:
    (tmp_path / "docker-compose.yml").write_text(
        """
        services:
          db:
            image: postgres:16
        """,
        encoding="utf-8",
    )

    assert detect_postgresql(tmp_path) == (
        DatabaseEngine.POSTGRESQL,
    )


def test_detect_postgresql_returns_empty_when_absent(
    tmp_path: Path,
) -> None:
    assert detect_postgresql(tmp_path) == ()
'@

Write-Utf8NoBom "tests\test_domain_intelligence_database_configuration.py" @'
from pathlib import Path

from forge.domain_intelligence.database.configuration import (
    discover_database_configuration_files,
)


def test_database_configuration_discovery_excludes_env(
    tmp_path: Path,
) -> None:
    (tmp_path / "postgresql.conf").write_text(
        "max_connections = 100",
        encoding="utf-8",
    )
    (tmp_path / ".env").write_text(
        "DATABASE_URL=secret",
        encoding="utf-8",
    )

    assert discover_database_configuration_files(tmp_path) == (
        "postgresql.conf",
    )
'@

Write-Utf8NoBom "tests\test_domain_intelligence_database_discovery.py" @'
from pathlib import Path

from forge.domain_intelligence.database.discovery import (
    discover_migration_files,
    discover_query_files,
    discover_schema_files,
)


def test_database_artifact_discovery(tmp_path: Path) -> None:
    migrations = tmp_path / "migrations"
    migrations.mkdir()

    (tmp_path / "schema.sql").write_text(
        "CREATE TABLE orders(id uuid);",
        encoding="utf-8",
    )
    (migrations / "001_create_orders.sql").write_text(
        "CREATE TABLE orders(id uuid);",
        encoding="utf-8",
    )
    (tmp_path / "queries.sql").write_text(
        "SELECT * FROM orders;",
        encoding="utf-8",
    )

    assert discover_schema_files(tmp_path) == (
        "schema.sql",
    )
    assert discover_migration_files(tmp_path) == (
        "migrations/001_create_orders.sql",
    )
    assert discover_query_files(tmp_path) == (
        "migrations/001_create_orders.sql",
        "queries.sql",
        "schema.sql",
    )
'@

Write-Utf8NoBom "tests\test_domain_intelligence_database_registry.py" @'
from pathlib import Path

import pytest

from forge.domain_intelligence.database.errors import (
    DatabaseConfigurationError,
)
from forge.domain_intelligence.database.models import DatabaseFinding
from forge.domain_intelligence.database.registry import (
    DatabaseAnalyzerRegistry,
)


def empty_analyzer(
    project_root: Path,
) -> tuple[DatabaseFinding, ...]:
    del project_root
    return ()


def test_database_registry_names_are_sorted() -> None:
    registry = DatabaseAnalyzerRegistry(
        (
            ("postgres", empty_analyzer),
            ("configuration", empty_analyzer),
        )
    )

    assert registry.names() == (
        "configuration",
        "postgres",
    )


def test_database_registry_rejects_duplicates() -> None:
    with pytest.raises(DatabaseConfigurationError):
        DatabaseAnalyzerRegistry(
            (
                ("postgres", empty_analyzer),
                ("POSTGRES", empty_analyzer),
            )
        )
'@

Write-Utf8NoBom "tests\test_domain_intelligence_database_service.py" @'
from pathlib import Path

from forge.domain_intelligence.database.models import (
    DatabaseAnalysisRequest,
    DatabaseEngine,
)
from forge.domain_intelligence.database.service import (
    DatabaseIntelligenceService,
    default_database_registry,
)


def initialize_repository(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()


def test_default_database_registry() -> None:
    assert default_database_registry().names() == (
        "configuration",
        "discovery",
        "postgres",
    )


def test_service_discovers_postgresql_project(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    migrations = tmp_path / "migrations"
    migrations.mkdir()

    (tmp_path / "docker-compose.yml").write_text(
        "services:\n  db:\n    image: postgres:16\n",
        encoding="utf-8",
    )
    (tmp_path / "schema.sql").write_text(
        "CREATE TABLE orders(id uuid);",
        encoding="utf-8",
    )
    (migrations / "001_create_orders.sql").write_text(
        "CREATE TABLE orders(id uuid);",
        encoding="utf-8",
    )

    report = DatabaseIntelligenceService().analyze(
        DatabaseAnalysisRequest(
            repository_root=str(tmp_path),
        )
    )

    assert report.project.engines == (
        DatabaseEngine.POSTGRESQL,
    )
    assert report.project.schema_files == (
        "schema.sql",
    )
    assert report.project.migration_files == (
        "migrations/001_create_orders.sql",
    )


def test_service_reports_unknown_database(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    report = DatabaseIntelligenceService().analyze(
        DatabaseAnalysisRequest(
            repository_root=str(tmp_path),
        )
    )

    assert report.project.engines == (
        DatabaseEngine.UNKNOWN,
    )
'@

Write-Host ""
Write-Host "M4.3 Package 1 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_domain_intelligence_database_postgres.py `
    .\tests\test_domain_intelligence_database_configuration.py `
    .\tests\test_domain_intelligence_database_discovery.py `
    .\tests\test_domain_intelligence_database_registry.py `
    .\tests\test_domain_intelligence_database_service.py `
    -p no:cacheprovider
Assert-CommandSuccess "M4.3 Package 1 tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M4.3 PACKAGE 1 COMPLETE" -ForegroundColor Green

git status --short