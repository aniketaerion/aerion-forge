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