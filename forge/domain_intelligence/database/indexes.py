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