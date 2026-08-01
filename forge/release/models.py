"""Typed, read-only Phase 1 release evidence contracts."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class ReleaseDecision(StrEnum):
    PASS = "pass"
    CONDITIONAL_PASS = "conditional_pass"
    FAIL = "fail"


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class PhaseSchemaEntry(FrozenModel):
    subsystem: str
    schema_version: str
    persistence_file: str
    primary_models: tuple[str, ...]
    compatibility_policy: str


class PhaseReleaseManifest(FrozenModel):
    schema_version: str = "1.0"
    product: str
    version: str
    phase: str
    milestone: str
    release_name: str
    baseline_commit: str
    baseline_tag: str
    release_commit: str
    schemas: tuple[PhaseSchemaEntry, ...]
    implemented_capability_ids: tuple[str, ...]
    planned_capability_ids: tuple[str, ...]
    test_count: int
    source_file_count: int
    validation: dict[str, str]
    frozen_contracts: tuple[str, ...]
    persistence_files: tuple[str, ...]
    report_families: tuple[str, ...]
    cli_command_families: tuple[str, ...]
    security_status: str
    determinism_status: str
    compatibility_status: str
    release_decision: ReleaseDecision
    recommended_commit: str
    recommended_tag: str
