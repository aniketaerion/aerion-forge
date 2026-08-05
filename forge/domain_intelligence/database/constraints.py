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