"""Typed, deterministic runtime diagnostics contracts."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SCHEMA_VERSION = "1.0"
CATALOGUE_VERSION = "1.0"
REDACTION = "********"


class HealthStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"
    SKIPPED = "skipped"


class DiagnosticSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class DiagnosticScope(StrEnum):
    RUNTIME = "runtime"
    WORKSPACE = "workspace"
    REPOSITORY = "repository"
    CONFIGURATION = "configuration"
    CAPABILITY = "capability"
    PERSISTENCE = "persistence"
    REPORTING = "reporting"
    INTEGRATION = "integration"
    SECURITY = "security"
    UNKNOWN = "unknown"


class DiagnosticCategory(StrEnum):
    CORE = "core"
    CONFIGURATION = "configuration"
    FILESYSTEM = "filesystem"
    PERSISTENCE = "persistence"
    REPORTING = "reporting"
    WORKSPACE = "workspace"
    DISCOVERY = "discovery"
    INDEXING = "indexing"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    CAPABILITIES = "capabilities"
    CONSISTENCY = "consistency"
    SECURITY = "security"
    COMPATIBILITY = "compatibility"
    UNKNOWN = "unknown"


class DiagnosticCriticality(StrEnum):
    REQUIRED = "required"
    RECOMMENDED = "recommended"
    OPTIONAL = "optional"


class DurationClass(StrEnum):
    INSTANT = "instant"
    SHORT = "short"
    BOUNDED = "bounded"


class StateFreshness(StrEnum):
    CURRENT = "current"
    STALE = "stale"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


class DiagnosticChangeType(StrEnum):
    ADDED = "added"
    REMOVED = "removed"
    UNCHANGED = "unchanged"
    STATUS_CHANGED = "status_changed"
    SEVERITY_CHANGED = "severity_changed"
    BLOCKING_CHANGED = "blocking_changed"
    EVIDENCE_CHANGED = "evidence_changed"
    ACTION_CHANGED = "action_changed"


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class DiagnosticDefinition(FrozenModel):
    check_id: str
    display_name: str
    description: str
    category: DiagnosticCategory
    scope: DiagnosticScope
    criticality: DiagnosticCriticality
    introduced_version: str = "0.2"
    introduced_milestone: str = "1.7"
    required_capabilities: tuple[str, ...] = ()
    required_configuration_keys: tuple[str, ...] = ()
    prerequisite_checks: tuple[str, ...] = ()
    target_required: bool = False
    workspace_required: bool = False
    portable: bool = True
    default_enabled: bool = True
    tags: tuple[str, ...] = ()
    schema_version: str = SCHEMA_VERSION

    @field_validator("check_id")
    @classmethod
    def canonical_id(cls, value: str) -> str:
        if not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)+", value):
            raise ValueError("check ID must be lowercase kebab-case")
        return value

    @model_validator(mode="after")
    def valid_target_requirement(self) -> DiagnosticDefinition:
        if self.workspace_required and not self.target_required:
            raise ValueError("workspace-required checks must require a target")
        return self


class DiagnosticEvidence(FrozenModel):
    evidence_id: str
    label: str
    safe_value: str
    source: str
    portable: bool = True
    sensitive: bool = False

    @model_validator(mode="after")
    def redact_sensitive(self) -> DiagnosticEvidence:
        if self.sensitive and self.safe_value != REDACTION:
            raise ValueError("sensitive evidence must be redacted")
        return self


class CorrectiveAction(FrozenModel):
    action_id: str
    title: str
    description: str
    command: str | None = None
    manual: bool = True
    destructive: bool = False
    requires_approval: bool = False
    related_capability: str | None = None

    @model_validator(mode="after")
    def advisory_only(self) -> CorrectiveAction:
        if self.destructive or not self.manual:
            raise ValueError("diagnostic corrective actions must be manual and non-destructive")
        return self


class DiagnosticResult(FrozenModel):
    check_id: str
    display_name: str
    status: HealthStatus
    severity: DiagnosticSeverity
    category: DiagnosticCategory
    scope: DiagnosticScope
    criticality: DiagnosticCriticality
    summary: str
    details: str = ""
    evidence: tuple[DiagnosticEvidence, ...] = ()
    corrective_actions: tuple[CorrectiveAction, ...] = ()
    blocking: bool = False
    prerequisite_results: tuple[str, ...] = ()
    duration_class: DurationClass = DurationClass.INSTANT
    schema_version: str = SCHEMA_VERSION

    @model_validator(mode="after")
    def unique_children(self) -> DiagnosticResult:
        evidence = [item.evidence_id for item in self.evidence]
        actions = [item.action_id for item in self.corrective_actions]
        if len(evidence) != len(set(evidence)):
            raise ValueError("duplicate evidence ID")
        if len(actions) != len(set(actions)):
            raise ValueError("duplicate corrective action ID")
        return self


class DiagnosticStatistics(FrozenModel):
    total_checks: int
    checks_by_status: dict[str, int]
    checks_by_category: dict[str, int]
    checks_by_scope: dict[str, int]
    checks_by_severity: dict[str, int]
    checks_by_criticality: dict[str, int]
    blocking_checks: int
    actionable_checks: int
    checks_with_warnings: int
    checks_with_errors: int


class DiagnosticSummary(FrozenModel):
    overall_status: HealthStatus
    total_checks: int
    healthy_count: int
    degraded_count: int
    unhealthy_count: int
    unknown_count: int
    not_applicable_count: int
    skipped_count: int
    blocking_count: int
    actionable_count: int


class DiagnosticGeneration(FrozenModel):
    schema_version: str = SCHEMA_VERSION
    generation_id: str
    previous_generation_id: str | None = None
    diagnostic_fingerprint: str
    scope: DiagnosticScope
    target_identity: str | None = None
    configuration_fingerprint: str
    capability_registry_fingerprint: str
    total_checks: int
    healthy_count: int
    degraded_count: int
    unhealthy_count: int
    unknown_count: int
    not_applicable_count: int
    skipped_count: int
    blocking_count: int
    overall_status: HealthStatus


class DiagnosticChange(FrozenModel):
    check_id: str
    change_type: DiagnosticChangeType
    detail: str = ""


class DiagnosticChangeSet(FrozenModel):
    changes: tuple[DiagnosticChange, ...] = ()
    overall_status_changed: bool = False


class DiagnosticSnapshot(FrozenModel):
    schema_version: str = SCHEMA_VERSION
    results: tuple[DiagnosticResult, ...]
    summary: DiagnosticSummary
    statistics: DiagnosticStatistics
    diagnostic_fingerprint: str
    generation: DiagnosticGeneration
    changes: DiagnosticChangeSet = DiagnosticChangeSet()


class DiagnosticStore(BaseModel):
    schema_version: str = SCHEMA_VERSION
    snapshots: dict[str, DiagnosticSnapshot] = Field(default_factory=dict)
    history: dict[str, list[DiagnosticSnapshot]] = Field(default_factory=dict)


class DiagnosticResultSet(FrozenModel):
    snapshot: DiagnosticSnapshot
    persisted: bool = False
    reports_written: bool = False


class DiagnosticConfiguration(FrozenModel):
    enabled: bool = True
    strict: bool = True
    history_limit: int = Field(default=5, ge=0, le=100)
    include_optional: bool = True
    write_probe_enabled: bool = True
    default_categories: tuple[DiagnosticCategory, ...] = ()


class DiagnosticValidationResult(FrozenModel):
    valid: bool
    errors: tuple[str, ...] = ()


def canonical_data(value: BaseModel) -> dict[str, Any]:
    """Return JSON-compatible model data for canonical hashing."""
    return value.model_dump(mode="json", exclude_none=True)
