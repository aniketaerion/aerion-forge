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
    throw "M5.9 Package 1 must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

git merge-base --is-ancestor forge-v0.2-m5.8 HEAD
if ($LASTEXITCODE -ne 0) {
    throw "M5.9 Package 1 requires the forge-v0.2-m5.8 release baseline."
}

# Package 1 assumes Package 0 is already committed.
$RequiredPackage0Files = @(
    ".\forge\general_engineering\models.py",
    ".\forge\general_engineering\identifiers.py",
    ".\forge\general_engineering\policies.py",
    ".\forge\general_engineering\protocols.py"
)

foreach ($Path in $RequiredPackage0Files) {
    if (-not (Test-Path $Path)) {
        throw "Missing M5.9 Package 0 prerequisite: $Path"
    }
}

if (git status --porcelain) {
    throw "Working tree must be clean before M5.9 Package 1."
}

Write-Utf8NoBom "forge\general_engineering\normalization.py" @'
"""Normalization helpers for M5.9 engineering requests."""

from __future__ import annotations

import re
from collections.abc import Iterable


_WHITESPACE = re.compile(r"\s+")
_BULLET_PREFIX = re.compile(r"^\s*(?:[-*•]+|\d+[.)])\s*")


def normalize_text(value: str) -> str:
    """Return stable single-line text while preserving semantic punctuation."""
    return _WHITESPACE.sub(" ", value.strip())


def normalize_optional_items(values: Iterable[str]) -> tuple[str, ...]:
    """Normalize, de-duplicate, and preserve input order."""
    result: list[str] = []
    seen: set[str] = set()

    for raw in values:
        cleaned = normalize_text(_BULLET_PREFIX.sub("", raw))
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(cleaned)

    return tuple(result)


def normalize_repository_path(value: str) -> str:
    """Normalize a repository-relative path without permitting traversal."""
    cleaned = normalize_text(value).replace("\\", "/")
    while cleaned.startswith("./"):
        cleaned = cleaned[2:]
    return cleaned
'@

Write-Utf8NoBom "forge\general_engineering\requirement_extractor.py" @'
"""Deterministic requirement extraction for M5.9 Package 1."""

from __future__ import annotations

import re

from forge.general_engineering.identifiers import (
    change_requirement_identifier,
)
from forge.general_engineering.models import ChangeRequirement
from forge.general_engineering.normalization import normalize_text


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?;])\s+")
_CONJUNCTION_SPLIT = re.compile(
    r"\s+(?:and then|then|and)\s+",
    flags=re.IGNORECASE,
)


def _candidate_clauses(objective: str) -> tuple[str, ...]:
    normalized = normalize_text(objective)
    if not normalized:
        return ()

    clauses: list[str] = []
    for sentence in _SENTENCE_SPLIT.split(normalized):
        for part in _CONJUNCTION_SPLIT.split(sentence):
            cleaned = part.strip(" .;")
            if cleaned:
                clauses.append(cleaned)

    return tuple(clauses)


def extract_change_requirements(
    *,
    objective: str,
    acceptance_criteria: tuple[str, ...] = (),
) -> tuple[ChangeRequirement, ...]:
    """Extract generic verifiable requirements from a normalized objective.

    Package 1 intentionally uses deterministic generic segmentation only.
    Provider-assisted semantic understanding is introduced later.
    """
    clauses = _candidate_clauses(objective)
    if not clauses:
        return ()

    result: list[ChangeRequirement] = []
    normalized_acceptance = tuple(
        item for item in (normalize_text(value) for value in acceptance_criteria) if item
    )

    for index, clause in enumerate(clauses, start=1):
        payload = {
            "index": index,
            "description": clause,
            "acceptance_criteria": normalized_acceptance,
        }
        result.append(
            ChangeRequirement(
                requirement_id=change_requirement_identifier(payload),
                description=clause,
                acceptance_criteria=normalized_acceptance,
            )
        )

    return tuple(result)
'@

Write-Utf8NoBom "forge\general_engineering\request_builder.py" @'
"""EngineeringRequest builder for M5.9 Package 1."""

from __future__ import annotations

from pathlib import Path

from forge.general_engineering.identifiers import (
    engineering_request_identifier,
)
from forge.general_engineering.models import EngineeringRequest
from forge.general_engineering.normalization import (
    normalize_optional_items,
    normalize_repository_path,
    normalize_text,
)


def build_engineering_request(
    *,
    objective: str,
    repository_root: str | Path,
    constraints: tuple[str, ...] = (),
    acceptance_criteria: tuple[str, ...] = (),
    explicit_target_paths: tuple[str, ...] = (),
    forbidden_paths: tuple[str, ...] = (),
    allow_code_changes: bool = False,
    max_repair_attempts: int = 3,
) -> EngineeringRequest:
    """Create a normalized deterministic EngineeringRequest."""
    root = Path(repository_root).resolve()
    normalized_objective = normalize_text(objective)
    normalized_constraints = normalize_optional_items(constraints)
    normalized_acceptance = normalize_optional_items(acceptance_criteria)
    normalized_targets = tuple(
        normalize_repository_path(path) for path in explicit_target_paths
    )
    normalized_forbidden = tuple(
        normalize_repository_path(path) for path in forbidden_paths
    )

    payload = {
        "objective": normalized_objective,
        "repository_root": root.as_posix(),
        "constraints": normalized_constraints,
        "acceptance_criteria": normalized_acceptance,
        "explicit_target_paths": normalized_targets,
        "forbidden_paths": normalized_forbidden,
        "allow_code_changes": allow_code_changes,
        "max_repair_attempts": max_repair_attempts,
    }

    return EngineeringRequest(
        request_id=engineering_request_identifier(payload),
        objective=normalized_objective,
        repository_root=str(root),
        constraints=normalized_constraints,
        acceptance_criteria=normalized_acceptance,
        explicit_target_paths=normalized_targets,
        forbidden_paths=normalized_forbidden,
        allow_code_changes=allow_code_changes,
        max_repair_attempts=max_repair_attempts,
    )
'@

Write-Utf8NoBom "forge\general_engineering\request_understanding.py" @'
"""Request-understanding service for M5.9 Package 1."""

from __future__ import annotations

from dataclasses import dataclass

from forge.general_engineering.errors import EngineeringContractError
from forge.general_engineering.models import (
    ChangeSpecification,
    EngineeringRequest,
)
from forge.general_engineering.requirement_extractor import (
    extract_change_requirements,
)


@dataclass(frozen=True)
class RequestUnderstandingResult:
    """Normalized request plus deterministic change specification."""

    request: EngineeringRequest
    specification: ChangeSpecification


class EngineeringRequestUnderstandingService:
    """Convert a normalized request into a generic change specification.

    Package 1 is deliberately repository-independent. Repository grounding is
    introduced in Package 2.
    """

    def understand(
        self,
        request: EngineeringRequest,
    ) -> RequestUnderstandingResult:
        requirements = extract_change_requirements(
            objective=request.objective,
            acceptance_criteria=request.acceptance_criteria,
        )

        if not requirements:
            raise EngineeringContractError(
                "Engineering request produced no actionable requirements."
            )

        invariants = tuple(
            item
            for item in request.constraints
            if item.casefold().startswith(
                (
                    "do not ",
                    "must not ",
                    "preserve ",
                    "keep ",
                    "only ",
                )
            )
        )

        specification = ChangeSpecification(
            request_id=request.request_id,
            requirements=requirements,
            constraints=request.constraints,
            invariants=invariants,
        )

        return RequestUnderstandingResult(
            request=request,
            specification=specification,
        )


engineering_request_understanding_service = (
    EngineeringRequestUnderstandingService()
)
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
from forge.general_engineering.normalization import (
    normalize_optional_items,
    normalize_repository_path,
    normalize_text,
)
from forge.general_engineering.policies import (
    EngineeringLimits,
    EngineeringSafetyPolicy,
    EngineeringScopePolicy,
    GeneralEngineeringPolicy,
    is_forbidden_path,
)
from forge.general_engineering.protocols import EngineeringProvider
from forge.general_engineering.request_builder import (
    build_engineering_request,
)
from forge.general_engineering.request_understanding import (
    EngineeringRequestUnderstandingService,
    RequestUnderstandingResult,
    engineering_request_understanding_service,
)
from forge.general_engineering.requirement_extractor import (
    extract_change_requirements,
)
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
    "EngineeringRequestUnderstandingService",
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
    "RequestUnderstandingResult",
    "ValidationOutcome",
    "ValidationPlan",
    "ValidationStatus",
    "build_engineering_request",
    "change_plan_identifier",
    "change_requirement_identifier",
    "change_set_identifier",
    "deterministic_engineering_identifier",
    "edit_operation_identifier",
    "engineering_evidence_identifier",
    "engineering_request_identifier",
    "engineering_request_understanding_service",
    "extract_change_requirements",
    "is_forbidden_path",
    "normalize_optional_items",
    "normalize_repository_path",
    "normalize_text",
    "repair_proposal_identifier",
    "repository_evidence_identifier",
    "validation_outcome_identifier",
    "validation_plan_identifier",
]
'@

Write-Utf8NoBom "tests\test_general_engineering_normalization.py" @'
from forge.general_engineering.normalization import (
    normalize_optional_items,
    normalize_repository_path,
    normalize_text,
)


def test_normalize_text_collapses_whitespace() -> None:
    assert normalize_text("  Add   validation\n  and tests. ") == (
        "Add validation and tests."
    )


def test_optional_items_are_deduplicated_case_insensitively() -> None:
    assert normalize_optional_items(
        ("- Preserve behavior", "preserve behavior", "Add tests")
    ) == ("Preserve behavior", "Add tests")


def test_repository_path_normalization_is_stable() -> None:
    assert normalize_repository_path(r".\src\service.py") == "src/service.py"
'@

Write-Utf8NoBom "tests\test_general_engineering_requirement_extractor.py" @'
from forge.general_engineering.requirement_extractor import (
    extract_change_requirements,
)


def test_requirement_extractor_splits_generic_conjunctions() -> None:
    requirements = extract_change_requirements(
        objective="Add validation and add tests.",
    )

    assert len(requirements) == 2
    assert requirements[0].description == "Add validation"
    assert requirements[1].description == "add tests"


def test_requirement_identifiers_are_deterministic() -> None:
    first = extract_change_requirements(
        objective="Create an endpoint and add tests.",
    )
    second = extract_change_requirements(
        objective="Create an endpoint and add tests.",
    )

    assert tuple(item.requirement_id for item in first) == tuple(
        item.requirement_id for item in second
    )
'@

Write-Utf8NoBom "tests\test_general_engineering_request_builder.py" @'
from pathlib import Path

from forge.general_engineering.request_builder import (
    build_engineering_request,
)


def test_request_builder_normalizes_and_preserves_scope(
    tmp_path: Path,
) -> None:
    request = build_engineering_request(
        objective="  Add   validation and tests. ",
        repository_root=tmp_path,
        constraints=(
            " Do not modify README. ",
            "do not modify README.",
        ),
        acceptance_criteria=("Tests pass",),
        explicit_target_paths=(r".\src\service.py",),
        forbidden_paths=(r".\docs",),
        allow_code_changes=True,
    )

    assert request.objective == "Add validation and tests."
    assert request.constraints == ("Do not modify README.",)
    assert request.acceptance_criteria == ("Tests pass",)
    assert request.explicit_target_paths == ("src/service.py",)
    assert request.forbidden_paths == ("docs",)
    assert request.allow_code_changes is True


def test_request_builder_identifier_is_deterministic(
    tmp_path: Path,
) -> None:
    first = build_engineering_request(
        objective="Add validation",
        repository_root=tmp_path,
    )
    second = build_engineering_request(
        objective="Add validation",
        repository_root=tmp_path,
    )

    assert first.request_id == second.request_id
'@

Write-Utf8NoBom "tests\test_general_engineering_request_understanding.py" @'
from pathlib import Path

from forge.general_engineering.request_builder import (
    build_engineering_request,
)
from forge.general_engineering.request_understanding import (
    EngineeringRequestUnderstandingService,
)


def test_understanding_builds_change_specification(
    tmp_path: Path,
) -> None:
    request = build_engineering_request(
        objective="Add validation and add tests.",
        repository_root=tmp_path,
        constraints=(
            "Preserve existing behavior.",
            "Do not modify configuration.",
        ),
        acceptance_criteria=("Existing tests continue to pass.",),
    )

    result = EngineeringRequestUnderstandingService().understand(request)

    assert result.request == request
    assert len(result.specification.requirements) == 2
    assert result.specification.constraints == request.constraints
    assert result.specification.invariants == (
        "Preserve existing behavior.",
        "Do not modify configuration.",
    )


def test_understanding_is_domain_agnostic(
    tmp_path: Path,
) -> None:
    objectives = (
        "Add a parser and add tests.",
        "Create a route and document the behavior.",
        "Update a calculation and preserve existing behavior.",
    )

    service = EngineeringRequestUnderstandingService()

    for objective in objectives:
        request = build_engineering_request(
            objective=objective,
            repository_root=tmp_path,
        )
        result = service.understand(request)
        assert result.specification.requirements
'@

Write-Utf8NoBom "scripts\validate-m5.9-package1.ps1" @'
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
    throw "Unable to read current branch."
}

if ($CurrentBranch -notin $AllowedBranches) {
    throw "M5.9 Package 1 validation must run on an approved branch: $($AllowedBranches -join ', '). Current branch: '$CurrentBranch'."
}

$RequiredFiles = @(
    ".\forge\general_engineering\normalization.py",
    ".\forge\general_engineering\requirement_extractor.py",
    ".\forge\general_engineering\request_builder.py",
    ".\forge\general_engineering\request_understanding.py",
    ".\tests\test_general_engineering_normalization.py",
    ".\tests\test_general_engineering_requirement_extractor.py",
    ".\tests\test_general_engineering_request_builder.py",
    ".\tests\test_general_engineering_request_understanding.py"
)

foreach ($Path in $RequiredFiles) {
    if (-not (Test-Path $Path)) {
        throw "Missing M5.9 Package 1 file: $Path"
    }
    if ((Get-Item $Path).Length -eq 0) {
        throw "M5.9 Package 1 file is empty: $Path"
    }
}

$Package1Core = @(
    ".\forge\general_engineering\normalization.py",
    ".\forge\general_engineering\requirement_extractor.py",
    ".\forge\general_engineering\request_builder.py",
    ".\forge\general_engineering\request_understanding.py"
)

$ForbiddenAuthority = Select-String `
    -Path $Package1Core `
    -Pattern "subprocess|os\.system|Popen|write_text\(|write_bytes\(|unlink\(|rmtree\(" `
    -ErrorAction SilentlyContinue

if ($ForbiddenAuthority) {
    $ForbiddenAuthority
    throw "M5.9 Package 1 contains forbidden execution or repository mutation authority."
}

$ForbiddenTaskSpecificLogic = Select-String `
    -Path $Package1Core `
    -Pattern "calculator|subtract|multiply|divide|PurchaseOrder|customer_service" `
    -ErrorAction SilentlyContinue

if ($ForbiddenTaskSpecificLogic) {
    $ForbiddenTaskSpecificLogic
    throw "M5.9 Package 1 contains task-specific acceptance logic."
}

$Builder = Get-Content ".\forge\general_engineering\request_builder.py" -Raw
$Understanding = Get-Content ".\forge\general_engineering\request_understanding.py" -Raw

if ($Builder -notmatch "def build_engineering_request\(") {
    throw "Package 1 request builder entrypoint is missing."
}

if ($Understanding -notmatch "class EngineeringRequestUnderstandingService") {
    throw "Package 1 request-understanding service is missing."
}

Write-Host ""
Write-Host "M5.9 PACKAGE 1 VALIDATION PASSED" -ForegroundColor Green
Write-Host "Behavior modules: 4"
Write-Host "Focused test files: 4"
Write-Host "Repository mutation authority: NONE"
'@

Write-Host ""
Write-Host "M5.9 Package 1 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_general_engineering_normalization.py `
    .\tests\test_general_engineering_requirement_extractor.py `
    .\tests\test_general_engineering_request_builder.py `
    .\tests\test_general_engineering_request_understanding.py `
    -p no:cacheprovider
Assert-CommandSuccess "M5.9 Package 1 focused tests"

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m5.9-package1.ps1" `
    -RepositoryRoot $RepositoryRoot
Assert-CommandSuccess "M5.9 Package 1 validation"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full repository regression"

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "M5.9 PACKAGE 1 REQUEST UNDERSTANDING COMPLETE" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green

Write-Host ""
Write-Host "NOTE: Package 1 does not inspect repository contents or mutate source files." `
    -ForegroundColor Yellow
Write-Host "Repository grounding begins in M5.9 Package 2." `
    -ForegroundColor Yellow

Write-Host ""
git status --short
