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
    throw "M5.9 Package 4 must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

$Prerequisites = @(
    ".\forge\general_engineering\models.py",
    ".\forge\general_engineering\protocols.py",
    ".\forge\general_engineering\planning_service.py",
    ".\forge\general_engineering\repository_grounding.py"
)

foreach ($Path in $Prerequisites) {
    if (-not (Test-Path $Path)) {
        throw "Missing M5.9 Package 4 prerequisite: $Path"
    }
}

if (git status --porcelain) {
    throw "Working tree must be clean before M5.9 Package 4."
}

Write-Utf8NoBom "forge\general_engineering\edit_synthesis_policy.py" @'
"""Safety policy for M5.9 Package 4 edit synthesis."""

from __future__ import annotations

from dataclasses import dataclass

from forge.general_engineering.models import ChangePlan, EngineeringRequest
from forge.general_engineering.states import EditOperationType


@dataclass(frozen=True)
class EditSynthesisDecision:
    allowed_paths: tuple[str, ...]
    allowed_requirement_ids: tuple[str, ...]
    allowed_operation_types: tuple[EditOperationType, ...]
    max_operations: int


def build_edit_synthesis_decision(
    request: EngineeringRequest,
    plan: ChangePlan,
    *,
    max_operations: int = 100,
) -> EditSynthesisDecision:
    """Derive the exact authority envelope for proposed edits."""
    if plan.request_id != request.request_id:
        raise ValueError("Change plan belongs to another engineering request.")

    allowed_paths = tuple(item.path for item in plan.file_changes)
    allowed_requirements = tuple(
        item.requirement_id for item in plan.requirements
    )
    allowed_operations = tuple(
        sorted(
            {
                operation
                for file_change in plan.file_changes
                for operation in file_change.intended_operations
            },
            key=lambda item: item.value,
        )
    )

    return EditSynthesisDecision(
        allowed_paths=allowed_paths,
        allowed_requirement_ids=allowed_requirements,
        allowed_operation_types=allowed_operations,
        max_operations=max_operations,
    )
'@

Write-Utf8NoBom "forge\general_engineering\edit_evidence.py" @'
"""Fingerprint and evidence helpers for M5.9 Package 4."""

from __future__ import annotations

from forge.general_engineering.models import EngineeringContext


def evidence_fingerprint_map(
    context: EngineeringContext,
) -> dict[str, str]:
    """Return one current source fingerprint per grounded repository path."""
    result: dict[str, str] = {}

    for evidence in context.evidence:
        if evidence.fingerprint:
            result[evidence.path] = evidence.fingerprint

    return result


def context_evidence_ids(context: EngineeringContext) -> frozenset[str]:
    return frozenset(item.evidence_id for item in context.evidence)
'@

Write-Utf8NoBom "forge\general_engineering\edit_proposal_validator.py" @'
"""Validation for provider-proposed edit change sets."""

from __future__ import annotations

from forge.general_engineering.errors import EngineeringContractError
from forge.general_engineering.edit_evidence import (
    context_evidence_ids,
    evidence_fingerprint_map,
)
from forge.general_engineering.edit_synthesis_policy import (
    build_edit_synthesis_decision,
)
from forge.general_engineering.models import (
    ChangePlan,
    EngineeringContext,
    EngineeringRequest,
    GeneratedChangeSet,
)
from forge.general_engineering.states import EditOperationType


_DESTRUCTIVE_OPERATIONS = frozenset(
    {
        EditOperationType.REPLACE,
        EditOperationType.DELETE,
        EditOperationType.RENAME,
    }
)


def validate_generated_change_set(
    *,
    request: EngineeringRequest,
    context: EngineeringContext,
    plan: ChangePlan,
    change_set: GeneratedChangeSet,
) -> None:
    """Fail closed if an edit proposal escapes the approved change plan."""
    if change_set.plan_id != plan.plan_id:
        raise EngineeringContractError(
            "Generated change set belongs to another change plan."
        )

    decision = build_edit_synthesis_decision(request, plan)
    if len(change_set.operations) > decision.max_operations:
        raise EngineeringContractError(
            "Generated change set exceeds the maximum operation count."
        )

    allowed_paths = set(decision.allowed_paths)
    allowed_requirements = set(decision.allowed_requirement_ids)
    allowed_operation_types = set(decision.allowed_operation_types)
    evidence_ids = context_evidence_ids(context)
    fingerprints = evidence_fingerprint_map(context)

    for operation in change_set.operations:
        if operation.target_path not in allowed_paths:
            raise EngineeringContractError(
                f"Edit target is outside approved plan scope: "
                f"{operation.target_path}"
            )

        if operation.originating_requirement_id not in allowed_requirements:
            raise EngineeringContractError(
                "Edit operation references a requirement outside the plan."
            )

        if operation.operation_type not in allowed_operation_types:
            raise EngineeringContractError(
                "Edit operation type is not authorized by the file plan."
            )

        if not set(operation.evidence_ids).issubset(evidence_ids):
            raise EngineeringContractError(
                "Edit operation references evidence outside the engineering context."
            )

        if operation.operation_type in _DESTRUCTIVE_OPERATIONS:
            expected = fingerprints.get(operation.target_path)
            if not expected:
                raise EngineeringContractError(
                    "Destructive edit lacks a grounded source fingerprint."
                )
            if operation.source_fingerprint != expected:
                raise EngineeringContractError(
                    f"Source fingerprint mismatch for {operation.target_path}."
                )

        if operation.operation_type is EditOperationType.RENAME:
            assert operation.rename_target_path is not None
            if operation.rename_target_path not in allowed_paths:
                raise EngineeringContractError(
                    "Rename destination is outside approved plan scope."
                )
'@

Write-Utf8NoBom "forge\general_engineering\change_set_factory.py" @'
"""Canonical GeneratedChangeSet construction for M5.9 Package 4."""

from __future__ import annotations

from forge.general_engineering.identifiers import change_set_identifier
from forge.general_engineering.models import (
    ChangePlan,
    EditOperation,
    GeneratedChangeSet,
)


def build_generated_change_set(
    *,
    plan: ChangePlan,
    operations: tuple[EditOperation, ...],
) -> GeneratedChangeSet:
    """Build a deterministic, canonically ordered GeneratedChangeSet."""
    ordered = tuple(
        sorted(
            operations,
            key=lambda item: (
                item.order,
                item.target_path,
                item.operation_id,
            ),
        )
    )
    evidence_ids = tuple(
        sorted(
            {
                evidence_id
                for operation in ordered
                for evidence_id in operation.evidence_ids
            }
        )
    )
    payload = {
        "plan_id": plan.plan_id,
        "operations": tuple(
            {
                "operation_id": operation.operation_id,
                "operation_type": operation.operation_type.value,
                "target_path": operation.target_path,
                "target_symbol": operation.target_symbol,
                "source_fingerprint": operation.source_fingerprint,
                "rename_target_path": operation.rename_target_path,
                "originating_requirement_id": (
                    operation.originating_requirement_id
                ),
                "order": operation.order,
            }
            for operation in ordered
        ),
        "evidence_ids": evidence_ids,
    }

    return GeneratedChangeSet(
        change_set_id=change_set_identifier(payload),
        plan_id=plan.plan_id,
        operations=ordered,
        evidence_ids=evidence_ids,
    )
'@

Write-Utf8NoBom "forge\general_engineering\edit_synthesis_service.py" @'
"""Provider-backed, non-mutating edit synthesis for M5.9 Package 4."""

from __future__ import annotations

from dataclasses import dataclass

from forge.general_engineering.change_set_factory import (
    build_generated_change_set,
)
from forge.general_engineering.edit_proposal_validator import (
    validate_generated_change_set,
)
from forge.general_engineering.models import (
    ChangePlan,
    EngineeringContext,
    EngineeringRequest,
    GeneratedChangeSet,
)
from forge.general_engineering.protocols import EngineeringProvider


@dataclass(frozen=True)
class EditSynthesisResult:
    change_set: GeneratedChangeSet
    operation_count: int
    affected_paths: tuple[str, ...]


class EngineeringEditSynthesisService:
    """Ask a reasoning provider for edit proposals, then validate them.

    The service exposes no file-writing or shell-execution capability.
    """

    def synthesize(
        self,
        *,
        provider: EngineeringProvider,
        request: EngineeringRequest,
        context: EngineeringContext,
        plan: ChangePlan,
    ) -> EditSynthesisResult:
        proposed = provider.synthesize_edits(
            request=request,
            context=context,
            plan=plan,
        )

        canonical = build_generated_change_set(
            plan=plan,
            operations=proposed.operations,
        )

        validate_generated_change_set(
            request=request,
            context=context,
            plan=plan,
            change_set=canonical,
        )

        return EditSynthesisResult(
            change_set=canonical,
            operation_count=len(canonical.operations),
            affected_paths=tuple(
                dict.fromkeys(
                    operation.target_path
                    for operation in canonical.operations
                )
            ),
        )


engineering_edit_synthesis_service = EngineeringEditSynthesisService()
'@

Write-Utf8NoBom "tests\test_general_engineering_edit_synthesis_policy.py" @'
from pathlib import Path

from forge.general_engineering.change_planner import build_change_plan
from forge.general_engineering.context_builder import build_engineering_context
from forge.general_engineering.edit_synthesis_policy import (
    build_edit_synthesis_decision,
)
from forge.general_engineering.relevance import RelevanceScore
from forge.general_engineering.repository_scanner import ScannedRepositoryFile
from forge.general_engineering.request_builder import build_engineering_request
from forge.general_engineering.request_understanding import (
    EngineeringRequestUnderstandingService,
)
from forge.general_engineering.states import EditOperationType


def test_edit_synthesis_decision_is_bounded_to_plan(tmp_path: Path) -> None:
    request = build_engineering_request(
        objective="Update invoice approval",
        repository_root=tmp_path,
    )
    specification = EngineeringRequestUnderstandingService().understand(
        request
    ).specification
    file = ScannedRepositoryFile(
        path="src/invoice.py",
        size_bytes=5,
        suffix=".py",
        fingerprint="abc",
        content="pass\n",
    )
    context = build_engineering_context(
        request=request,
        files=(file,),
        symbol_map={file.path: ()},
        scores=(
            RelevanceScore(
                path=file.path,
                score=1.0,
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

    decision = build_edit_synthesis_decision(request, plan)

    assert decision.allowed_paths == ("src/invoice.py",)
    assert decision.allowed_operation_types == (EditOperationType.REPLACE,)
'@

Write-Utf8NoBom "tests\test_general_engineering_edit_evidence.py" @'
from forge.general_engineering.edit_evidence import evidence_fingerprint_map
from forge.general_engineering.models import (
    EngineeringContext,
    RelevantFile,
    RepositoryEvidence,
)
from forge.general_engineering.states import EvidenceType


def test_evidence_fingerprint_map_uses_grounded_evidence() -> None:
    context = EngineeringContext(
        request_id="request-1",
        relevant_files=(
            RelevantFile(
                path="src/service.py",
                evidence_ids=("evidence-1",),
                rationale="grounded",
            ),
        ),
        evidence=(
            RepositoryEvidence(
                evidence_id="evidence-1",
                path="src/service.py",
                evidence_type=EvidenceType.FILE,
                rationale="grounded",
                relevance=1.0,
                fingerprint="fingerprint-1",
            ),
        ),
    )

    assert evidence_fingerprint_map(context) == {
        "src/service.py": "fingerprint-1"
    }
'@

Write-Utf8NoBom "tests\test_general_engineering_change_set_factory.py" @'
from forge.general_engineering.change_set_factory import (
    build_generated_change_set,
)
from forge.general_engineering.models import (
    ChangePlan,
    ChangeRequirement,
    EditOperation,
    FileChangePlan,
    ValidationPlan,
)
from forge.general_engineering.states import (
    EditOperationType,
    EngineeringRisk,
)


def _plan() -> ChangePlan:
    requirement = ChangeRequirement(
        requirement_id="requirement-1",
        description="Update behavior",
    )
    return ChangePlan(
        plan_id="plan-1",
        request_id="request-1",
        objective="Update behavior",
        requirements=(requirement,),
        file_changes=(
            FileChangePlan(
                path="src/service.py",
                rationale="grounded",
                evidence_ids=("evidence-1",),
                intended_operations=(EditOperationType.REPLACE,),
                expected_effect="update behavior",
            ),
        ),
        validation_plan=ValidationPlan(
            validation_plan_id="validation-1",
            capabilities=("repository_tests",),
        ),
        expected_effect="update behavior",
        aggregate_risk=EngineeringRisk.LOW,
        evidence_ids=("evidence-1",),
    )


def test_change_set_factory_is_deterministic() -> None:
    operation = EditOperation(
        operation_id="operation-1",
        operation_type=EditOperationType.REPLACE,
        target_path="src/service.py",
        source_fingerprint="fingerprint-1",
        proposed_content="VALUE = 2\n",
        rationale="Implement requirement",
        originating_requirement_id="requirement-1",
        evidence_ids=("evidence-1",),
    )

    first = build_generated_change_set(plan=_plan(), operations=(operation,))
    second = build_generated_change_set(plan=_plan(), operations=(operation,))

    assert first.change_set_id == second.change_set_id
    assert first.operations == second.operations
'@

Write-Utf8NoBom "tests\test_general_engineering_edit_proposal_validator.py" @'
from pathlib import Path

import pytest

from forge.general_engineering.change_planner import build_change_plan
from forge.general_engineering.context_builder import build_engineering_context
from forge.general_engineering.edit_proposal_validator import (
    validate_generated_change_set,
)
from forge.general_engineering.errors import EngineeringContractError
from forge.general_engineering.models import EditOperation, GeneratedChangeSet
from forge.general_engineering.relevance import RelevanceScore
from forge.general_engineering.repository_scanner import ScannedRepositoryFile
from forge.general_engineering.request_builder import build_engineering_request
from forge.general_engineering.request_understanding import (
    EngineeringRequestUnderstandingService,
)
from forge.general_engineering.states import EditOperationType


def test_validator_rejects_stale_fingerprint(tmp_path: Path) -> None:
    request = build_engineering_request(
        objective="Update invoice approval",
        repository_root=tmp_path,
    )
    specification = EngineeringRequestUnderstandingService().understand(
        request
    ).specification
    file = ScannedRepositoryFile(
        path="src/invoice.py",
        size_bytes=5,
        suffix=".py",
        fingerprint="current",
        content="pass\n",
    )
    context = build_engineering_context(
        request=request,
        files=(file,),
        symbol_map={file.path: ()},
        scores=(
            RelevanceScore(
                path=file.path,
                score=1.0,
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
    operation = EditOperation(
        operation_id="operation-1",
        operation_type=EditOperationType.REPLACE,
        target_path=file.path,
        source_fingerprint="stale",
        proposed_content="value = 2\n",
        rationale="Implement requirement",
        originating_requirement_id=plan.requirements[0].requirement_id,
        evidence_ids=plan.evidence_ids,
    )
    change_set = GeneratedChangeSet(
        change_set_id="change-set-1",
        plan_id=plan.plan_id,
        operations=(operation,),
        evidence_ids=plan.evidence_ids,
    )

    with pytest.raises(EngineeringContractError, match="fingerprint mismatch"):
        validate_generated_change_set(
            request=request,
            context=context,
            plan=plan,
            change_set=change_set,
        )
'@

Write-Utf8NoBom "tests\test_general_engineering_edit_synthesis_service.py" @'
from pathlib import Path

from forge.general_engineering.change_planner import build_change_plan
from forge.general_engineering.context_builder import build_engineering_context
from forge.general_engineering.edit_synthesis_service import (
    EngineeringEditSynthesisService,
)
from forge.general_engineering.models import (
    ChangePlan,
    ChangeSpecification,
    EditOperation,
    EngineeringContext,
    EngineeringRequest,
    GeneratedChangeSet,
    RepairProposal,
    ValidationOutcome,
)
from forge.general_engineering.relevance import RelevanceScore
from forge.general_engineering.repository_scanner import ScannedRepositoryFile
from forge.general_engineering.request_builder import build_engineering_request
from forge.general_engineering.request_understanding import (
    EngineeringRequestUnderstandingService,
)
from forge.general_engineering.states import EditOperationType


class FakeEngineeringProvider:
    def understand_request(
        self,
        request: EngineeringRequest,
        context: EngineeringContext,
    ) -> ChangeSpecification:
        raise NotImplementedError

    def propose_change_plan(
        self,
        request: EngineeringRequest,
        context: EngineeringContext,
        specification: ChangeSpecification,
    ) -> ChangePlan:
        raise NotImplementedError

    def synthesize_edits(
        self,
        request: EngineeringRequest,
        context: EngineeringContext,
        plan: ChangePlan,
    ) -> GeneratedChangeSet:
        evidence = context.evidence[0]
        operation = EditOperation(
            operation_id="operation-1",
            operation_type=EditOperationType.REPLACE,
            target_path=plan.file_changes[0].path,
            source_fingerprint=evidence.fingerprint,
            proposed_content="def schedule_delivery():\n    return True\n",
            rationale="Implement approved requirement",
            originating_requirement_id=plan.requirements[0].requirement_id,
            evidence_ids=plan.evidence_ids,
        )
        return GeneratedChangeSet(
            change_set_id="provider-change-set",
            plan_id=plan.plan_id,
            operations=(operation,),
            evidence_ids=plan.evidence_ids,
        )

    def propose_repair(
        self,
        request: EngineeringRequest,
        context: EngineeringContext,
        plan: ChangePlan,
        validation_outcome: ValidationOutcome,
        attempt_number: int,
    ) -> RepairProposal:
        raise NotImplementedError


def test_service_accepts_safe_provider_edit_proposal(tmp_path: Path) -> None:
    request = build_engineering_request(
        objective="Update delivery scheduling",
        repository_root=tmp_path,
    )
    specification = EngineeringRequestUnderstandingService().understand(
        request
    ).specification
    file = ScannedRepositoryFile(
        path="src/delivery.py",
        size_bytes=20,
        suffix=".py",
        fingerprint="fingerprint-1",
        content="def schedule_delivery():\n    return False\n",
    )
    context = build_engineering_context(
        request=request,
        files=(file,),
        symbol_map={file.path: ()},
        scores=(
            RelevanceScore(
                path=file.path,
                score=1.0,
                matched_terms=("delivery",),
                matched_symbols=(),
            ),
        ),
    )
    plan = build_change_plan(
        request=request,
        specification=specification,
        context=context,
    )

    result = EngineeringEditSynthesisService().synthesize(
        provider=FakeEngineeringProvider(),
        request=request,
        context=context,
        plan=plan,
    )

    assert result.operation_count == 1
    assert result.affected_paths == ("src/delivery.py",)
    assert result.change_set.operations[0].proposed_content is not None
'@

Write-Utf8NoBom "scripts\validate-m5.9-package4.ps1" @'
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
if ($CurrentBranch -notin $AllowedBranches) {
    throw "M5.9 Package 4 validation must run on an approved branch. Current: '$CurrentBranch'."
}

$Required = @(
    ".\forge\general_engineering\edit_synthesis_policy.py",
    ".\forge\general_engineering\edit_evidence.py",
    ".\forge\general_engineering\edit_proposal_validator.py",
    ".\forge\general_engineering\change_set_factory.py",
    ".\forge\general_engineering\edit_synthesis_service.py",
    ".\tests\test_general_engineering_edit_synthesis_policy.py",
    ".\tests\test_general_engineering_edit_evidence.py",
    ".\tests\test_general_engineering_change_set_factory.py",
    ".\tests\test_general_engineering_edit_proposal_validator.py",
    ".\tests\test_general_engineering_edit_synthesis_service.py"
)

foreach ($Path in $Required) {
    if (-not (Test-Path $Path)) {
        throw "Missing Package 4 file: $Path"
    }
    if ((Get-Item $Path).Length -eq 0) {
        throw "Empty Package 4 file: $Path"
    }
}

$Core = $Required[0..4]

$ForbiddenAuthority = Select-String `
    -Path $Core `
    -Pattern "subprocess|os\.system|Popen|write_text\(|write_bytes\(|unlink\(|rmtree\(" `
    -ErrorAction SilentlyContinue

if ($ForbiddenAuthority) {
    $ForbiddenAuthority
    throw "Package 4 contains forbidden execution or repository mutation authority."
}

$TaskSpecific = Select-String `
    -Path $Core `
    -Pattern "calculator|subtract|multiply|divide|PurchaseOrder|customer_service|shipment_service|delivery_service" `
    -ErrorAction SilentlyContinue

if ($TaskSpecific) {
    $TaskSpecific
    throw "Package 4 contains acceptance-task-specific synthesis logic."
}

$Service = Get-Content ".\forge\general_engineering\edit_synthesis_service.py" -Raw
$Validator = Get-Content ".\forge\general_engineering\edit_proposal_validator.py" -Raw

if ($Service -notmatch "provider\.synthesize_edits") {
    throw "Package 4 does not delegate reasoning to EngineeringProvider."
}

if ($Validator -notmatch "validate_generated_change_set") {
    throw "Package 4 change-set validator is missing."
}

Write-Host ""
Write-Host "M5.9 PACKAGE 4 VALIDATION PASSED" -ForegroundColor Green
Write-Host "Edit-synthesis modules: 5"
Write-Host "Focused test files: 5"
Write-Host "Repository mutation authority: NONE"
'@

Write-Host ""
Write-Host "M5.9 Package 4 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_general_engineering_edit_synthesis_policy.py `
    .\tests\test_general_engineering_edit_evidence.py `
    .\tests\test_general_engineering_change_set_factory.py `
    .\tests\test_general_engineering_edit_proposal_validator.py `
    .\tests\test_general_engineering_edit_synthesis_service.py `
    -p no:cacheprovider
Assert-CommandSuccess "M5.9 Package 4 focused tests"

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m5.9-package4.ps1" `
    -RepositoryRoot $RepositoryRoot
Assert-CommandSuccess "M5.9 Package 4 validation"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full repository regression"

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "M5.9 PACKAGE 4 GENERAL EDIT SYNTHESIS COMPLETE" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host "Package 4 proposes and validates edits only." -ForegroundColor Yellow
Write-Host "Actual repository mutation begins in Package 5." -ForegroundColor Yellow
Write-Host ""
git status --short
