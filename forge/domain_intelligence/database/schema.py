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