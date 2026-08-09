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

    New-Item `
        -ItemType Directory `
        -Path $Directory `
        -Force | Out-Null

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

$ExpectedBranch = "feature/m5.9-general-engineering-agent"
$CurrentBranch = git branch --show-current
Assert-CommandSuccess "Read current branch"

if ($CurrentBranch -ne $ExpectedBranch) {
    throw "M5.9 Package 0 must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

git merge-base --is-ancestor forge-v0.2-m5.8 HEAD
if ($LASTEXITCODE -ne 0) {
    throw "M5.9 Package 0 requires the forge-v0.2-m5.8 release baseline."
}

if (git status --porcelain) {
    throw "Working tree must be clean before M5.9 Package 0."
}

Write-Utf8NoBom "forge\general_engineering\errors.py" @'
"""Errors for the M5.9 General Engineering Agent."""

from __future__ import annotations


class GeneralEngineeringError(Exception):
    """Base error for general engineering failures."""


class EngineeringContractError(GeneralEngineeringError):
    """Raised when a general engineering contract is invalid."""


class EngineeringPolicyError(GeneralEngineeringError):
    """Raised when policy blocks an engineering action."""


class EngineeringScopeError(GeneralEngineeringError):
    """Raised when requested or proposed scope is invalid."""


class EngineeringEvidenceError(GeneralEngineeringError):
    """Raised when required repository evidence is missing or invalid."""


class EngineeringProviderError(GeneralEngineeringError):
    """Raised when a provider returns invalid or unusable proposal data."""


class EngineeringRepairError(GeneralEngineeringError):
    """Raised when bounded repair cannot proceed safely."""
'@

Write-Utf8NoBom "forge\general_engineering\states.py" @'
"""Enumerations for the M5.9 General Engineering Agent."""

from __future__ import annotations

from enum import StrEnum


class EngineeringRisk(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EvidenceType(StrEnum):
    FILE = "file"
    SYMBOL = "symbol"
    IMPORT = "import"
    REFERENCE = "reference"
    TEST = "test"
    CONFIGURATION = "configuration"
    BUILD = "build"
    CONVENTION = "convention"
    DEPENDENCY = "dependency"
    FINGERPRINT = "fingerprint"


class EditOperationType(StrEnum):
    CREATE_FILE = "create_file"
    INSERT = "insert"
    REPLACE = "replace"
    DELETE = "delete"
    RENAME = "rename"


class ValidationStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED_BY_APPROVED_EXCEPTION = "skipped_by_approved_exception"


class RepairDisposition(StrEnum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXHAUSTED = "exhausted"


class EngineeringTerminalStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"
'@

Write-Utf8NoBom "forge\general_engineering\identifiers.py" @'
"""Deterministic identifiers for M5.9 general engineering contracts."""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from pathlib import Path
from typing import Any


def _normalize(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, dict):
        return {
            str(key): _normalize(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, list | tuple | set | frozenset):
        items = [_normalize(item) for item in value]
        if isinstance(value, set | frozenset):
            items = sorted(
                items,
                key=lambda item: json.dumps(
                    item,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=True,
                ),
            )
        return items
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    raise TypeError(f"Unsupported identifier value: {type(value)!r}")


def deterministic_engineering_identifier(
    prefix: str,
    payload: dict[str, Any],
) -> str:
    canonical = json.dumps(
        _normalize(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]
    return f"{prefix}-{digest}"


def engineering_request_identifier(payload: dict[str, Any]) -> str:
    return deterministic_engineering_identifier("engineering-request", payload)


def repository_evidence_identifier(payload: dict[str, Any]) -> str:
    return deterministic_engineering_identifier("repository-evidence", payload)


def change_requirement_identifier(payload: dict[str, Any]) -> str:
    return deterministic_engineering_identifier("change-requirement", payload)


def change_plan_identifier(payload: dict[str, Any]) -> str:
    return deterministic_engineering_identifier("change-plan", payload)


def edit_operation_identifier(payload: dict[str, Any]) -> str:
    return deterministic_engineering_identifier("edit-operation", payload)


def change_set_identifier(payload: dict[str, Any]) -> str:
    return deterministic_engineering_identifier("change-set", payload)


def validation_plan_identifier(payload: dict[str, Any]) -> str:
    return deterministic_engineering_identifier("validation-plan", payload)


def validation_outcome_identifier(payload: dict[str, Any]) -> str:
    return deterministic_engineering_identifier("validation-outcome", payload)


def repair_proposal_identifier(payload: dict[str, Any]) -> str:
    return deterministic_engineering_identifier("repair-proposal", payload)


def engineering_evidence_identifier(payload: dict[str, Any]) -> str:
    return deterministic_engineering_identifier("engineering-evidence", payload)
'@

Write-Utf8NoBom "forge\general_engineering\policies.py" @'
"""Policies for the M5.9 General Engineering Agent."""

from __future__ import annotations

from pathlib import PurePosixPath

from pydantic import BaseModel, ConfigDict, Field, model_validator

from forge.general_engineering.errors import EngineeringPolicyError


class EngineeringLimits(BaseModel):
    model_config = ConfigDict(frozen=True)

    max_target_files: int = Field(default=20, ge=1, le=200)
    max_edit_operations: int = Field(default=100, ge=1, le=1000)
    max_repair_attempts: int = Field(default=3, ge=0, le=3)
    max_generated_content_bytes: int = Field(
        default=2_000_000,
        ge=1,
        le=20_000_000,
    )


class EngineeringSafetyPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    require_repository_grounding: bool = True
    require_plan_approval: bool = True
    require_edit_approval: bool = True
    require_release_approval: bool = True
    require_source_fingerprints_for_destructive_edits: bool = True
    allow_direct_provider_file_writes: bool = False
    allow_arbitrary_shell_execution: bool = False
    allow_scope_expansion_without_reapproval: bool = False
    allow_self_modification: bool = False


class EngineeringScopePolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    forbidden_paths: tuple[str, ...] = (
        ".git",
        ".venv",
        "venv",
        "__pycache__",
    )

    @model_validator(mode="after")
    def validate_forbidden_paths(self) -> "EngineeringScopePolicy":
        normalized = tuple(_normalize_relative_path(path) for path in self.forbidden_paths)
        if len(normalized) != len(set(normalized)):
            raise EngineeringPolicyError("Forbidden paths must be unique.")
        return self


class GeneralEngineeringPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    limits: EngineeringLimits = Field(default_factory=EngineeringLimits)
    safety: EngineeringSafetyPolicy = Field(
        default_factory=EngineeringSafetyPolicy
    )
    scope: EngineeringScopePolicy = Field(
        default_factory=EngineeringScopePolicy
    )


def _normalize_relative_path(path: str) -> str:
    stripped = path.strip().replace("\\", "/")
    if not stripped:
        raise EngineeringPolicyError("Policy path cannot be empty.")
    pure = PurePosixPath(stripped)
    if pure.is_absolute() or ".." in pure.parts:
        raise EngineeringPolicyError(
            f"Policy path must remain repository-relative: {path!r}"
        )
    return pure.as_posix()


def is_forbidden_path(
    path: str,
    policy: EngineeringScopePolicy,
) -> bool:
    normalized = _normalize_relative_path(path)
    target = PurePosixPath(normalized)

    for forbidden in policy.forbidden_paths:
        base = PurePosixPath(_normalize_relative_path(forbidden))
        if target == base or base in target.parents:
            return True
    return False
'@

Write-Utf8NoBom "forge\general_engineering\models.py" @'
"""Immutable contracts for the M5.9 General Engineering Agent."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from pydantic import BaseModel, ConfigDict, Field, model_validator

from forge.general_engineering.errors import EngineeringContractError
from forge.general_engineering.states import (
    EditOperationType,
    EngineeringRisk,
    EngineeringTerminalStatus,
    EvidenceType,
    RepairDisposition,
    ValidationStatus,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _validate_relative_path(path: str, field_name: str) -> str:
    stripped = path.strip().replace("\\", "/")
    if not stripped:
        raise EngineeringContractError(f"{field_name} cannot be empty.")

    pure = PurePosixPath(stripped)
    if pure.is_absolute() or ".." in pure.parts:
        raise EngineeringContractError(
            f"{field_name} must be repository-relative: {path!r}"
        )
    return pure.as_posix()


class EngineeringRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_id: str
    objective: str
    repository_root: str
    constraints: tuple[str, ...] = ()
    acceptance_criteria: tuple[str, ...] = ()
    explicit_target_paths: tuple[str, ...] = ()
    forbidden_paths: tuple[str, ...] = ()
    allow_code_changes: bool = False
    max_repair_attempts: int = Field(default=3, ge=0, le=3)
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_request(self) -> "EngineeringRequest":
        if not self.request_id.strip():
            raise EngineeringContractError("Request ID cannot be empty.")
        if not self.objective.strip():
            raise EngineeringContractError("Objective cannot be empty.")
        if not self.repository_root.strip():
            raise EngineeringContractError("Repository root cannot be empty.")

        root = Path(self.repository_root)
        if not root.is_absolute():
            raise EngineeringContractError(
                "Repository root must be an absolute path."
            )

        for path in self.explicit_target_paths:
            _validate_relative_path(path, "Explicit target path")
        for path in self.forbidden_paths:
            _validate_relative_path(path, "Forbidden path")
        return self


class RepositoryEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    evidence_id: str
    path: str
    evidence_type: EvidenceType
    rationale: str
    relevance: float = Field(ge=0.0, le=1.0)
    symbol: str | None = None
    fingerprint: str | None = None
    provenance: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_evidence(self) -> "RepositoryEvidence":
        _validate_relative_path(self.path, "Evidence path")
        if not self.rationale.strip():
            raise EngineeringContractError(
                "Repository evidence requires rationale."
            )
        return self


class RelevantSymbol(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    kind: str
    path: str
    evidence_ids: tuple[str, ...]
    rationale: str

    @model_validator(mode="after")
    def validate_symbol(self) -> "RelevantSymbol":
        _validate_relative_path(self.path, "Relevant symbol path")
        if not self.name.strip() or not self.kind.strip():
            raise EngineeringContractError(
                "Relevant symbol requires name and kind."
            )
        if not self.evidence_ids:
            raise EngineeringContractError(
                "Relevant symbol requires repository evidence."
            )
        if not self.rationale.strip():
            raise EngineeringContractError(
                "Relevant symbol requires rationale."
            )
        return self


class RelevantFile(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str
    evidence_ids: tuple[str, ...]
    rationale: str
    symbols: tuple[RelevantSymbol, ...] = ()

    @model_validator(mode="after")
    def validate_file(self) -> "RelevantFile":
        _validate_relative_path(self.path, "Relevant file path")
        if not self.evidence_ids:
            raise EngineeringContractError(
                "Relevant file requires repository evidence."
            )
        if not self.rationale.strip():
            raise EngineeringContractError(
                "Relevant file requires rationale."
            )
        return self


class EngineeringContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_id: str
    relevant_files: tuple[RelevantFile, ...]
    evidence: tuple[RepositoryEvidence, ...]

    @model_validator(mode="after")
    def validate_context(self) -> "EngineeringContext":
        if not self.relevant_files:
            raise EngineeringContractError(
                "Engineering context requires relevant files."
            )
        if not self.evidence:
            raise EngineeringContractError(
                "Engineering context requires repository evidence."
            )

        evidence_ids = {item.evidence_id for item in self.evidence}
        for file in self.relevant_files:
            missing = set(file.evidence_ids) - evidence_ids
            if missing:
                raise EngineeringContractError(
                    "Relevant file references unknown evidence: "
                    + ", ".join(sorted(missing))
                )
        return self


class ChangeRequirement(BaseModel):
    model_config = ConfigDict(frozen=True)

    requirement_id: str
    description: str
    acceptance_criteria: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_requirement(self) -> "ChangeRequirement":
        if not self.description.strip():
            raise EngineeringContractError(
                "Change requirement description cannot be empty."
            )
        return self


class ChangeSpecification(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_id: str
    requirements: tuple[ChangeRequirement, ...]
    constraints: tuple[str, ...] = ()
    invariants: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_specification(self) -> "ChangeSpecification":
        if not self.requirements:
            raise EngineeringContractError(
                "Change specification requires at least one requirement."
            )
        return self


class FileChangePlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str
    rationale: str
    evidence_ids: tuple[str, ...]
    relevant_symbols: tuple[str, ...] = ()
    intended_operations: tuple[EditOperationType, ...]
    dependencies: tuple[str, ...] = ()
    expected_effect: str
    risk: EngineeringRisk = EngineeringRisk.MEDIUM

    @model_validator(mode="after")
    def validate_file_plan(self) -> "FileChangePlan":
        _validate_relative_path(self.path, "File change path")
        if not self.rationale.strip():
            raise EngineeringContractError(
                "File change plan requires rationale."
            )
        if not self.evidence_ids:
            raise EngineeringContractError(
                "File change plan requires repository evidence."
            )
        if not self.intended_operations:
            raise EngineeringContractError(
                "File change plan requires intended operations."
            )
        if not self.expected_effect.strip():
            raise EngineeringContractError(
                "File change plan requires expected effect."
            )
        return self


class ValidationPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    validation_plan_id: str
    commands: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_plan(self) -> "ValidationPlan":
        if not self.commands and not self.capabilities:
            raise EngineeringContractError(
                "Validation plan requires commands or capabilities."
            )
        return self


class ChangePlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    plan_id: str
    request_id: str
    objective: str
    requirements: tuple[ChangeRequirement, ...]
    file_changes: tuple[FileChangePlan, ...]
    validation_plan: ValidationPlan
    expected_effect: str
    aggregate_risk: EngineeringRisk
    evidence_ids: tuple[str, ...]
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_change_plan(self) -> "ChangePlan":
        if not self.objective.strip():
            raise EngineeringContractError(
                "Change plan objective cannot be empty."
            )
        if not self.requirements:
            raise EngineeringContractError(
                "Change plan requires requirements."
            )
        if not self.file_changes:
            raise EngineeringContractError(
                "Change plan requires at least one file change."
            )
        if not self.evidence_ids:
            raise EngineeringContractError(
                "Change plan requires repository evidence."
            )
        if not self.expected_effect.strip():
            raise EngineeringContractError(
                "Change plan requires expected effect."
            )
        return self


class EditOperation(BaseModel):
    model_config = ConfigDict(frozen=True)

    operation_id: str
    operation_type: EditOperationType
    target_path: str
    rationale: str
    originating_requirement_id: str
    target_symbol: str | None = None
    source_fingerprint: str | None = None
    proposed_content: str | None = None
    rename_target_path: str | None = None
    evidence_ids: tuple[str, ...] = ()
    order: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_operation(self) -> "EditOperation":
        _validate_relative_path(self.target_path, "Edit target path")

        if self.rename_target_path is not None:
            _validate_relative_path(
                self.rename_target_path,
                "Rename target path",
            )

        if not self.rationale.strip():
            raise EngineeringContractError(
                "Edit operation requires rationale."
            )

        if not self.originating_requirement_id.strip():
            raise EngineeringContractError(
                "Edit operation requires an originating requirement."
            )

        if self.operation_type is EditOperationType.RENAME:
            if not self.rename_target_path:
                raise EngineeringContractError(
                    "RENAME operation requires rename_target_path."
                )
        elif self.rename_target_path is not None:
            raise EngineeringContractError(
                "rename_target_path is valid only for RENAME operations."
            )

        if self.operation_type in {
            EditOperationType.CREATE_FILE,
            EditOperationType.INSERT,
            EditOperationType.REPLACE,
        } and self.proposed_content is None:
            raise EngineeringContractError(
                f"{self.operation_type.value} requires proposed_content."
            )

        if self.operation_type in {
            EditOperationType.REPLACE,
            EditOperationType.DELETE,
            EditOperationType.RENAME,
        } and not self.source_fingerprint:
            raise EngineeringContractError(
                f"{self.operation_type.value} requires source_fingerprint."
            )

        return self


class GeneratedChangeSet(BaseModel):
    model_config = ConfigDict(frozen=True)

    change_set_id: str
    plan_id: str
    operations: tuple[EditOperation, ...]
    evidence_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_change_set(self) -> "GeneratedChangeSet":
        if not self.operations:
            raise EngineeringContractError(
                "Generated change set requires operations."
            )

        ordered = tuple(sorted(self.operations, key=lambda item: item.order))
        if ordered != self.operations:
            raise EngineeringContractError(
                "Generated change set operations must already be ordered."
            )

        operation_ids = [item.operation_id for item in self.operations]
        if len(operation_ids) != len(set(operation_ids)):
            raise EngineeringContractError(
                "Generated change set operation IDs must be unique."
            )
        return self


class ValidationOutcome(BaseModel):
    model_config = ConfigDict(frozen=True)

    outcome_id: str
    validation_plan_id: str
    status: ValidationStatus
    summary: str
    commands_run: tuple[str, ...] = ()
    failures: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_outcome(self) -> "ValidationOutcome":
        if not self.summary.strip():
            raise EngineeringContractError(
                "Validation outcome requires summary."
            )
        if (
            self.status is ValidationStatus.FAILED
            and not self.failures
        ):
            raise EngineeringContractError(
                "Failed validation requires failure evidence."
            )
        return self


class RepairProposal(BaseModel):
    model_config = ConfigDict(frozen=True)

    repair_id: str
    request_id: str
    attempt_number: int = Field(ge=1, le=3)
    diagnosis: str
    target_paths: tuple[str, ...]
    validation_outcome_id: str
    proposed_change_set_id: str | None = None
    disposition: RepairDisposition = RepairDisposition.PROPOSED
    risk: EngineeringRisk = EngineeringRisk.MEDIUM

    @model_validator(mode="after")
    def validate_repair(self) -> "RepairProposal":
        if not self.diagnosis.strip():
            raise EngineeringContractError(
                "Repair proposal requires diagnosis."
            )
        if not self.target_paths:
            raise EngineeringContractError(
                "Repair proposal requires bounded target paths."
            )
        for path in self.target_paths:
            _validate_relative_path(path, "Repair target path")
        return self


class EngineeringEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    evidence_id: str
    request_id: str
    repository_evidence_ids: tuple[str, ...]
    plan_id: str | None = None
    change_set_id: str | None = None
    validation_outcome_ids: tuple[str, ...] = ()
    repair_ids: tuple[str, ...] = ()
    approval_ids: tuple[str, ...] = ()
    terminal_status: EngineeringTerminalStatus
    summary: str
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_engineering_evidence(self) -> "EngineeringEvidence":
        if not self.repository_evidence_ids:
            raise EngineeringContractError(
                "Engineering evidence requires repository evidence."
            )
        if not self.summary.strip():
            raise EngineeringContractError(
                "Engineering evidence summary cannot be empty."
            )
        return self
'@

Write-Utf8NoBom "forge\general_engineering\protocols.py" @'
"""Provider protocols for the M5.9 General Engineering Agent."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from forge.general_engineering.models import (
    ChangePlan,
    ChangeSpecification,
    EngineeringContext,
    EngineeringRequest,
    GeneratedChangeSet,
    RepairProposal,
    ValidationOutcome,
)


@runtime_checkable
class EngineeringProvider(Protocol):
    """Reasoning-only provider boundary.

    Implementations propose typed engineering artifacts. They are intentionally
    not given repository mutation or shell-execution methods.
    """

    def understand_request(
        self,
        request: EngineeringRequest,
        context: EngineeringContext,
    ) -> ChangeSpecification:
        """Normalize the engineering request against repository context."""

    def propose_change_plan(
        self,
        request: EngineeringRequest,
        context: EngineeringContext,
        specification: ChangeSpecification,
    ) -> ChangePlan:
        """Propose a structured, repository-grounded change plan."""

    def synthesize_edits(
        self,
        request: EngineeringRequest,
        context: EngineeringContext,
        plan: ChangePlan,
    ) -> GeneratedChangeSet:
        """Propose structured edit operations for an approved plan."""

    def propose_repair(
        self,
        request: EngineeringRequest,
        context: EngineeringContext,
        plan: ChangePlan,
        validation_outcome: ValidationOutcome,
        attempt_number: int,
    ) -> RepairProposal:
        """Propose a bounded repair from validation evidence."""
'@

Write-Utf8NoBom "forge\general_engineering\__init__.py" @'
"""M5.9 General Engineering Agent foundational contracts."""

from forge.general_engineering.errors import (
    EngineeringContractError,
    EngineeringEvidenceError,
    EngineeringPolicyError,
    EngineeringProviderError,
    EngineeringRepairError,
    EngineeringScopeError,
    GeneralEngineeringError,
)
from forge.general_engineering.identifiers import (
    change_plan_identifier,
    change_requirement_identifier,
    change_set_identifier,
    deterministic_engineering_identifier,
    edit_operation_identifier,
    engineering_evidence_identifier,
    engineering_request_identifier,
    repair_proposal_identifier,
    repository_evidence_identifier,
    validation_outcome_identifier,
    validation_plan_identifier,
)
from forge.general_engineering.models import (
    ChangePlan,
    ChangeRequirement,
    ChangeSpecification,
    EditOperation,
    EngineeringContext,
    EngineeringEvidence,
    EngineeringRequest,
    FileChangePlan,
    GeneratedChangeSet,
    RelevantFile,
    RelevantSymbol,
    RepairProposal,
    RepositoryEvidence,
    ValidationOutcome,
    ValidationPlan,
)
from forge.general_engineering.policies import (
    EngineeringLimits,
    EngineeringSafetyPolicy,
    EngineeringScopePolicy,
    GeneralEngineeringPolicy,
    is_forbidden_path,
)
from forge.general_engineering.protocols import EngineeringProvider
from forge.general_engineering.states import (
    EditOperationType,
    EngineeringRisk,
    EngineeringTerminalStatus,
    EvidenceType,
    RepairDisposition,
    ValidationStatus,
)

__all__ = [
    "ChangePlan",
    "ChangeRequirement",
    "ChangeSpecification",
    "EditOperation",
    "EditOperationType",
    "EngineeringContext",
    "EngineeringContractError",
    "EngineeringEvidence",
    "EngineeringEvidenceError",
    "EngineeringLimits",
    "EngineeringPolicyError",
    "EngineeringProvider",
    "EngineeringProviderError",
    "EngineeringRepairError",
    "EngineeringRequest",
    "EngineeringRisk",
    "EngineeringSafetyPolicy",
    "EngineeringScopeError",
    "EngineeringScopePolicy",
    "EngineeringTerminalStatus",
    "EvidenceType",
    "FileChangePlan",
    "GeneralEngineeringError",
    "GeneralEngineeringPolicy",
    "GeneratedChangeSet",
    "RelevantFile",
    "RelevantSymbol",
    "RepairDisposition",
    "RepairProposal",
    "RepositoryEvidence",
    "ValidationOutcome",
    "ValidationPlan",
    "ValidationStatus",
    "change_plan_identifier",
    "change_requirement_identifier",
    "change_set_identifier",
    "deterministic_engineering_identifier",
    "edit_operation_identifier",
    "engineering_evidence_identifier",
    "engineering_request_identifier",
    "is_forbidden_path",
    "repair_proposal_identifier",
    "repository_evidence_identifier",
    "validation_outcome_identifier",
    "validation_plan_identifier",
]
'@

Write-Utf8NoBom "tests\test_general_engineering_identifiers.py" @'
from forge.general_engineering.identifiers import (
    deterministic_engineering_identifier,
)


def test_identifier_is_deterministic_and_order_independent() -> None:
    first = deterministic_engineering_identifier(
        "engineering-test",
        {
            "objective": "add validation",
            "paths": ["src/service.py", "tests/test_service.py"],
            "meta": {"b": 2, "a": 1},
        },
    )
    second = deterministic_engineering_identifier(
        "engineering-test",
        {
            "meta": {"a": 1, "b": 2},
            "paths": ["src/service.py", "tests/test_service.py"],
            "objective": "add validation",
        },
    )

    assert first == second
    assert first.startswith("engineering-test-")
'@

Write-Utf8NoBom "tests\test_general_engineering_states.py" @'
from forge.general_engineering.states import (
    EditOperationType,
    EngineeringRisk,
    ValidationStatus,
)


def test_general_engineering_states_are_stable_string_enums() -> None:
    assert EditOperationType.CREATE_FILE == "create_file"
    assert EditOperationType.REPLACE == "replace"
    assert EngineeringRisk.CRITICAL == "critical"
    assert ValidationStatus.PASSED == "passed"
'@

Write-Utf8NoBom "tests\test_general_engineering_models.py" @'
from pathlib import Path

import pytest

from forge.general_engineering.errors import EngineeringContractError
from forge.general_engineering.models import (
    EditOperation,
    EngineeringRequest,
    RepositoryEvidence,
)
from forge.general_engineering.states import (
    EditOperationType,
    EvidenceType,
)


def test_engineering_request_requires_absolute_repository_root(
    tmp_path: Path,
) -> None:
    request = EngineeringRequest(
        request_id="engineering-request-test",
        objective="Add service validation",
        repository_root=str(tmp_path),
        allow_code_changes=True,
    )

    assert request.repository_root == str(tmp_path)


def test_engineering_request_rejects_repository_escape_path(
    tmp_path: Path,
) -> None:
    with pytest.raises(EngineeringContractError):
        EngineeringRequest(
            request_id="engineering-request-test",
            objective="Add validation",
            repository_root=str(tmp_path),
            explicit_target_paths=("../outside.py",),
        )


def test_repository_evidence_requires_rationale() -> None:
    with pytest.raises(EngineeringContractError):
        RepositoryEvidence(
            evidence_id="repository-evidence-test",
            path="src/service.py",
            evidence_type=EvidenceType.FILE,
            relevance=1.0,
            rationale="",
        )


def test_replace_operation_requires_source_fingerprint() -> None:
    with pytest.raises(EngineeringContractError):
        EditOperation(
            operation_id="edit-operation-test",
            operation_type=EditOperationType.REPLACE,
            target_path="src/service.py",
            proposed_content="value = 2\n",
            rationale="Update implementation",
            originating_requirement_id="requirement-1",
        )


def test_create_file_operation_requires_content() -> None:
    with pytest.raises(EngineeringContractError):
        EditOperation(
            operation_id="edit-operation-test",
            operation_type=EditOperationType.CREATE_FILE,
            target_path="src/new_service.py",
            rationale="Create requested service",
            originating_requirement_id="requirement-1",
        )
'@

Write-Utf8NoBom "tests\test_general_engineering_policies.py" @'
import pytest

from forge.general_engineering.errors import EngineeringPolicyError
from forge.general_engineering.policies import (
    EngineeringLimits,
    EngineeringScopePolicy,
    GeneralEngineeringPolicy,
    is_forbidden_path,
)


def test_default_repair_limit_is_bounded_to_three() -> None:
    policy = GeneralEngineeringPolicy()

    assert policy.limits.max_repair_attempts == 3


def test_repair_limit_cannot_exceed_three() -> None:
    with pytest.raises(ValueError):
        EngineeringLimits(max_repair_attempts=4)


def test_forbidden_paths_are_enforced() -> None:
    policy = EngineeringScopePolicy()

    assert is_forbidden_path(".git/config", policy)
    assert is_forbidden_path(".venv/pyvenv.cfg", policy)
    assert not is_forbidden_path("src/service.py", policy)


def test_forbidden_policy_path_cannot_escape_repository() -> None:
    with pytest.raises(EngineeringPolicyError):
        EngineeringScopePolicy(forbidden_paths=("../outside",))
'@

Write-Utf8NoBom "tests\test_general_engineering_protocols.py" @'
from typing import get_type_hints

from forge.general_engineering.protocols import EngineeringProvider


def test_provider_protocol_exposes_reasoning_only_operations() -> None:
    assert hasattr(EngineeringProvider, "understand_request")
    assert hasattr(EngineeringProvider, "propose_change_plan")
    assert hasattr(EngineeringProvider, "synthesize_edits")
    assert hasattr(EngineeringProvider, "propose_repair")

    forbidden = {
        "write_file",
        "delete_file",
        "run_shell",
        "execute_shell",
        "approve",
        "release",
    }
    assert forbidden.isdisjoint(set(dir(EngineeringProvider)))


def test_provider_protocol_uses_typed_contracts() -> None:
    hints = get_type_hints(
        EngineeringProvider.synthesize_edits,
    )

    assert hints["return"].__name__ == "GeneratedChangeSet"
'@

Write-Utf8NoBom "scripts\validate-m5.9-architecture.ps1" @'
[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

$AllowedBranches = @(
    "feature/m5.9-general-engineering-agent",
    "main"
)

$CurrentBranch = git branch --show-current
if ($LASTEXITCODE -ne 0) {
    throw "Unable to read current Git branch."
}

if ($CurrentBranch -notin $AllowedBranches) {
    throw "M5.9 architecture validation must run on an approved branch: $($AllowedBranches -join ', '). Current branch: '$CurrentBranch'."
}

git merge-base --is-ancestor forge-v0.2-m5.8 HEAD
if ($LASTEXITCODE -ne 0) {
    throw "M5.9 architecture validation requires the forge-v0.2-m5.8 release baseline."
}

$ArchitectureFiles = @(
    ".\docs\general_engineering_agent\ARCHITECTURE.md",
    ".\docs\general_engineering_agent\SPECIFICATION.md",
    ".\docs\general_engineering_agent\DATA_MODEL.md",
    ".\docs\general_engineering_agent\CHANGE_PLAN_MODEL.md",
    ".\docs\general_engineering_agent\EDIT_MODEL.md",
    ".\docs\general_engineering_agent\VALIDATION_AND_REPAIR_MODEL.md",
    ".\docs\general_engineering_agent\PROVIDER_MODEL.md",
    ".\docs\general_engineering_agent\ACCEPTANCE_CRITERIA.md",
    ".\docs\general_engineering_agent\DECISIONS.md"
)

$ContractFiles = @(
    ".\forge\general_engineering\__init__.py",
    ".\forge\general_engineering\errors.py",
    ".\forge\general_engineering\states.py",
    ".\forge\general_engineering\identifiers.py",
    ".\forge\general_engineering\models.py",
    ".\forge\general_engineering\policies.py",
    ".\forge\general_engineering\protocols.py"
)

$TestFiles = @(
    ".\tests\test_general_engineering_identifiers.py",
    ".\tests\test_general_engineering_states.py",
    ".\tests\test_general_engineering_models.py",
    ".\tests\test_general_engineering_policies.py",
    ".\tests\test_general_engineering_protocols.py"
)

foreach ($Path in $ArchitectureFiles + $ContractFiles + $TestFiles) {
    if (-not (Test-Path $Path)) {
        throw "Missing required M5.9 Package 0 file: $Path"
    }

    if ((Get-Item $Path).Length -eq 0) {
        throw "M5.9 Package 0 file is empty: $Path"
    }
}

$CoreFiles = @(
    ".\forge\general_engineering\errors.py",
    ".\forge\general_engineering\states.py",
    ".\forge\general_engineering\identifiers.py",
    ".\forge\general_engineering\models.py",
    ".\forge\general_engineering\policies.py",
    ".\forge\general_engineering\protocols.py"
)

$ForbiddenProviderDependencies = Select-String `
    -Path $CoreFiles `
    -Pattern "openai|ollama|anthropic|google\.generativeai|litellm" `
    -ErrorAction SilentlyContinue

if ($ForbiddenProviderDependencies) {
    $ForbiddenProviderDependencies
    throw "M5.9 core contracts contain provider-specific dependencies."
}

$ForbiddenExecutionAuthority = Select-String `
    -Path $CoreFiles `
    -Pattern "subprocess|os\.system|Popen|write_text\(|write_bytes\(|open\(.*['`"]w|unlink\(|rmtree\(" `
    -ErrorAction SilentlyContinue

if ($ForbiddenExecutionAuthority) {
    $ForbiddenExecutionAuthority
    throw "M5.9 core contracts contain forbidden direct execution or filesystem mutation authority."
}

$ForbiddenTaskSpecificLogic = Select-String `
    -Path $CoreFiles `
    -Pattern "calculator|subtract|multiply|divide|PurchaseOrder|customer_service" `
    -ErrorAction SilentlyContinue

if ($ForbiddenTaskSpecificLogic) {
    $ForbiddenTaskSpecificLogic
    throw "M5.9 core contracts contain acceptance-task-specific logic."
}

$ProtocolContent = Get-Content ".\forge\general_engineering\protocols.py" -Raw

foreach ($RequiredMethod in @(
    "understand_request",
    "propose_change_plan",
    "synthesize_edits",
    "propose_repair"
)) {
    if ($ProtocolContent -notmatch "def $RequiredMethod\(") {
        throw "EngineeringProvider protocol is missing '$RequiredMethod'."
    }
}

foreach ($ForbiddenMethod in @(
    "write_file",
    "run_shell",
    "approve",
    "release"
)) {
    if ($ProtocolContent -match "def $ForbiddenMethod\(") {
        throw "EngineeringProvider exposes forbidden authority: '$ForbiddenMethod'."
    }
}

$Policies = Get-Content ".\forge\general_engineering\policies.py" -Raw

if ($Policies -notmatch "max_repair_attempts.*default=3") {
    throw "M5.9 repair bound is missing from EngineeringLimits."
}

if ($Policies -notmatch "allow_direct_provider_file_writes: bool = False") {
    throw "M5.9 provider direct-write prohibition is missing."
}

if ($Policies -notmatch "allow_arbitrary_shell_execution: bool = False") {
    throw "M5.9 arbitrary shell prohibition is missing."
}

Write-Host ""
Write-Host "M5.9 ARCHITECTURE VALIDATION PASSED" -ForegroundColor Green
Write-Host "Architecture documents: $($ArchitectureFiles.Count)"
Write-Host "General engineering contract files: $($ContractFiles.Count)"
Write-Host "Package 0 focused tests: $($TestFiles.Count)"
'@

Write-Host ""
Write-Host "M5.9 Package 0 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_general_engineering_identifiers.py `
    .\tests\test_general_engineering_states.py `
    .\tests\test_general_engineering_models.py `
    .\tests\test_general_engineering_policies.py `
    .\tests\test_general_engineering_protocols.py `
    -p no:cacheprovider
Assert-CommandSuccess "M5.9 Package 0 focused tests"

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m5.9-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot
Assert-CommandSuccess "M5.9 architecture validation"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full repository regression"

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "M5.9 PACKAGE 0 CONTRACT FOUNDATION COMPLETE" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green

Write-Host ""
Write-Host "NOTE: Package 0 defines contracts only." -ForegroundColor Yellow
Write-Host "No model provider, repository mutation, or runtime integration is implemented by this package." -ForegroundColor Yellow

Write-Host ""
git status --short
