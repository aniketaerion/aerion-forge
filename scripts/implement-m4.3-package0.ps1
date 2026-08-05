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

Write-Utf8NoBom "forge\domain_intelligence\database\errors.py" @'
"""Typed errors for M4.3 Database Domain Intelligence."""

from __future__ import annotations

from forge.domain_intelligence.errors import DomainIntelligenceError


class DatabaseIntelligenceError(DomainIntelligenceError):
    """Base error for database-intelligence operations."""


class DatabaseConfigurationError(DatabaseIntelligenceError):
    """Raised when database configuration is invalid."""


class DatabasePolicyError(DatabaseIntelligenceError):
    """Raised when database analysis violates policy."""


class DatabaseParseError(DatabaseIntelligenceError):
    """Raised when a database artifact cannot be parsed safely."""
'@

Write-Utf8NoBom "forge\domain_intelligence\database\identifiers.py" @'
"""Deterministic identifiers for M4.3 Database Intelligence."""

from __future__ import annotations

from typing import Any

from forge.domain_intelligence.identifiers import stable_identifier


def database_project_identifier(payload: Any) -> str:
    """Return a deterministic database-project identifier."""
    return stable_identifier("database-project", payload)


def database_object_identifier(payload: Any) -> str:
    """Return a deterministic database-object identifier."""
    return stable_identifier("database-object", payload)


def database_finding_identifier(payload: Any) -> str:
    """Return a deterministic database-finding identifier."""
    return stable_identifier("database-finding", payload)


def database_report_identifier(payload: Any) -> str:
    """Return a deterministic database-report identifier."""
    return stable_identifier("database-report", payload)
'@

Write-Utf8NoBom "forge\domain_intelligence\database\models.py" @'
"""Immutable contracts for M4.3 Database Domain Intelligence."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DatabaseEngine(StrEnum):
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    MSSQL = "mssql"
    ORACLE = "oracle"
    UNKNOWN = "unknown"


class DatabaseObjectKind(StrEnum):
    SCHEMA = "schema"
    TABLE = "table"
    COLUMN = "column"
    PRIMARY_KEY = "primary_key"
    FOREIGN_KEY = "foreign_key"
    UNIQUE_CONSTRAINT = "unique_constraint"
    CHECK_CONSTRAINT = "check_constraint"
    INDEX = "index"
    VIEW = "view"
    FUNCTION = "function"
    TRIGGER = "trigger"
    MIGRATION = "migration"
    QUERY = "query"


class DatabaseFindingSeverity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ImmutableDatabaseModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
    )


class DatabaseAnalysisRequest(ImmutableDatabaseModel):
    repository_root: str = Field(min_length=1)
    project_root: str = Field(default=".", min_length=1)
    include_patterns: tuple[str, ...] = (
        "**/*.sql",
        "**/*.prisma",
        "**/*.py",
        "**/*.ts",
        "**/*.js",
        "**/*.json",
        "**/*.yaml",
        "**/*.yml",
        "**/*.toml",
    )
    exclude_patterns: tuple[str, ...] = (
        ".git/**",
        "node_modules/**",
        ".venv/**",
        "venv/**",
        "__pycache__/**",
        "dist/**",
        "build/**",
    )
    max_files: int = Field(default=10000, ge=1, le=100000)


class DatabaseColumn(ImmutableDatabaseModel):
    column_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    data_type: str = Field(min_length=1)
    nullable: bool = True
    default: str | None = None
    ordinal_position: int = Field(ge=1)


class DatabaseConstraint(ImmutableDatabaseModel):
    constraint_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    kind: DatabaseObjectKind
    columns: tuple[str, ...] = ()
    referenced_schema: str | None = None
    referenced_table: str | None = None
    referenced_columns: tuple[str, ...] = ()
    expression: str | None = None


class DatabaseIndex(ImmutableDatabaseModel):
    index_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    columns: tuple[str, ...] = ()
    unique: bool = False
    method: str | None = None
    predicate: str | None = None


class DatabaseTable(ImmutableDatabaseModel):
    table_id: str = Field(min_length=1)
    schema_name: str = Field(min_length=1)
    name: str = Field(min_length=1)
    columns: tuple[DatabaseColumn, ...] = ()
    constraints: tuple[DatabaseConstraint, ...] = ()
    indexes: tuple[DatabaseIndex, ...] = ()

    @field_validator("columns")
    @classmethod
    def ensure_unique_columns(
        cls,
        columns: tuple[DatabaseColumn, ...],
    ) -> tuple[DatabaseColumn, ...]:
        names = [column.name.lower() for column in columns]

        if len(names) != len(set(names)):
            raise ValueError("database column names must be unique")

        return columns


class DatabaseProject(ImmutableDatabaseModel):
    project_id: str = Field(min_length=1)
    root: str = Field(min_length=1)
    engines: tuple[DatabaseEngine, ...] = ()
    schema_files: tuple[str, ...] = ()
    migration_files: tuple[str, ...] = ()
    query_files: tuple[str, ...] = ()
    configuration_files: tuple[str, ...] = ()
    detected_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )


class DatabaseFinding(ImmutableDatabaseModel):
    finding_id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    severity: DatabaseFindingSeverity
    message: str = Field(min_length=1)
    path: str | None = None
    evidence: dict[str, str] = Field(default_factory=dict)


class DatabaseAnalysisReport(ImmutableDatabaseModel):
    report_id: str = Field(min_length=1)
    project: DatabaseProject
    tables: tuple[DatabaseTable, ...] = ()
    findings: tuple[DatabaseFinding, ...] = ()
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )

    @field_validator("findings")
    @classmethod
    def ensure_unique_findings(
        cls,
        findings: tuple[DatabaseFinding, ...],
    ) -> tuple[DatabaseFinding, ...]:
        identifiers = [finding.finding_id for finding in findings]

        if len(identifiers) != len(set(identifiers)):
            raise ValueError(
                "database finding identifiers must be unique"
            )

        return findings
'@

Write-Utf8NoBom "forge\domain_intelligence\database\policies.py" @'
"""Safety policies for M4.3 Database Domain Intelligence."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from forge.domain_intelligence.database.errors import DatabasePolicyError
from forge.domain_intelligence.database.models import (
    DatabaseAnalysisRequest,
)


class DatabaseIntelligencePolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    allow_network: bool = False
    allow_database_connections: bool = False
    allow_query_execution: bool = False
    allow_schema_modification: bool = False
    inspect_secrets: bool = False
    require_repository_root: bool = True
    max_files: int = Field(default=10000, ge=1, le=100000)
    max_file_bytes: int = Field(
        default=5_000_000,
        ge=1,
        le=100_000_000,
    )


def resolve_database_repository_root(
    repository_root: str | Path,
    policy: DatabaseIntelligencePolicy,
) -> Path:
    """Resolve and validate the database repository root."""
    root = Path(repository_root).expanduser().resolve()

    if not root.is_dir():
        raise DatabasePolicyError(
            f"repository root does not exist: {root}"
        )

    if policy.require_repository_root and not (root / ".git").exists():
        raise DatabasePolicyError(
            f"repository root is not a Git repository: {root}"
        )

    return root


def validate_database_request(
    request: DatabaseAnalysisRequest,
    policy: DatabaseIntelligencePolicy,
) -> None:
    """Validate database-analysis scope and bounds."""
    if request.max_files > policy.max_files:
        raise DatabasePolicyError(
            f"request exceeds maximum file count: {policy.max_files}"
        )

    project_root = Path(request.project_root)

    if project_root.is_absolute() or ".." in project_root.parts:
        raise DatabasePolicyError(
            "project root must remain repository-relative"
        )
'@

Write-Utf8NoBom "forge\domain_intelligence\database\__init__.py" @'
"""M4.3 Database Domain Intelligence public API."""

from forge.domain_intelligence.database.errors import (
    DatabaseConfigurationError,
    DatabaseIntelligenceError,
    DatabaseParseError,
    DatabasePolicyError,
)
from forge.domain_intelligence.database.identifiers import (
    database_finding_identifier,
    database_object_identifier,
    database_project_identifier,
    database_report_identifier,
)
from forge.domain_intelligence.database.models import (
    DatabaseAnalysisReport,
    DatabaseAnalysisRequest,
    DatabaseColumn,
    DatabaseConstraint,
    DatabaseEngine,
    DatabaseFinding,
    DatabaseFindingSeverity,
    DatabaseIndex,
    DatabaseObjectKind,
    DatabaseProject,
    DatabaseTable,
)
from forge.domain_intelligence.database.policies import (
    DatabaseIntelligencePolicy,
    resolve_database_repository_root,
    validate_database_request,
)

__all__ = [
    "DatabaseAnalysisReport",
    "DatabaseAnalysisRequest",
    "DatabaseColumn",
    "DatabaseConfigurationError",
    "DatabaseConstraint",
    "DatabaseEngine",
    "DatabaseFinding",
    "DatabaseFindingSeverity",
    "DatabaseIndex",
    "DatabaseIntelligenceError",
    "DatabaseIntelligencePolicy",
    "DatabaseObjectKind",
    "DatabaseParseError",
    "DatabasePolicyError",
    "DatabaseProject",
    "DatabaseTable",
    "database_finding_identifier",
    "database_object_identifier",
    "database_project_identifier",
    "database_report_identifier",
    "resolve_database_repository_root",
    "validate_database_request",
]
'@

Write-Utf8NoBom "tests\test_domain_intelligence_database_identifiers.py" @'
from forge.domain_intelligence.database.identifiers import (
    database_object_identifier,
    database_project_identifier,
)


def test_database_project_identifier_is_deterministic() -> None:
    first = database_project_identifier(
        {"root": "apps/erp", "engine": "postgresql"}
    )
    second = database_project_identifier(
        {"engine": "postgresql", "root": "apps/erp"}
    )

    assert first == second
    assert first.startswith("database-project-")


def test_database_object_identifier_changes_by_object() -> None:
    first = database_object_identifier(
        {"schema": "public", "table": "orders"}
    )
    second = database_object_identifier(
        {"schema": "public", "table": "inventory"}
    )

    assert first != second
'@

Write-Utf8NoBom "tests\test_domain_intelligence_database_models.py" @'
import pytest
from pydantic import ValidationError

from forge.domain_intelligence.database.models import (
    DatabaseAnalysisReport,
    DatabaseColumn,
    DatabaseConstraint,
    DatabaseEngine,
    DatabaseFinding,
    DatabaseFindingSeverity,
    DatabaseObjectKind,
    DatabaseProject,
    DatabaseTable,
)


def test_database_table_supports_constraints() -> None:
    table = DatabaseTable(
        table_id="table-1",
        schema_name="public",
        name="orders",
        columns=(
            DatabaseColumn(
                column_id="column-1",
                name="id",
                data_type="uuid",
                nullable=False,
                ordinal_position=1,
            ),
        ),
        constraints=(
            DatabaseConstraint(
                constraint_id="constraint-1",
                name="orders_pkey",
                kind=DatabaseObjectKind.PRIMARY_KEY,
                columns=("id",),
            ),
        ),
    )

    assert table.constraints[0].kind is DatabaseObjectKind.PRIMARY_KEY


def test_database_table_rejects_duplicate_columns() -> None:
    column = DatabaseColumn(
        column_id="column-1",
        name="id",
        data_type="uuid",
        ordinal_position=1,
    )

    with pytest.raises(ValidationError):
        DatabaseTable(
            table_id="table-1",
            schema_name="public",
            name="orders",
            columns=(column, column),
        )


def test_database_report_rejects_duplicate_findings() -> None:
    project = DatabaseProject(
        project_id="database-project-1",
        root="apps/erp",
        engines=(DatabaseEngine.POSTGRESQL,),
    )
    finding = DatabaseFinding(
        finding_id="database-finding-1",
        category="schema",
        severity=DatabaseFindingSeverity.INFO,
        message="Schema detected.",
    )

    with pytest.raises(ValidationError):
        DatabaseAnalysisReport(
            report_id="database-report-1",
            project=project,
            findings=(finding, finding),
        )
'@

Write-Utf8NoBom "tests\test_domain_intelligence_database_policies.py" @'
from pathlib import Path

import pytest

from forge.domain_intelligence.database.errors import DatabasePolicyError
from forge.domain_intelligence.database.models import (
    DatabaseAnalysisRequest,
)
from forge.domain_intelligence.database.policies import (
    DatabaseIntelligencePolicy,
    resolve_database_repository_root,
    validate_database_request,
)


def test_database_policy_is_offline_and_read_only() -> None:
    policy = DatabaseIntelligencePolicy()

    assert not policy.allow_network
    assert not policy.allow_database_connections
    assert not policy.allow_query_execution
    assert not policy.allow_schema_modification
    assert not policy.inspect_secrets


def test_database_repository_requires_git(tmp_path: Path) -> None:
    with pytest.raises(DatabasePolicyError):
        resolve_database_repository_root(
            tmp_path,
            DatabaseIntelligencePolicy(),
        )


def test_database_request_rejects_path_escape() -> None:
    request = DatabaseAnalysisRequest(
        repository_root=".",
        project_root="../outside",
    )

    with pytest.raises(DatabasePolicyError):
        validate_database_request(
            request,
            DatabaseIntelligencePolicy(),
        )
'@

Write-Utf8NoBom "docs\domain_intelligence\database\ARCHITECTURE.md" @'
# M4.3 Database Domain Intelligence Architecture

M4.3 provides read-only database discovery and structural analysis through
typed contracts, PostgreSQL schema inspection, migration analysis, constraint
and index analysis, relationship mapping, query inspection, risk reporting,
and CLI integration.

Package 0 establishes the immutable contracts and safety boundary. It does not
connect to a live database, execute SQL, inspect secrets, or modify schemas.
'@

Write-Utf8NoBom "docs\domain_intelligence\database\SPECIFICATION.md" @'
# M4.3 Database Domain Intelligence Specification

Database intelligence shall identify:

- database engines and project configuration;
- schemas, tables, columns, keys, constraints, and indexes;
- migration history and ordering;
- relationships between entities;
- query artifacts and schema-change risks.

Analysis remains local, deterministic, bounded, offline, and read-only.
'@

Write-Utf8NoBom "docs\domain_intelligence\database\DATA_MODEL.md" @'
# M4.3 Database Data Model

Primary contracts:

- DatabaseAnalysisRequest
- DatabaseProject
- DatabaseColumn
- DatabaseConstraint
- DatabaseIndex
- DatabaseTable
- DatabaseFinding
- DatabaseAnalysisReport
- DatabaseIntelligencePolicy
'@

Write-Utf8NoBom "docs\domain_intelligence\database\SECURITY_MODEL.md" @'
# M4.3 Database Security Model

Database analysis is fail-closed.

- Network access is disabled.
- Live database connections are disabled.
- SQL execution is disabled.
- Schema modification is disabled.
- Secret inspection is disabled.
- Repository path escape is rejected.
- File count and file-size limits are enforced.
'@

Write-Utf8NoBom "docs\domain_intelligence\database\ACCEPTANCE_CRITERIA.md" @'
# M4.3 Package 0 Acceptance Criteria

- Database contracts are immutable and typed.
- Database identifiers are deterministic.
- PostgreSQL and additional engine types are represented.
- Tables, columns, constraints, and indexes are modeled.
- Duplicate columns and findings are rejected.
- Analysis is offline and read-only by default.
- Repository path escape is rejected.
- Ruff, MyPy, focused tests, and full regression pass.
'@

Write-Host ""
Write-Host "M4.3 Package 0 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_domain_intelligence_database_identifiers.py `
    .\tests\test_domain_intelligence_database_models.py `
    .\tests\test_domain_intelligence_database_policies.py `
    -p no:cacheprovider
Assert-CommandSuccess "M4.3 Package 0 tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M4.3 PACKAGE 0 COMPLETE" -ForegroundColor Green

git status --short