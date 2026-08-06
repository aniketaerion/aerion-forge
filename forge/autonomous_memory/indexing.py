"""Deterministic in-memory memory index."""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.autonomous_memory.models import MemoryRecord


@dataclass(slots=True)
class MemoryIndex:
    """Index memory by repository, tags, modules, and capabilities."""

    _repository: dict[str, set[str]] = field(
        default_factory=dict
    )
    _tags: dict[str, set[str]] = field(default_factory=dict)
    _modules: dict[str, set[str]] = field(
        default_factory=dict
    )
    _capabilities: dict[str, set[str]] = field(
        default_factory=dict
    )

    def add(self, record: MemoryRecord) -> None:
        self._repository.setdefault(
            record.repository_scope,
            set(),
        ).add(record.memory_id)

        for tag in record.tags:
            self._tags.setdefault(tag, set()).add(
                record.memory_id
            )

        for module in record.module_scope:
            self._modules.setdefault(module, set()).add(
                record.memory_id
            )

        for capability in record.capability_scope:
            self._capabilities.setdefault(
                capability,
                set(),
            ).add(record.memory_id)

    def candidates(
        self,
        *,
        repository_scope: str,
        tags: tuple[str, ...] = (),
        module_scope: tuple[str, ...] = (),
        capability_scope: tuple[str, ...] = (),
    ) -> tuple[str, ...]:
        candidate_ids = set(
            self._repository.get(repository_scope, set())
        )

        for tag in tags:
            candidate_ids &= self._tags.get(tag, set())

        for module in module_scope:
            candidate_ids &= self._modules.get(
                module,
                set(),
            )

        for capability in capability_scope:
            candidate_ids &= self._capabilities.get(
                capability,
                set(),
            )

        return tuple(sorted(candidate_ids))