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
    New-Item -ItemType Directory -Path $Directory -Force | Out-Null

    [System.IO.File]::WriteAllText(
        $FullPath,
        $Content,
        [System.Text.UTF8Encoding]::new($false)
    )

    Write-Host "WROTE $Path" -ForegroundColor Green
}

Write-Utf8NoBom "forge\autonomous_repair\errors.py" @'
"""Typed errors for M3.5 Autonomous Repair."""


class AutonomousRepairError(RuntimeError):
    """Base error for autonomous repair."""


class RepairInputValidationError(AutonomousRepairError):
    """Raised when repair input is invalid."""


class RepairProviderNotFoundError(AutonomousRepairError):
    """Raised when a requested provider is unavailable."""


class RepairProviderConflictError(AutonomousRepairError):
    """Raised when duplicate provider registrations conflict."""


class RepairProposalError(AutonomousRepairError):
    """Raised when a bounded proposal cannot be generated."""


class RepairPolicyViolationError(AutonomousRepairError):
    """Raised when a repair violates policy."""


class RepairApprovalRequiredError(AutonomousRepairError):
    """Raised when apply mode lacks explicit approval."""


class RepairRepositoryStateError(AutonomousRepairError):
    """Raised when repository state changed unexpectedly."""


class RepairAttemptLimitError(AutonomousRepairError):
    """Raised when maximum repair attempts are exhausted."""


class RepairExecutionError(AutonomousRepairError):
    """Raised when repair execution fails."""


class RepairValidationError(AutonomousRepairError):
    """Raised when post-repair validation fails."""


class RepairRollbackError(AutonomousRepairError):
    """Raised when rollback cannot restore prior state."""


class RepairPersistenceError(AutonomousRepairError):
    """Raised when session evidence cannot be persisted."""
'@

Write-Utf8NoBom "forge\autonomous_repair\identifiers.py" @'
"""Deterministic identifiers for M3.5 Autonomous Repair."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any


def sha256_text(value: str) -> str:
    """Return a SHA-256 digest for UTF-8 text."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def stable_identifier(
    prefix: str,
    payload: Mapping[str, Any] | Sequence[Any] | str,
) -> str:
    """Build a stable identifier from canonical JSON."""
    if isinstance(payload, str):
        canonical = payload
    else:
        canonical = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            default=str,
        )
    return f"{prefix}_{sha256_text(canonical)[:24]}"


def proposal_identifier(payload: Mapping[str, Any]) -> str:
    """Return a stable proposal identifier."""
    return stable_identifier("repairprop", payload)


def execution_request_identifier(payload: Mapping[str, Any]) -> str:
    """Return a stable execution-request identifier."""
    return stable_identifier("repairexec", payload)


def execution_session_identifier(payload: Mapping[str, Any]) -> str:
    """Return a stable execution-session identifier."""
    return stable_identifier("repairsess", payload)


def patch_identifier(payload: Mapping[str, Any]) -> str:
    """Return a stable repair-patch identifier."""
    return stable_identifier("repairpatch", payload)
'@

Write-Utf8NoBom "forge\autonomous_repair\models.py" @'
"""Immutable contracts for M3.5 Autonomous Repair."""

from __future__ import annotations

from enum import StrEnum
from pathlib import PurePosixPath
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FrozenModel(BaseModel):
    """Base class for immutable repair contracts."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class RepairProviderType(StrEnum):
    """Supported repair providers."""

    EXACT_PATCH = "exact_patch"
    RUFF_FIX = "ruff_fix"


class RepairPatchOperation(StrEnum):
    """Supported bounded patch operations."""

    INSERT = "insert"
    REPLACE = "replace"
    DELETE = "delete"


class RepairExecutionStatus(StrEnum):
    """Autonomous repair state."""

    CREATED = "created"
    VALIDATED = "validated"
    PROPOSED = "proposed"
    DRY_RUN_COMPLETE = "dry_run_complete"
    AWAITING_APPROVAL = "awaiting_approval"
    APPLYING = "applying"
    REVALIDATING = "revalidating"
    SUCCEEDED = "succeeded"
    ROLLING_BACK = "rolling_back"
    RETRY_READY = "retry_ready"
    FAILED = "failed"


def _relative_path(value: str) -> str:
    normalized = value.replace("\\", "/").strip()
    path = PurePosixPath(normalized)
    if not normalized or path.is_absolute() or ".." in path.parts:
        raise ValueError("path must be repository-relative without traversal")
    return path.as_posix()


class RepairApproval(FrozenModel):
    """Explicit human approval evidence."""

    approved: bool = False
    approved_by: str | None = None
    reason: str | None = None

    @model_validator(mode="after")
    def validate_approval(self) -> RepairApproval:
        if self.approved and not self.approved_by:
            raise ValueError("approved repairs require approved_by")
        return self


class RepairInput(FrozenModel):
    """Input derived from an M3.4 repair candidate."""

    input_id: str
    candidate_id: str
    repository_root: str
    provider: RepairProviderType
    finding_ids: tuple[str, ...]
    target_paths: tuple[str, ...]
    repository_fingerprint: str
    objective: str

    @model_validator(mode="after")
    def validate_input(self) -> RepairInput:
        if not self.finding_ids:
            raise ValueError("repair input requires findings")
        if not self.target_paths:
            raise ValueError("repair input requires target paths")
        normalized = tuple(_relative_path(path) for path in self.target_paths)
        if len(normalized) != len(set(normalized)):
            raise ValueError("duplicate target paths are not allowed")
        object.__setattr__(self, "target_paths", normalized)
        return self


class RepairPatch(FrozenModel):
    """One bounded file patch."""

    patch_id: str
    relative_path: str
    operation: RepairPatchOperation
    start_offset: Annotated[int, Field(ge=0)]
    end_offset: Annotated[int, Field(ge=0)]
    expected_text: str = ""
    replacement_text: str = ""
    source_fingerprint: str

    @model_validator(mode="after")
    def validate_patch(self) -> RepairPatch:
        object.__setattr__(self, "relative_path", _relative_path(self.relative_path))
        if self.end_offset < self.start_offset:
            raise ValueError("end_offset may not precede start_offset")
        if self.operation is RepairPatchOperation.INSERT:
            if self.start_offset != self.end_offset:
                raise ValueError("INSERT requires equal offsets")
            if self.expected_text:
                raise ValueError("INSERT must not include expected_text")
        if self.operation is RepairPatchOperation.DELETE:
            if not self.expected_text:
                raise ValueError("DELETE requires expected_text")
            if self.replacement_text:
                raise ValueError("DELETE requires empty replacement_text")
        if self.operation is RepairPatchOperation.REPLACE and not self.expected_text:
            raise ValueError("REPLACE requires expected_text")
        return self


class RepairProposal(FrozenModel):
    """Provider-generated bounded repair proposal."""

    proposal_id: str
    input_id: str
    provider: RepairProviderType
    patches: tuple[RepairPatch, ...]
    affected_paths: tuple[str, ...]
    risk_notes: tuple[str, ...] = ()
    validation_commands: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_proposal(self) -> RepairProposal:
        if not self.patches:
            raise ValueError("repair proposal requires at least one patch")
        normalized = tuple(_relative_path(path) for path in self.affected_paths)
        patch_paths = {patch.relative_path for patch in self.patches}
        if patch_paths != set(normalized):
            raise ValueError("affected_paths must match patch target paths")
        object.__setattr__(self, "affected_paths", normalized)
        return self


class RepairExecutionRequest(FrozenModel):
    """Dry-run or approved execution request."""

    request_id: str
    proposal: RepairProposal
    repository_root: str
    repository_fingerprint: str
    dry_run: bool = True
    approval: RepairApproval = RepairApproval()

    @model_validator(mode="after")
    def validate_execution_request(self) -> RepairExecutionRequest:
        if not self.dry_run and not self.approval.approved:
            raise ValueError("apply mode requires explicit approval")
        return self


class RepairValidationEvidence(FrozenModel):
    """Validation evidence before or after a repair."""

    stage: str
    passed: bool
    tool_results: tuple[str, ...] = ()
    finding_ids: tuple[str, ...] = ()


class RepairExecutionAttempt(FrozenModel):
    """One bounded autonomous-repair attempt."""

    attempt_number: Annotated[int, Field(ge=1)]
    proposal_id: str
    status: RepairExecutionStatus
    dry_run_request_id: str | None = None
    apply_request_id: str | None = None
    validation_evidence: tuple[RepairValidationEvidence, ...] = ()
    errors: tuple[str, ...] = ()


class RepairExecutionSession(FrozenModel):
    """Bounded repair execution session."""

    session_id: str
    input: RepairInput
    max_attempts: Annotated[int, Field(ge=1, le=10)]
    status: RepairExecutionStatus = RepairExecutionStatus.CREATED
    attempts: tuple[RepairExecutionAttempt, ...] = ()

    @model_validator(mode="after")
    def validate_attempt_limit(self) -> RepairExecutionSession:
        if len(self.attempts) > self.max_attempts:
            raise ValueError("attempt count exceeds max_attempts")
        return self


class RepairExecutionReport(FrozenModel):
    """Final auditable autonomous-repair report."""

    session_id: str
    status: RepairExecutionStatus
    succeeded: bool
    attempts: tuple[RepairExecutionAttempt, ...]
    final_repository_fingerprint: str | None = None
    messages: tuple[str, ...] = ()
'@

Write-Utf8NoBom "forge\autonomous_repair\policies.py" @'
"""Safety policy for M3.5 Autonomous Repair."""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from pydantic import Field

from forge.autonomous_repair.errors import (
    RepairApprovalRequiredError,
    RepairPolicyViolationError,
)
from forge.autonomous_repair.models import FrozenModel, RepairProviderType


class AutonomousRepairPolicy(FrozenModel):
    """Immutable bounded repair policy."""

    max_attempts: int = Field(default=3, ge=1, le=10)
    max_files_per_attempt: int = Field(default=5, ge=1, le=100)
    max_changed_bytes: int = Field(default=250_000, ge=1)
    allowed_providers: tuple[RepairProviderType, ...] = (
        RepairProviderType.EXACT_PATCH,
        RepairProviderType.RUFF_FIX,
    )
    protected_paths: tuple[str, ...] = (
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "reports",
        "audit",
        "memory",
    )
    dry_run_default: bool = True
    require_explicit_approval: bool = True
    require_source_fingerprints: bool = True
    rollback_on_failed_validation: bool = True
    stop_on_repository_state_change: bool = True
    allow_shell: bool = False
    allow_git_mutation: bool = False
    allow_dependency_changes: bool = False

    def validate_provider(self, provider: RepairProviderType) -> None:
        """Reject providers not permitted by policy."""
        if provider not in self.allowed_providers:
            raise RepairPolicyViolationError(
                f"repair provider is not permitted: {provider}"
            )

    def validate_apply_mode(self, *, dry_run: bool, approved: bool) -> None:
        """Require explicit approval for mutation."""
        if not dry_run and self.require_explicit_approval and not approved:
            raise RepairApprovalRequiredError(
                "repair application requires explicit approval"
            )

    def validate_paths(self, paths: tuple[str, ...]) -> tuple[str, ...]:
        """Normalize and reject protected or unsafe paths."""
        if len(paths) > self.max_files_per_attempt:
            raise RepairPolicyViolationError(
                "repair exceeds maximum files per attempt"
            )

        normalized: list[str] = []
        for raw_path in paths:
            path = PurePosixPath(raw_path.replace("\\", "/").strip())
            if path.is_absolute() or ".." in path.parts or not path.parts:
                raise RepairPolicyViolationError(f"invalid repair path: {raw_path}")
            if path.parts[0] in self.protected_paths:
                raise RepairPolicyViolationError(f"protected repair path: {raw_path}")
            normalized.append(path.as_posix())
        return tuple(normalized)

    @staticmethod
    def resolve_repository(repository_root: Path) -> Path:
        """Resolve and validate repository root."""
        root = repository_root.expanduser().resolve()
        if not root.is_dir():
            raise RepairPolicyViolationError(
                f"repository root does not exist: {root}"
            )
        return root
'@

Write-Utf8NoBom "forge\autonomous_repair\__init__.py" @'
"""M3.5 Autonomous Repair contracts."""

from forge.autonomous_repair.identifiers import (
    execution_request_identifier,
    execution_session_identifier,
    patch_identifier,
    proposal_identifier,
    sha256_text,
    stable_identifier,
)
from forge.autonomous_repair.models import (
    RepairApproval,
    RepairExecutionAttempt,
    RepairExecutionReport,
    RepairExecutionRequest,
    RepairExecutionSession,
    RepairExecutionStatus,
    RepairInput,
    RepairPatch,
    RepairPatchOperation,
    RepairProposal,
    RepairProviderType,
    RepairValidationEvidence,
)
from forge.autonomous_repair.policies import AutonomousRepairPolicy

__all__ = [
    "AutonomousRepairPolicy",
    "RepairApproval",
    "RepairExecutionAttempt",
    "RepairExecutionReport",
    "RepairExecutionRequest",
    "RepairExecutionSession",
    "RepairExecutionStatus",
    "RepairInput",
    "RepairPatch",
    "RepairPatchOperation",
    "RepairProposal",
    "RepairProviderType",
    "RepairValidationEvidence",
    "execution_request_identifier",
    "execution_session_identifier",
    "patch_identifier",
    "proposal_identifier",
    "sha256_text",
    "stable_identifier",
]
'@

Write-Utf8NoBom "tests\test_autonomous_repair_identifiers.py" @'
from forge.autonomous_repair.identifiers import (
    patch_identifier,
    proposal_identifier,
    stable_identifier,
)


def test_stable_identifier_is_order_independent() -> None:
    assert stable_identifier("x", {"a": 1, "b": 2}) == stable_identifier(
        "x", {"b": 2, "a": 1}
    )


def test_proposal_identifier_has_expected_prefix() -> None:
    assert proposal_identifier({"candidate": "c1"}).startswith("repairprop_")


def test_patch_identifier_changes_with_payload() -> None:
    assert patch_identifier({"x": 1}) != patch_identifier({"x": 2})
'@

Write-Utf8NoBom "tests\test_autonomous_repair_models.py" @'
import pytest
from pydantic import ValidationError

from forge.autonomous_repair.models import (
    RepairApproval,
    RepairExecutionRequest,
    RepairInput,
    RepairPatch,
    RepairPatchOperation,
    RepairProposal,
    RepairProviderType,
)


def patch() -> RepairPatch:
    return RepairPatch(
        patch_id="patch-1",
        relative_path="forge/app.py",
        operation=RepairPatchOperation.REPLACE,
        start_offset=0,
        end_offset=3,
        expected_text="old",
        replacement_text="new",
        source_fingerprint="a" * 64,
    )


def proposal() -> RepairProposal:
    item = patch()
    return RepairProposal(
        proposal_id="proposal-1",
        input_id="input-1",
        provider=RepairProviderType.EXACT_PATCH,
        patches=(item,),
        affected_paths=("forge/app.py",),
    )


def test_repair_input_rejects_path_traversal() -> None:
    with pytest.raises(ValidationError):
        RepairInput(
            input_id="input-1",
            candidate_id="candidate-1",
            repository_root=".",
            provider=RepairProviderType.EXACT_PATCH,
            finding_ids=("f1",),
            target_paths=("../secret.py",),
            repository_fingerprint="a" * 64,
            objective="fix",
        )


def test_apply_request_requires_approval() -> None:
    with pytest.raises(ValidationError):
        RepairExecutionRequest(
            request_id="request-1",
            proposal=proposal(),
            repository_root=".",
            repository_fingerprint="a" * 64,
            dry_run=False,
            approval=RepairApproval(),
        )


def test_approved_request_requires_approver_identity() -> None:
    with pytest.raises(ValidationError):
        RepairApproval(approved=True)


def test_models_are_immutable() -> None:
    item = patch()
    with pytest.raises(ValidationError):
        item.start_offset = 2
'@

Write-Utf8NoBom "tests\test_autonomous_repair_policies.py" @'
from pathlib import Path

import pytest

from forge.autonomous_repair.errors import (
    RepairApprovalRequiredError,
    RepairPolicyViolationError,
)
from forge.autonomous_repair.models import RepairProviderType
from forge.autonomous_repair.policies import AutonomousRepairPolicy


def test_policy_defaults_are_bounded() -> None:
    policy = AutonomousRepairPolicy()
    assert policy.max_attempts == 3
    assert policy.dry_run_default is True
    assert policy.allow_shell is False
    assert policy.allow_git_mutation is False


def test_policy_rejects_unapproved_apply() -> None:
    with pytest.raises(RepairApprovalRequiredError):
        AutonomousRepairPolicy().validate_apply_mode(
            dry_run=False,
            approved=False,
        )


def test_policy_rejects_protected_path() -> None:
    with pytest.raises(RepairPolicyViolationError):
        AutonomousRepairPolicy().validate_paths((".git/config",))


def test_policy_accepts_registered_provider() -> None:
    AutonomousRepairPolicy().validate_provider(
        RepairProviderType.EXACT_PATCH
    )


def test_policy_resolves_existing_repository(tmp_path: Path) -> None:
    assert AutonomousRepairPolicy.resolve_repository(tmp_path) == tmp_path.resolve()
'@

Write-Utf8NoBom "docs\autonomous_repair\ARCHITECTURE.md" @'
# M3.5 Autonomous Repair Architecture

## Objective

Take an approved M3.4 repair candidate, generate a bounded proposal, dry-run it through M3.3 Safe Code Editing, require explicit approval, apply atomically, revalidate through M3.4 and roll back on failure.

## Components

1. Immutable contracts and identifiers.
2. Repair-provider registry.
3. Exact-patch provider.
4. Isolated Ruff-fix provider.
5. Execution state machine.
6. Repair executor.
7. Service and reporting.
8. CLI and release validators.

## Safety boundary

M3.5 v1 forbids unrestricted LLM code generation, arbitrary shell execution, Git mutation, dependency installation, silent approval and unbounded retry loops.
'@

Write-Utf8NoBom "docs\autonomous_repair\SPECIFICATION.md" @'
# M3.5 Autonomous Repair Specification

Supported providers:

- `exact_patch`
- `ruff_fix`

Every proposal must identify exact target paths, source fingerprints, bounded operations, risk notes and required validation commands.

Dry-run is mandatory before mutation. Apply mode requires explicit approval. Repository state must be reverified before each attempt. Failed validation triggers rollback when policy requires it.
'@

Write-Utf8NoBom "docs\autonomous_repair\DATA_MODEL.md" @'
# M3.5 Data Model

Core immutable contracts:

- `RepairApproval`
- `RepairInput`
- `RepairPatch`
- `RepairProposal`
- `RepairExecutionRequest`
- `RepairValidationEvidence`
- `RepairExecutionAttempt`
- `RepairExecutionSession`
- `RepairExecutionReport`

All identifiers are deterministic and derived from canonical payloads.
'@

Write-Utf8NoBom "docs\autonomous_repair\PROVIDER_CONTRACT.md" @'
# M3.5 Provider Contract

A provider must:

1. Declare supported findings.
2. Produce bounded proposals only.
3. Never write directly to the real repository.
4. Never invoke a shell.
5. Declare affected paths.
6. Include expected source fingerprints.
7. Produce deterministic patches.
8. Fail closed when safety cannot be proven.
'@

Write-Utf8NoBom "docs\autonomous_repair\SECURITY_MODEL.md" @'
# M3.5 Security Model

Controls include:

- repository-relative paths only;
- protected-path rejection;
- source-fingerprint verification;
- maximum attempts;
- maximum files and changed bytes;
- explicit approval;
- no arbitrary shell;
- no Git mutation;
- no dependency changes;
- rollback on failed validation;
- stop on unexpected repository-state change.
'@

Write-Utf8NoBom "docs\autonomous_repair\STATE_MACHINE.md" @'
# M3.5 State Machine

`CREATED → VALIDATED → PROPOSED → DRY_RUN_COMPLETE → AWAITING_APPROVAL → APPLYING → REVALIDATING`

From `REVALIDATING`:

- pass → `SUCCEEDED`
- fail → `ROLLING_BACK`
- restored and attempts remain → `RETRY_READY`
- no attempts remain → `FAILED`

Invalid transitions must be rejected.
'@

Write-Utf8NoBom "docs\autonomous_repair\ACCEPTANCE_CRITERIA.md" @'
# M3.5 Acceptance Criteria

M3.5 is complete when:

- provider registration is deterministic;
- exact-patch and isolated Ruff-fix providers are implemented;
- proposals become valid M3.3 requests;
- dry-run never changes the real repository;
- apply requires explicit approval;
- repository fingerprints are verified;
- changed files and bytes are bounded;
- post-repair validation uses M3.4;
- failed validation rolls back exact original bytes;
- repeated identical proposals are blocked;
- attempt limits are enforced;
- CLI, reports and validation scripts pass.
'@

Write-Host ""
Write-Host "M3.5 Package 0 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m mypy .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m pytest `
    .\tests\test_autonomous_repair_identifiers.py `
    .\tests\test_autonomous_repair_models.py `
    .\tests\test_autonomous_repair_policies.py `
    -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m pytest -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "M3.5 PACKAGE 0 COMPLETE" -ForegroundColor Green
git status --short
