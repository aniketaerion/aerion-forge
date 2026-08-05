"""Business ontology construction for M4.5."""

from __future__ import annotations

from collections import defaultdict

from forge.domain_intelligence.business_domain.models import (
    BusinessEntity,
)


def build_business_ontology(
    entities: tuple[BusinessEntity, ...],
) -> dict[str, tuple[str, ...]]:
    """Build a deterministic module-to-entity ontology."""
    ontology: dict[str, set[str]] = defaultdict(set)

    for entity in entities:
        module = entity.module or "unassigned"
        ontology[module].add(entity.name)

    return {
        module: tuple(sorted(names))
        for module, names in sorted(ontology.items())
    }


def ontology_relationships(
    entities: tuple[BusinessEntity, ...],
) -> tuple[tuple[str, str, str], ...]:
    """Infer conservative cross-module relationships by shared names."""
    by_name: dict[str, list[BusinessEntity]] = defaultdict(list)

    for entity in entities:
        by_name[entity.name.lower()].append(entity)

    relationships: set[tuple[str, str, str]] = set()

    for matching_entities in by_name.values():
        if len(matching_entities) < 2:
            continue

        ordered = sorted(
            matching_entities,
            key=lambda entity: (
                entity.module or "",
                entity.entity_id,
            ),
        )

        for index, source in enumerate(ordered):
            for target in ordered[index + 1 :]:
                relationships.add(
                    (
                        source.entity_id,
                        target.entity_id,
                        "shared_business_concept",
                    )
                )

    return tuple(sorted(relationships))