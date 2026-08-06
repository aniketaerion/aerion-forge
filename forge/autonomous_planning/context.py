"""Repository-grounded planning context."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class PlanningContext(BaseModel):
    """Evidence and constraints used to generate a plan."""

    model_config = ConfigDict(frozen=True)

    repository_root: str
    repository_fingerprint: str
    known_modules: tuple[str, ...] = ()
    known_capabilities: tuple[str, ...] = ()
    relevant_files: tuple[str, ...] = ()
    validation_commands: tuple[str, ...] = ()
    architecture_constraints: tuple[str, ...] = ()
    operational_constraints: tuple[str, ...] = ()
    evidence_references: tuple[str, ...] = ()