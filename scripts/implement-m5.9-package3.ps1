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
    throw "M5.9 Package 3 must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

$Prerequisites = @(
    ".\forge\general_engineering\models.py",
    ".\forge\general_engineering\request_understanding.py",
    ".\forge\general_engineering\repository_grounding.py"
)

foreach ($Path in $Prerequisites) {
    if (-not (Test-Path $Path)) {
        throw "Missing M5.9 Package 3 prerequisite: $Path"
    }
}

if (git status --porcelain) {
    throw "Working tree must be clean before M5.9 Package 3."
}

Write-Utf8NoBom "forge\general_engineering\planning_policy.py" @'
"""Planning policy for M5.9 Package 3."""

from __future__ import annotations

from dataclasses import dataclass

from forge.general_engineering.models import EngineeringRequest, RelevantFile
from forge.general_engineering.states import EngineeringRisk


@dataclass(frozen=True)
class PlanningDecision:
    selected_paths: tuple[str, ...]
    aggregate_risk: EngineeringRisk
    rationale: str


def select_planning_targets(
    request: EngineeringRequest,
    relevant_files: tuple[RelevantFile, ...],
    *,
    max_files: int = 20,
) -> PlanningDecision:
    """Select bounded, evidence-backed targets for a change plan."""
    available = {item.path: item for item in relevant_files}

    if request.explicit_target_paths:
        missing = [path for path in request.explicit_target_paths if path not in available]
        if missing:
            raise ValueError(
                "Explicit target paths are not repository-grounded: "
                + ", ".join(sorted(missing))
            )
        selected = tuple(request.explicit_target_paths)
    else:
        selected = tuple(item.path for item in relevant_files[:max_files])

    forbidden = set(request.forbidden_paths)
    blocked = [path for path in selected if any(
        path == item or path.startswith(f"{item.rstrip('/')}/")
        for item in forbidden
    )]
    if blocked:
        raise ValueError(
            "Selected targets violate request forbidden paths: "
            + ", ".join(sorted(blocked))
        )

    count = len(selected)
    if count <= 2:
        risk = EngineeringRisk.LOW
    elif count <= 5:
        risk = EngineeringRisk.MEDIUM
    elif count <= 10:
        risk = EngineeringRisk.HIGH
    else:
        risk = EngineeringRisk.CRITICAL

    return PlanningDecision(
        selected_paths=selected,
        aggregate_risk=risk,
        rationale=(
            f"Selected {count} evidence-backed repository path(s) within "
            "the approved request scope."
        ),
    )
'@

Write-Utf8NoBom "forge\general_engineering\validation_planner.py" @'
"""Validation planning for M5.9 Package 3."""

from __future__ import annotations

from forge.general_engineering.identifiers import validation_plan_identifier
from forge.general_engineering.models import EngineeringRequest, ValidationPlan


def build_validation_plan(
    request: EngineeringRequest,
    target_paths: tuple[str, ...],
) -> ValidationPlan:
    """Build a provider-independent validation intent.

    Package 3 defines validation capabilities only. It does not execute shell
    commands or decide repository-specific commands; execution arrives later.
    """
    capabilities = ["repository_tests", "static_analysis"]
    if any(path.casefold().startswith("tests/") for path in target_paths):
        capabilities.append("focused_tests")

    payload = {
        "request_id": request.request_id,
        "target_paths": target_paths,
        "capabilities": tuple(capabilities),
    }
    return ValidationPlan(
        validation_plan_id=validation_plan_identifier(payload),
        capabilities=tuple(capabilities),
    )
'@

Write-Utf8NoBom "forge\general_engineering\change_planner.py" @'
"""Repository-grounded deterministic change planning for M5.9 Package 3."""

from __future__ import annotations

from forge.general_engineering.identifiers import change_plan_identifier
from forge.general_engineering.models import (
    ChangePlan,
    ChangeSpecification,
    EngineeringContext,
    EngineeringRequest,
    FileChangePlan,
)
from forge.general_engineering.planning_policy import select_planning_targets
from forge.general_engineering.states import EditOperationType, EngineeringRisk
from forge.general_engineering.validation_planner import build_validation_plan


def _file_risk(path: str) -> EngineeringRisk:
    lowered = path.casefold()
    if lowered.startswith("tests/") or "/test" in lowered:
        return EngineeringRisk.LOW
    if any(token in lowered for token in ("migration", "schema", "security", "auth")):
        return EngineeringRisk.HIGH
    return EngineeringRisk.MEDIUM


def build_change_plan(
    *,
    request: EngineeringRequest,
    specification: ChangeSpecification,
    context: EngineeringContext,
) -> ChangePlan:
    """Create an evidence-backed, non-mutating ChangePlan."""
    if request.request_id != specification.request_id:
        raise ValueError("Specification does not belong to the engineering request.")
    if request.request_id != context.request_id:
        raise ValueError("Engineering context does not belong to the request.")

    decision = select_planning_targets(request, context.relevant_files)
    by_path = {item.path: item for item in context.relevant_files}
    file_changes: list[FileChangePlan] = []

    for path in decision.selected_paths:
        relevant = by_path[path]
        symbols = tuple(symbol.name for symbol in relevant.symbols)
        file_changes.append(
            FileChangePlan(
                path=path,
                rationale=relevant.rationale,
                evidence_ids=relevant.evidence_ids,
                relevant_symbols=symbols,
                intended_operations=(EditOperationType.REPLACE,),
                expected_effect=(
                    "Implement the approved requirements affecting this "
                    "repository-grounded target while preserving unrelated behavior."
                ),
                risk=_file_risk(path),
            )
        )

    validation_plan = build_validation_plan(request, decision.selected_paths)
    evidence_ids = tuple(
        sorted(
            {
                evidence_id
                for item in file_changes
                for evidence_id in item.evidence_ids
            }
        )
    )
    payload = {
        "request_id": request.request_id,
        "objective": request.objective,
        "requirements": tuple(
            requirement.requirement_id for requirement in specification.requirements
        ),
        "paths": decision.selected_paths,
        "evidence_ids": evidence_ids,
        "validation_plan_id": validation_plan.validation_plan_id,
    }

    return ChangePlan(
        plan_id=change_plan_identifier(payload),
        request_id=request.request_id,
        objective=request.objective,
        requirements=specification.requirements,
        file_changes=tuple(file_changes),
        validation_plan=validation_plan,
        expected_effect=(
            "Satisfy the normalized engineering requirements using only "
            "repository-grounded approved targets."
        ),
        aggregate_risk=decision.aggregate_risk,
        evidence_ids=evidence_ids,
    )
'@

Write-Utf8NoBom "forge\general_engineering\plan_validator.py" @'
"""Change-plan validation for M5.9 Package 3."""

from __future__ import annotations

from forge.general_engineering.errors import EngineeringContractError
from forge.general_engineering.models import (
    ChangePlan,
    ChangeSpecification,
    EngineeringContext,
    EngineeringRequest,
)


def validate_change_plan(
    *,
    request: EngineeringRequest,
    specification: ChangeSpecification,
    context: EngineeringContext,
    plan: ChangePlan,
) -> None:
    """Fail closed when a plan escapes request, requirements, or evidence."""
    if plan.request_id != request.request_id:
        raise EngineeringContractError("Plan belongs to another engineering request.")

    expected_requirements = {item.requirement_id for item in specification.requirements}
    planned_requirements = {item.requirement_id for item in plan.requirements}
    if expected_requirements != planned_requirements:
        raise EngineeringContractError(
            "Plan does not cover exactly the normalized requirements."
        )

    relevant_paths = {item.path for item in context.relevant_files}
    planned_paths = {item.path for item in plan.file_changes}
    if not planned_paths.issubset(relevant_paths):
        raise EngineeringContractError(
            "Plan includes targets not justified by repository grounding."
        )

    context_evidence = {item.evidence_id for item in context.evidence}
    if not set(plan.evidence_ids).issubset(context_evidence):
        raise EngineeringContractError(
            "Plan references evidence outside the engineering context."
        )

    forbidden = set(request.forbidden_paths)
    for path in planned_paths:
        if any(
            path == item or path.startswith(f"{item.rstrip('/')}/")
            for item in forbidden
        ):
            raise EngineeringContractError(
                f"Plan includes forbidden repository path: {path}"
            )
'@

Write-Utf8NoBom "forge\general_engineering\planning_service.py" @'
"""Planning orchestration for M5.9 Package 3."""

from __future__ import annotations

from dataclasses import dataclass

from forge.general_engineering.change_planner import build_change_plan
from forge.general_engineering.models import (
    ChangePlan,
    ChangeSpecification,
    EngineeringContext,
    EngineeringRequest,
)
from forge.general_engineering.plan_validator import validate_change_plan


@dataclass(frozen=True)
class EngineeringPlanningResult:
    plan: ChangePlan
    planned_file_count: int
    evidence_count: int


class EngineeringChangePlanningService:
    """Produce and validate a repository-grounded change plan."""

    def plan(
        self,
        *,
        request: EngineeringRequest,
        specification: ChangeSpecification,
        context: EngineeringContext,
    ) -> EngineeringPlanningResult:
        plan = build_change_plan(
            request=request,
            specification=specification,
            context=context,
        )
        validate_change_plan(
            request=request,
            specification=specification,
            context=context,
            plan=plan,
        )
        return EngineeringPlanningResult(
            plan=plan,
            planned_file_count=len(plan.file_changes),
            evidence_count=len(plan.evidence_ids),
        )


engineering_change_planning_service = EngineeringChangePlanningService()
'@

Write-Utf8NoBom "tests\test_general_engineering_planning_policy.py" @'
from pathlib import Path

import pytest

from forge.general_engineering.models import RelevantFile
from forge.general_engineering.planning_policy import select_planning_targets
from forge.general_engineering.request_builder import build_engineering_request
from forge.general_engineering.states import EngineeringRisk


def _relevant(path: str) -> RelevantFile:
    return RelevantFile(
        path=path,
        evidence_ids=(f"evidence-{path}",),
        rationale="repository evidence",
    )


def test_explicit_targets_must_be_grounded(tmp_path: Path) -> None:
    request = build_engineering_request(
        objective="Update service",
        repository_root=tmp_path,
        explicit_target_paths=("src/missing.py",),
    )
    with pytest.raises(ValueError, match="not repository-grounded"):
        select_planning_targets(request, (_relevant("src/service.py"),))


def test_small_plan_is_low_aggregate_risk(tmp_path: Path) -> None:
    request = build_engineering_request(
        objective="Update service",
        repository_root=tmp_path,
    )
    decision = select_planning_targets(
        request,
        (_relevant("src/service.py"), _relevant("tests/test_service.py")),
    )
    assert decision.aggregate_risk is EngineeringRisk.LOW
'@

Write-Utf8NoBom "tests\test_general_engineering_validation_planner.py" @'
from pathlib import Path

from forge.general_engineering.request_builder import build_engineering_request
from forge.general_engineering.validation_planner import build_validation_plan


def test_validation_plan_is_capability_based_and_deterministic(tmp_path: Path) -> None:
    request = build_engineering_request(
        objective="Update service and tests",
        repository_root=tmp_path,
    )
    first = build_validation_plan(request, ("src/service.py", "tests/test_service.py"))
    second = build_validation_plan(request, ("src/service.py", "tests/test_service.py"))

    assert first.validation_plan_id == second.validation_plan_id
    assert first.commands == ()
    assert "repository_tests" in first.capabilities
    assert "focused_tests" in first.capabilities
'@

Write-Utf8NoBom "tests\test_general_engineering_change_planner.py" @'
from pathlib import Path

from forge.general_engineering.context_builder import build_engineering_context
from forge.general_engineering.change_planner import build_change_plan
from forge.general_engineering.repository_scanner import ScannedRepositoryFile
from forge.general_engineering.relevance import RelevanceScore
from forge.general_engineering.request_builder import build_engineering_request
from forge.general_engineering.request_understanding import (
    EngineeringRequestUnderstandingService,
)


def test_change_plan_uses_only_grounded_targets(tmp_path: Path) -> None:
    request = build_engineering_request(
        objective="Update invoice approval and add tests",
        repository_root=tmp_path,
    )
    specification = EngineeringRequestUnderstandingService().understand(
        request
    ).specification
    source = ScannedRepositoryFile(
        path="src/invoice.py",
        size_bytes=10,
        suffix=".py",
        fingerprint="abc",
        content="pass\n",
    )
    context = build_engineering_context(
        request=request,
        files=(source,),
        symbol_map={source.path: ()},
        scores=(
            RelevanceScore(
                path=source.path,
                score=0.8,
                matched_terms=("invoice",),
                matched_symbols=(),
            ),
        ),
    )
    plan = build_change_plan(
        request=request,
        specification=specification,
        context=context,
    )

    assert tuple(item.path for item in plan.file_changes) == ("src/invoice.py",)
    assert plan.evidence_ids == context.relevant_files[0].evidence_ids
'@

Write-Utf8NoBom "tests\test_general_engineering_plan_validator.py" @'
from pathlib import Path

import pytest

from forge.general_engineering.errors import EngineeringContractError
from forge.general_engineering.models import (
    ChangePlan,
    ChangeRequirement,
    FileChangePlan,
    RelevantFile,
    RepositoryEvidence,
    ValidationPlan,
    EngineeringContext,
)
from forge.general_engineering.plan_validator import validate_change_plan
from forge.general_engineering.request_builder import build_engineering_request
from forge.general_engineering.request_understanding import EngineeringRequestUnderstandingService
from forge.general_engineering.states import EditOperationType, EngineeringRisk, EvidenceType


def test_validator_rejects_ungrounded_target(tmp_path: Path) -> None:
    request = build_engineering_request(objective="Update service", repository_root=tmp_path)
    specification = EngineeringRequestUnderstandingService().understand(request).specification
    evidence = RepositoryEvidence(
        evidence_id="evidence-1",
        path="src/service.py",
        evidence_type=EvidenceType.FILE,
        rationale="grounded",
        relevance=1.0,
    )
    context = EngineeringContext(
        request_id=request.request_id,
        relevant_files=(RelevantFile(path="src/service.py", evidence_ids=("evidence-1",), rationale="grounded"),),
        evidence=(evidence,),
    )
    plan = ChangePlan(
        plan_id="plan-1",
        request_id=request.request_id,
        objective=request.objective,
        requirements=specification.requirements,
        file_changes=(
            FileChangePlan(
                path="src/other.py",
                rationale="not grounded",
                evidence_ids=("evidence-1",),
                intended_operations=(EditOperationType.REPLACE,),
                expected_effect="change",
            ),
        ),
        validation_plan=ValidationPlan(validation_plan_id="validation-1", capabilities=("repository_tests",)),
        expected_effect="change",
        aggregate_risk=EngineeringRisk.LOW,
        evidence_ids=("evidence-1",),
    )

    with pytest.raises(EngineeringContractError, match="not justified"):
        validate_change_plan(
            request=request,
            specification=specification,
            context=context,
            plan=plan,
        )
'@

Write-Utf8NoBom "tests\test_general_engineering_planning_service.py" @'
from pathlib import Path

from forge.general_engineering.planning_service import EngineeringChangePlanningService
from forge.general_engineering.repository_grounding import RepositoryGroundingService
from forge.general_engineering.request_builder import build_engineering_request
from forge.general_engineering.request_understanding import EngineeringRequestUnderstandingService


def test_planning_service_runs_request_to_grounded_plan(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "shipment.py").write_text(
        "def schedule_shipment():\n    return True\n",
        encoding="utf-8",
    )
    request = build_engineering_request(
        objective="Update shipment scheduling",
        repository_root=tmp_path,
    )
    specification = EngineeringRequestUnderstandingService().understand(request).specification
    context = RepositoryGroundingService().ground(request).context

    result = EngineeringChangePlanningService().plan(
        request=request,
        specification=specification,
        context=context,
    )

    assert result.planned_file_count == 1
    assert result.plan.file_changes[0].path == "src/shipment.py"
    assert result.plan.validation_plan.capabilities
'@

Write-Utf8NoBom "scripts\validate-m5.9-package3.ps1" @'
[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

$AllowedBranches = @("feature/m5.9-general-engineering-agent", "main")
$CurrentBranch = git branch --show-current
if ($CurrentBranch -notin $AllowedBranches) {
    throw "M5.9 Package 3 validation must run on an approved branch. Current: '$CurrentBranch'."
}

$Required = @(
    ".\forge\general_engineering\planning_policy.py",
    ".\forge\general_engineering\validation_planner.py",
    ".\forge\general_engineering\change_planner.py",
    ".\forge\general_engineering\plan_validator.py",
    ".\forge\general_engineering\planning_service.py",
    ".\tests\test_general_engineering_planning_policy.py",
    ".\tests\test_general_engineering_validation_planner.py",
    ".\tests\test_general_engineering_change_planner.py",
    ".\tests\test_general_engineering_plan_validator.py",
    ".\tests\test_general_engineering_planning_service.py"
)

foreach ($Path in $Required) {
    if (-not (Test-Path $Path)) { throw "Missing Package 3 file: $Path" }
    if ((Get-Item $Path).Length -eq 0) { throw "Empty Package 3 file: $Path" }
}

$Core = $Required[0..4]
$ForbiddenAuthority = Select-String `
    -Path $Core `
    -Pattern "subprocess|os\.system|Popen|write_text\(|write_bytes\(|unlink\(|rmtree\(" `
    -ErrorAction SilentlyContinue

if ($ForbiddenAuthority) {
    $ForbiddenAuthority
    throw "Package 3 contains forbidden execution or repository mutation authority."
}

$TaskSpecific = Select-String `
    -Path $Core `
    -Pattern "calculator|subtract|multiply|divide|PurchaseOrder|customer_service|shipment_service" `
    -ErrorAction SilentlyContinue

if ($TaskSpecific) {
    $TaskSpecific
    throw "Package 3 contains acceptance-task-specific planning logic."
}

$Planner = Get-Content ".\forge\general_engineering\change_planner.py" -Raw
$Validator = Get-Content ".\forge\general_engineering\plan_validator.py" -Raw

if ($Planner -notmatch "def build_change_plan\(") {
    throw "Package 3 change-plan builder is missing."
}
if ($Validator -notmatch "def validate_change_plan\(") {
    throw "Package 3 plan validator is missing."
}

Write-Host ""
Write-Host "M5.9 PACKAGE 3 VALIDATION PASSED" -ForegroundColor Green
Write-Host "Planning modules: 5"
Write-Host "Focused test files: 5"
Write-Host "Repository mutation authority: NONE"
'@

Write-Host ""
Write-Host "M5.9 Package 3 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_general_engineering_planning_policy.py `
    .\tests\test_general_engineering_validation_planner.py `
    .\tests\test_general_engineering_change_planner.py `
    .\tests\test_general_engineering_plan_validator.py `
    .\tests\test_general_engineering_planning_service.py `
    -p no:cacheprovider
Assert-CommandSuccess "M5.9 Package 3 focused tests"

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m5.9-package3.ps1" `
    -RepositoryRoot $RepositoryRoot
Assert-CommandSuccess "M5.9 Package 3 validation"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full repository regression"

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "M5.9 PACKAGE 3 CHANGE PLANNING COMPLETE" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host "Package 3 plans and validates changes only; it does not mutate source files." -ForegroundColor Yellow
Write-Host ""
git status --short
