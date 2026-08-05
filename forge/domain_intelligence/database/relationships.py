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