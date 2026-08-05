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

Write-Utf8NoBom "forge\domain_intelligence\database\schema.py" @'
"""SQL schema parsing for M4.3 Database Domain Intelligence."""

from __future__ import annotations

import re
from pathlib import Path

from forge.domain_intelligence.database.identifiers import (
    database_object_identifier,
)
from forge.domain_intelligence.database.models import (
    DatabaseColumn,
    DatabaseTable,
)

_CREATE_TABLE_PATTERN = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?"
    r"(?:(?P<schema>[A-Za-z_][A-Za-z0-9_]*)\.)?"
    r"(?P<table>[A-Za-z_][A-Za-z0-9_]*)\s*"
    r"\((?P<body>.*?)\)\s*;",
    re.IGNORECASE | re.DOTALL,
)


def _split_sql_items(body: str) -> tuple[str, ...]:
    items: list[str] = []
    current: list[str] = []
    depth = 0

    for character in body:
        if character == "(":
            depth += 1
        elif character == ")":
            depth = max(depth - 1, 0)

        if character == "," and depth == 0:
            value = "".join(current).strip()
            if value:
                items.append(value)
            current = []
            continue

        current.append(character)

    value = "".join(current).strip()
    if value:
        items.append(value)

    return tuple(items)


def parse_schema_sql(
    sql: str,
) -> tuple[DatabaseTable, ...]:
    """Parse conservative CREATE TABLE definitions."""
    tables: list[DatabaseTable] = []

    for match in _CREATE_TABLE_PATTERN.finditer(sql):
        schema_name = match.group("schema") or "public"
        table_name = match.group("table")
        columns: list[DatabaseColumn] = []

        for ordinal, item in enumerate(
            _split_sql_items(match.group("body")),
            start=1,
        ):
            normalized = item.strip()
            upper = normalized.upper()

            if upper.startswith(
                (
                    "PRIMARY KEY",
                    "FOREIGN KEY",
                    "UNIQUE",
                    "CHECK",
                    "CONSTRAINT",
                )
            ):
                continue

            parts = normalized.split()
            if len(parts) < 2:
                continue

            name = parts[0].strip('"')
            data_type = parts[1]
            nullable = "NOT NULL" not in upper
            default: str | None = None

            default_match = re.search(
                r"\bDEFAULT\s+(.+?)(?:\s+NOT\s+NULL|\s+NULL|$)",
                normalized,
                re.IGNORECASE,
            )
            if default_match is not None:
                default = default_match.group(1).strip()

            columns.append(
                DatabaseColumn(
                    column_id=database_object_identifier(
                        {
                            "schema": schema_name,
                            "table": table_name,
                            "column": name,
                        }
                    ),
                    name=name,
                    data_type=data_type,
                    nullable=nullable,
                    default=default,
                    ordinal_position=ordinal,
                )
            )

        tables.append(
            DatabaseTable(
                table_id=database_object_identifier(
                    {
                        "schema": schema_name,
                        "table": table_name,
                    }
                ),
                schema_name=schema_name,
                name=table_name,
                columns=tuple(columns),
            )
        )

    return tuple(
        sorted(
            tables,
            key=lambda table: (
                table.schema_name,
                table.name,
            ),
        )
    )


def parse_schema_file(
    path: Path,
) -> tuple[DatabaseTable, ...]:
    """Parse a SQL schema file."""
    return parse_schema_sql(
        path.read_text(encoding="utf-8-sig")
    )
'@

Write-Utf8NoBom "forge\domain_intelligence\database\constraints.py" @'
"""Constraint extraction for M4.3 Database Domain Intelligence."""

from __future__ import annotations

import re

from forge.domain_intelligence.database.identifiers import (
    database_object_identifier,
)
from forge.domain_intelligence.database.models import (
    DatabaseConstraint,
    DatabaseObjectKind,
)

_PRIMARY_KEY_PATTERN = re.compile(
    r"(?:CONSTRAINT\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s+)?"
    r"PRIMARY\s+KEY\s*\((?P<columns>[^)]+)\)",
    re.IGNORECASE,
)

_FOREIGN_KEY_PATTERN = re.compile(
    r"(?:CONSTRAINT\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s+)?"
    r"FOREIGN\s+KEY\s*\((?P<columns>[^)]+)\)\s+"
    r"REFERENCES\s+"
    r"(?:(?P<schema>[A-Za-z_][A-Za-z0-9_]*)\.)?"
    r"(?P<table>[A-Za-z_][A-Za-z0-9_]*)"
    r"\s*\((?P<referenced_columns>[^)]+)\)",
    re.IGNORECASE,
)

_UNIQUE_PATTERN = re.compile(
    r"(?:CONSTRAINT\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s+)?"
    r"UNIQUE\s*\((?P<columns>[^)]+)\)",
    re.IGNORECASE,
)


def _columns(value: str) -> tuple[str, ...]:
    return tuple(
        column.strip().strip('"')
        for column in value.split(",")
        if column.strip()
    )


def extract_constraints(
    sql: str,
    *,
    schema_name: str,
    table_name: str,
) -> tuple[DatabaseConstraint, ...]:
    """Extract primary, foreign, and unique constraints."""
    constraints: list[DatabaseConstraint] = []

    for match in _PRIMARY_KEY_PATTERN.finditer(sql):
        name = match.group("name") or f"{table_name}_pkey"
        columns = _columns(match.group("columns"))
        constraints.append(
            DatabaseConstraint(
                constraint_id=database_object_identifier(
                    {
                        "schema": schema_name,
                        "table": table_name,
                        "constraint": name,
                    }
                ),
                name=name,
                kind=DatabaseObjectKind.PRIMARY_KEY,
                columns=columns,
            )
        )

    for match in _FOREIGN_KEY_PATTERN.finditer(sql):
        name = (
            match.group("name")
            or f"{table_name}_{'_'.join(_columns(match.group('columns')))}_fkey"
        )
        constraints.append(
            DatabaseConstraint(
                constraint_id=database_object_identifier(
                    {
                        "schema": schema_name,
                        "table": table_name,
                        "constraint": name,
                    }
                ),
                name=name,
                kind=DatabaseObjectKind.FOREIGN_KEY,
                columns=_columns(match.group("columns")),
                referenced_schema=match.group("schema") or "public",
                referenced_table=match.group("table"),
                referenced_columns=_columns(
                    match.group("referenced_columns")
                ),
            )
        )

    for match in _UNIQUE_PATTERN.finditer(sql):
        name = (
            match.group("name")
            or f"{table_name}_{'_'.join(_columns(match.group('columns')))}_key"
        )
        constraints.append(
            DatabaseConstraint(
                constraint_id=database_object_identifier(
                    {
                        "schema": schema_name,
                        "table": table_name,
                        "constraint": name,
                    }
                ),
                name=name,
                kind=DatabaseObjectKind.UNIQUE_CONSTRAINT,
                columns=_columns(match.group("columns")),
            )
        )

    return tuple(
        sorted(
            constraints,
            key=lambda constraint: constraint.name,
        )
    )
'@

Write-Utf8NoBom "forge\domain_intelligence\database\indexes.py" @'
"""Index extraction for M4.3 Database Domain Intelligence."""

from __future__ import annotations

import re

from forge.domain_intelligence.database.identifiers import (
    database_object_identifier,
)
from forge.domain_intelligence.database.models import DatabaseIndex

_CREATE_INDEX_PATTERN = re.compile(
    r"CREATE\s+(?P<unique>UNIQUE\s+)?INDEX\s+"
    r"(?:IF\s+NOT\s+EXISTS\s+)?"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s+ON\s+"
    r"(?:(?P<schema>[A-Za-z_][A-Za-z0-9_]*)\.)?"
    r"(?P<table>[A-Za-z_][A-Za-z0-9_]*)"
    r"(?:\s+USING\s+(?P<method>[A-Za-z_][A-Za-z0-9_]*))?"
    r"\s*\((?P<columns>[^)]+)\)"
    r"(?:\s+WHERE\s+(?P<predicate>.*?))?;",
    re.IGNORECASE | re.DOTALL,
)


def extract_indexes(
    sql: str,
) -> tuple[DatabaseIndex, ...]:
    """Extract CREATE INDEX statements."""
    indexes: list[DatabaseIndex] = []

    for match in _CREATE_INDEX_PATTERN.finditer(sql):
        schema_name = match.group("schema") or "public"
        table_name = match.group("table")
        name = match.group("name")
        columns = tuple(
            column.strip().strip('"')
            for column in match.group("columns").split(",")
            if column.strip()
        )

        indexes.append(
            DatabaseIndex(
                index_id=database_object_identifier(
                    {
                        "schema": schema_name,
                        "table": table_name,
                        "index": name,
                    }
                ),
                name=name,
                columns=columns,
                unique=bool(match.group("unique")),
                method=match.group("method"),
                predicate=(
                    match.group("predicate").strip()
                    if match.group("predicate")
                    else None
                ),
            )
        )

    return tuple(
        sorted(indexes, key=lambda index: index.name)
    )
'@

Write-Utf8NoBom "forge\domain_intelligence\database\relationships.py" @'
"""Relationship mapping for M4.3 Database Domain Intelligence."""

from __future__ import annotations

from forge.domain_intelligence.database.models import (
    DatabaseObjectKind,
    DatabaseTable,
)


def relationship_edges(
    tables: tuple[DatabaseTable, ...],
) -> tuple[tuple[str, str, str], ...]:
    """Return deterministic foreign-key relationship edges."""
    edges: set[tuple[str, str, str]] = set()

    for table in tables:
        source = f"{table.schema_name}.{table.name}"

        for constraint in table.constraints:
            if (
                constraint.kind is DatabaseObjectKind.FOREIGN_KEY
                and constraint.referenced_table is not None
            ):
                target_schema = (
                    constraint.referenced_schema or "public"
                )
                target = (
                    f"{target_schema}."
                    f"{constraint.referenced_table}"
                )
                edges.add((source, target, constraint.name))

    return tuple(sorted(edges))
'@

Write-Utf8NoBom "forge\domain_intelligence\database\queries.py" @'
"""SQL query classification for M4.3 Database Domain Intelligence."""

from __future__ import annotations

import re
from pathlib import Path

_QUERY_PATTERNS = {
    "select": re.compile(r"\bSELECT\b", re.IGNORECASE),
    "insert": re.compile(r"\bINSERT\s+INTO\b", re.IGNORECASE),
    "update": re.compile(r"\bUPDATE\b", re.IGNORECASE),
    "delete": re.compile(r"\bDELETE\s+FROM\b", re.IGNORECASE),
}


def classify_queries(
    sql: str,
) -> dict[str, int]:
    """Count basic SQL query types."""
    return {
        name: len(pattern.findall(sql))
        for name, pattern in sorted(_QUERY_PATTERNS.items())
    }


def classify_query_file(
    path: Path,
) -> dict[str, int]:
    """Classify queries in one file."""
    return classify_queries(
        path.read_text(encoding="utf-8-sig")
    )
'@

Write-Utf8NoBom "forge\domain_intelligence\database\risk.py" @'
"""Database risk analysis for M4.3 Database Domain Intelligence."""

from __future__ import annotations

from forge.domain_intelligence.database.identifiers import (
    database_finding_identifier,
)
from forge.domain_intelligence.database.models import (
    DatabaseFinding,
    DatabaseFindingSeverity,
    DatabaseObjectKind,
    DatabaseTable,
)


def database_risk_findings(
    tables: tuple[DatabaseTable, ...],
) -> tuple[DatabaseFinding, ...]:
    """Identify conservative schema risks."""
    findings: list[DatabaseFinding] = []

    for table in tables:
        has_primary_key = any(
            constraint.kind is DatabaseObjectKind.PRIMARY_KEY
            for constraint in table.constraints
        )

        if not has_primary_key:
            finding_id = database_finding_identifier(
                {
                    "category": "missing_primary_key",
                    "schema": table.schema_name,
                    "table": table.name,
                }
            )
            findings.append(
                DatabaseFinding(
                    finding_id=finding_id,
                    category="missing_primary_key",
                    severity=DatabaseFindingSeverity.HIGH,
                    message=(
                        "Table has no detected primary key: "
                        f"{table.schema_name}.{table.name}"
                    ),
                    evidence={
                        "schema": table.schema_name,
                        "table": table.name,
                    },
                )
            )

        indexed_columns = {
            column
            for index in table.indexes
            for column in index.columns
        }

        for constraint in table.constraints:
            if constraint.kind is not DatabaseObjectKind.FOREIGN_KEY:
                continue

            missing = tuple(
                column
                for column in constraint.columns
                if column not in indexed_columns
            )

            if not missing:
                continue

            finding_id = database_finding_identifier(
                {
                    "category": "unindexed_foreign_key",
                    "schema": table.schema_name,
                    "table": table.name,
                    "constraint": constraint.name,
                    "columns": missing,
                }
            )
            findings.append(
                DatabaseFinding(
                    finding_id=finding_id,
                    category="unindexed_foreign_key",
                    severity=DatabaseFindingSeverity.MEDIUM,
                    message=(
                        "Foreign-key columns have no detected index: "
                        f"{table.schema_name}.{table.name}"
                    ),
                    evidence={
                        "constraint": constraint.name,
                        "columns": ",".join(missing),
                    },
                )
            )

    return tuple(
        sorted(findings, key=lambda finding: finding.finding_id)
    )
'@

Write-Utf8NoBom "tests\test_domain_intelligence_database_schema.py" @'
from forge.domain_intelligence.database.schema import parse_schema_sql


def test_parse_schema_sql() -> None:
    tables = parse_schema_sql(
        """
        CREATE TABLE public.orders (
            id uuid NOT NULL,
            reference text,
            created_at timestamp DEFAULT now()
        );
        """
    )

    assert len(tables) == 1
    assert tables[0].name == "orders"
    assert [column.name for column in tables[0].columns] == [
        "id",
        "reference",
        "created_at",
    ]
    assert not tables[0].columns[0].nullable
'@

Write-Utf8NoBom "tests\test_domain_intelligence_database_constraints.py" @'
from forge.domain_intelligence.database.constraints import (
    extract_constraints,
)
from forge.domain_intelligence.database.models import DatabaseObjectKind


def test_extract_constraints() -> None:
    constraints = extract_constraints(
        """
        CONSTRAINT orders_pkey PRIMARY KEY (id),
        CONSTRAINT orders_customer_fkey
            FOREIGN KEY (customer_id)
            REFERENCES public.customers(id),
        UNIQUE (reference)
        """,
        schema_name="public",
        table_name="orders",
    )

    assert {
        constraint.kind for constraint in constraints
    } == {
        DatabaseObjectKind.PRIMARY_KEY,
        DatabaseObjectKind.FOREIGN_KEY,
        DatabaseObjectKind.UNIQUE_CONSTRAINT,
    }
'@

Write-Utf8NoBom "tests\test_domain_intelligence_database_indexes.py" @'
from forge.domain_intelligence.database.indexes import extract_indexes


def test_extract_indexes() -> None:
    indexes = extract_indexes(
        """
        CREATE UNIQUE INDEX orders_reference_idx
        ON public.orders USING btree (reference);
        """
    )

    assert len(indexes) == 1
    assert indexes[0].name == "orders_reference_idx"
    assert indexes[0].unique
    assert indexes[0].method == "btree"
'@

Write-Utf8NoBom "tests\test_domain_intelligence_database_relationships.py" @'
from forge.domain_intelligence.database.models import (
    DatabaseConstraint,
    DatabaseObjectKind,
    DatabaseTable,
)
from forge.domain_intelligence.database.relationships import (
    relationship_edges,
)


def test_relationship_edges() -> None:
    table = DatabaseTable(
        table_id="table-orders",
        schema_name="public",
        name="orders",
        constraints=(
            DatabaseConstraint(
                constraint_id="constraint-1",
                name="orders_customer_fkey",
                kind=DatabaseObjectKind.FOREIGN_KEY,
                columns=("customer_id",),
                referenced_schema="public",
                referenced_table="customers",
                referenced_columns=("id",),
            ),
        ),
    )

    assert relationship_edges((table,)) == (
        (
            "public.orders",
            "public.customers",
            "orders_customer_fkey",
        ),
    )
'@

Write-Utf8NoBom "tests\test_domain_intelligence_database_queries.py" @'
from forge.domain_intelligence.database.queries import classify_queries


def test_classify_queries() -> None:
    result = classify_queries(
        """
        SELECT * FROM orders;
        INSERT INTO orders(id) VALUES ('1');
        UPDATE orders SET id = '2';
        DELETE FROM orders WHERE id = '2';
        """
    )

    assert result == {
        "delete": 1,
        "insert": 1,
        "select": 1,
        "update": 1,
    }
'@

Write-Utf8NoBom "tests\test_domain_intelligence_database_risk.py" @'
from forge.domain_intelligence.database.models import (
    DatabaseConstraint,
    DatabaseObjectKind,
    DatabaseTable,
)
from forge.domain_intelligence.database.risk import (
    database_risk_findings,
)


def test_database_risk_findings() -> None:
    table = DatabaseTable(
        table_id="table-orders",
        schema_name="public",
        name="orders",
        constraints=(
            DatabaseConstraint(
                constraint_id="constraint-1",
                name="orders_customer_fkey",
                kind=DatabaseObjectKind.FOREIGN_KEY,
                columns=("customer_id",),
                referenced_schema="public",
                referenced_table="customers",
                referenced_columns=("id",),
            ),
        ),
    )

    categories = {
        finding.category
        for finding in database_risk_findings((table,))
    }

    assert categories == {
        "missing_primary_key",
        "unindexed_foreign_key",
    }
'@

Write-Host ""
Write-Host "M4.3 Package 2 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_domain_intelligence_database_schema.py `
    .\tests\test_domain_intelligence_database_constraints.py `
    .\tests\test_domain_intelligence_database_indexes.py `
    .\tests\test_domain_intelligence_database_relationships.py `
    .\tests\test_domain_intelligence_database_queries.py `
    .\tests\test_domain_intelligence_database_risk.py `
    -p no:cacheprovider
Assert-CommandSuccess "M4.3 Package 2 tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M4.3 PACKAGE 2 COMPLETE" -ForegroundColor Green

git status --short