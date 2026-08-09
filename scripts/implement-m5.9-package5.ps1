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
    throw "M5.9 Package 5 must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

$Prerequisites = @(
    ".\forge\general_engineering\edit_synthesis_service.py",
    ".\forge\safe_code_editing\service.py",
    ".\forge\safe_code_editing\models.py"
)

foreach ($Path in $Prerequisites) {
    if (-not (Test-Path $Path)) {
        throw "Missing M5.9 Package 5 prerequisite: $Path"
    }
}

if (git status --porcelain) {
    throw "Working tree must be clean before M5.9 Package 5."
}

Write-Utf8NoBom "forge\general_engineering\safe_edit_adapter.py" @'
"""Translate M5.9 edit proposals into existing Safe Code Editing requests."""

from __future__ import annotations

from pathlib import Path

from forge.general_engineering.errors import EngineeringContractError
from forge.general_engineering.models import (
    ChangePlan,
    EngineeringRequest,
    GeneratedChangeSet,
)
from forge.general_engineering.states import EditOperationType
from forge.safe_code_editing.models import (
    EditOperation as SafeEditOperation,
)
from forge.safe_code_editing.models import (
    EditOperationType as SafeEditOperationType,
)
from forge.safe_code_editing.models import FileEditPlan, SafeEditRequest


def _safe_operation_type(
    operation_type: EditOperationType,
) -> SafeEditOperationType:
    mapping = {
        EditOperationType.INSERT: SafeEditOperationType.INSERT,
        EditOperationType.REPLACE: SafeEditOperationType.REPLACE,
        EditOperationType.DELETE: SafeEditOperationType.DELETE,
    }
    try:
        return mapping[operation_type]
    except KeyError as exc:
        raise EngineeringContractError(
            f"Operation type is not executable by Safe Code Editing: "
            f"{operation_type.value}"
        ) from exc


def _build_safe_operation(
    *,
    repository_root: Path,
    operation,
) -> SafeEditOperation:
    path = repository_root / operation.target_path
    if not path.is_file():
        raise EngineeringContractError(
            f"Executable edit target does not exist: {operation.target_path}"
        )

    content = path.read_text(encoding="utf-8")
    expected_text = content

    if operation.operation_type is EditOperationType.INSERT:
        start_offset = len(content)
        end_offset = len(content)
        expected_text = ""
    else:
        start_offset = 0
        end_offset = len(content)

    replacement_text = operation.proposed_content or ""
    if operation.operation_type is EditOperationType.DELETE:
        replacement_text = ""

    return SafeEditOperation(
        operation_id=operation.operation_id,
        operation_type=_safe_operation_type(operation.operation_type),
        relative_path=operation.target_path,
        start_offset=start_offset,
        end_offset=end_offset,
        expected_text=expected_text,
        replacement_text=replacement_text,
        source_fingerprint=operation.source_fingerprint or "",
    )


def build_safe_edit_request(
    *,
    request: EngineeringRequest,
    plan: ChangePlan,
    change_set: GeneratedChangeSet,
    approved: bool,
    dry_run: bool,
) -> SafeEditRequest:
    """Build one bounded SafeEditRequest from a validated change set."""
    if change_set.plan_id != plan.plan_id:
        raise EngineeringContractError(
            "Generated change set does not belong to the supplied change plan."
        )

    repository_root = Path(request.repository_root).resolve()
    grouped: dict[str, list[SafeEditOperation]] = {}

    for operation in change_set.operations:
        grouped.setdefault(operation.target_path, []).append(
            _build_safe_operation(
                repository_root=repository_root,
                operation=operation,
            )
        )

    file_plans: list[FileEditPlan] = []
    for path, operations in sorted(grouped.items()):
        fingerprints = {
            operation.source_fingerprint for operation in operations
        }
        if len(fingerprints) != 1:
            raise EngineeringContractError(
                f"Conflicting source fingerprints for {path}."
            )
        source_fingerprint = next(iter(fingerprints))
        file_plans.append(
            FileEditPlan(
                relative_path=path,
                source_fingerprint=source_fingerprint,
                operations=tuple(operations),
            )
        )

    return SafeEditRequest(
        request_id=f"general-engineering-{change_set.change_set_id}",
        change_plan_id=plan.plan_id,
        repository_root=str(repository_root),
        file_plans=tuple(file_plans),
        dry_run=dry_run,
        approved=approved,
    )
'@

Write-Utf8NoBom "forge\general_engineering\execution_policy.py" @'
"""Execution policy for M5.9 Package 5."""

from __future__ import annotations

from dataclasses import dataclass

from forge.general_engineering.models import (
    ChangePlan,
    EngineeringRequest,
    GeneratedChangeSet,
)


@dataclass(frozen=True)
class ExecutionDecision:
    approved: bool
    dry_run: bool
    affected_paths: tuple[str, ...]


def authorize_execution(
    *,
    request: EngineeringRequest,
    plan: ChangePlan,
    change_set: GeneratedChangeSet,
    approved: bool,
    dry_run: bool,
) -> ExecutionDecision:
    if not request.allow_code_changes and not dry_run:
        raise PermissionError(
            "Engineering request does not authorize repository mutation."
        )

    if not dry_run and not approved:
        raise PermissionError(
            "Apply mode requires explicit edit approval."
        )

    planned_paths = {item.path for item in plan.file_changes}
    affected_paths = tuple(
        dict.fromkeys(
            operation.target_path for operation in change_set.operations
        )
    )

    if not set(affected_paths).issubset(planned_paths):
        raise PermissionError(
            "Generated change set exceeds approved plan scope."
        )

    return ExecutionDecision(
        approved=approved,
        dry_run=dry_run,
        affected_paths=affected_paths,
    )
'@

Write-Utf8NoBom "forge\general_engineering\execution_service.py" @'
"""Governed repository mutation for M5.9 Package 5."""

from __future__ import annotations

from dataclasses import dataclass

from forge.general_engineering.execution_policy import authorize_execution
from forge.general_engineering.models import (
    ChangePlan,
    EngineeringRequest,
    GeneratedChangeSet,
)
from forge.general_engineering.safe_edit_adapter import (
    build_safe_edit_request,
)
from forge.safe_code_editing.models import SafeEditReport
from forge.safe_code_editing.service import SafeCodeEditingService


@dataclass(frozen=True)
class EngineeringExecutionResult:
    report: SafeEditReport
    affected_paths: tuple[str, ...]


class EngineeringExecutionService:
    """Execute a validated change set through Safe Code Editing only."""

    def __init__(
        self,
        safe_editing: SafeCodeEditingService | None = None,
    ) -> None:
        self.safe_editing = safe_editing or SafeCodeEditingService()

    def execute(
        self,
        *,
        request: EngineeringRequest,
        plan: ChangePlan,
        change_set: GeneratedChangeSet,
        approved: bool,
        dry_run: bool = True,
    ) -> EngineeringExecutionResult:
        decision = authorize_execution(
            request=request,
            plan=plan,
            change_set=change_set,
            approved=approved,
            dry_run=dry_run,
        )

        safe_request = build_safe_edit_request(
            request=request,
            plan=plan,
            change_set=change_set,
            approved=decision.approved,
            dry_run=decision.dry_run,
        )
        report = self.safe_editing.execute(safe_request)

        return EngineeringExecutionResult(
            report=report,
            affected_paths=decision.affected_paths,
        )


engineering_execution_service = EngineeringExecutionService()
'@

Write-Utf8NoBom "forge\general_engineering\execution_evidence.py" @'
"""Execution evidence helpers for M5.9 Package 5."""

from __future__ import annotations

from dataclasses import dataclass

from forge.safe_code_editing.models import SafeEditReport


@dataclass(frozen=True)
class FileExecutionEvidence:
    path: str
    changed: bool
    original_fingerprint: str
    resulting_fingerprint: str


def summarize_execution_report(
    report: SafeEditReport,
) -> tuple[FileExecutionEvidence, ...]:
    return tuple(
        FileExecutionEvidence(
            path=result.relative_path,
            changed=result.changed,
            original_fingerprint=result.original_fingerprint,
            resulting_fingerprint=result.resulting_fingerprint,
        )
        for result in report.file_results
    )
'@

Write-Utf8NoBom "tests\test_general_engineering_execution_policy.py" @'
from pathlib import Path

import pytest

from forge.general_engineering.execution_policy import authorize_execution
from forge.general_engineering.models import (
    ChangePlan,
    ChangeRequirement,
    EditOperation,
    FileChangePlan,
    GeneratedChangeSet,
    ValidationPlan,
)
from forge.general_engineering.request_builder import build_engineering_request
from forge.general_engineering.states import (
    EditOperationType,
    EngineeringRisk,
)


def _plan_and_change_set(request_id: str) -> tuple[ChangePlan, GeneratedChangeSet]:
    requirement = ChangeRequirement(
        requirement_id="requirement-1",
        description="Update behavior",
    )
    plan = ChangePlan(
        plan_id="plan-1",
        request_id=request_id,
        objective="Update behavior",
        requirements=(requirement,),
        file_changes=(
            FileChangePlan(
                path="src/service.py",
                rationale="grounded",
                evidence_ids=("evidence-1",),
                intended_operations=(EditOperationType.REPLACE,),
                expected_effect="updated",
            ),
        ),
        validation_plan=ValidationPlan(
            validation_plan_id="validation-1",
            capabilities=("repository_tests",),
        ),
        expected_effect="updated",
        aggregate_risk=EngineeringRisk.LOW,
        evidence_ids=("evidence-1",),
    )
    operation = EditOperation(
        operation_id="operation-1",
        operation_type=EditOperationType.REPLACE,
        target_path="src/service.py",
        source_fingerprint="fingerprint-1",
        proposed_content="VALUE = 2\n",
        rationale="implement",
        originating_requirement_id="requirement-1",
        evidence_ids=("evidence-1",),
    )
    return plan, GeneratedChangeSet(
        change_set_id="change-set-1",
        plan_id=plan.plan_id,
        operations=(operation,),
        evidence_ids=("evidence-1",),
    )


def test_apply_requires_code_change_authority(tmp_path: Path) -> None:
    request = build_engineering_request(
        objective="Update behavior",
        repository_root=tmp_path,
        allow_code_changes=False,
    )
    plan, change_set = _plan_and_change_set(request.request_id)

    with pytest.raises(PermissionError, match="does not authorize"):
        authorize_execution(
            request=request,
            plan=plan,
            change_set=change_set,
            approved=True,
            dry_run=False,
        )


def test_dry_run_allowed_without_code_change_authority(tmp_path: Path) -> None:
    request = build_engineering_request(
        objective="Update behavior",
        repository_root=tmp_path,
        allow_code_changes=False,
    )
    plan, change_set = _plan_and_change_set(request.request_id)

    decision = authorize_execution(
        request=request,
        plan=plan,
        change_set=change_set,
        approved=False,
        dry_run=True,
    )

    assert decision.dry_run is True
'@

Write-Utf8NoBom "tests\test_general_engineering_safe_edit_adapter.py" @'
import hashlib
from pathlib import Path

from forge.general_engineering.models import (
    ChangePlan,
    ChangeRequirement,
    EditOperation,
    FileChangePlan,
    GeneratedChangeSet,
    ValidationPlan,
)
from forge.general_engineering.request_builder import build_engineering_request
from forge.general_engineering.safe_edit_adapter import build_safe_edit_request
from forge.general_engineering.states import (
    EditOperationType,
    EngineeringRisk,
)


def test_adapter_builds_safe_code_editing_request(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    target = tmp_path / "src" / "service.py"
    original = "VALUE = 1\n"
    target.write_text(original, encoding="utf-8")
    fingerprint = hashlib.sha256(original.encode("utf-8")).hexdigest()

    request = build_engineering_request(
        objective="Update behavior",
        repository_root=tmp_path,
        allow_code_changes=True,
    )
    requirement = ChangeRequirement(
        requirement_id="requirement-1",
        description="Update behavior",
    )
    plan = ChangePlan(
        plan_id="plan-1",
        request_id=request.request_id,
        objective=request.objective,
        requirements=(requirement,),
        file_changes=(
            FileChangePlan(
                path="src/service.py",
                rationale="grounded",
                evidence_ids=("evidence-1",),
                intended_operations=(EditOperationType.REPLACE,),
                expected_effect="updated",
            ),
        ),
        validation_plan=ValidationPlan(
            validation_plan_id="validation-1",
            capabilities=("repository_tests",),
        ),
        expected_effect="updated",
        aggregate_risk=EngineeringRisk.LOW,
        evidence_ids=("evidence-1",),
    )
    operation = EditOperation(
        operation_id="operation-1",
        operation_type=EditOperationType.REPLACE,
        target_path="src/service.py",
        source_fingerprint=fingerprint,
        proposed_content="VALUE = 2\n",
        rationale="implement",
        originating_requirement_id="requirement-1",
        evidence_ids=("evidence-1",),
    )
    change_set = GeneratedChangeSet(
        change_set_id="change-set-1",
        plan_id=plan.plan_id,
        operations=(operation,),
        evidence_ids=("evidence-1",),
    )

    safe = build_safe_edit_request(
        request=request,
        plan=plan,
        change_set=change_set,
        approved=True,
        dry_run=False,
    )

    assert safe.file_plans[0].relative_path == "src/service.py"
    assert safe.file_plans[0].operations[0].replacement_text == "VALUE = 2\n"
'@

Write-Utf8NoBom "tests\test_general_engineering_execution_service.py" @'
import hashlib
from pathlib import Path

from forge.general_engineering.execution_service import EngineeringExecutionService
from forge.general_engineering.models import (
    ChangePlan,
    ChangeRequirement,
    EditOperation,
    FileChangePlan,
    GeneratedChangeSet,
    ValidationPlan,
)
from forge.general_engineering.request_builder import build_engineering_request
from forge.general_engineering.states import (
    EditOperationType,
    EngineeringRisk,
)


def _fixture(tmp_path: Path):
    (tmp_path / "src").mkdir()
    target = tmp_path / "src" / "service.py"
    original = "VALUE = 1\n"
    target.write_text(original, encoding="utf-8")
    fingerprint = hashlib.sha256(original.encode("utf-8")).hexdigest()

    request = build_engineering_request(
        objective="Update service value",
        repository_root=tmp_path,
        allow_code_changes=True,
    )
    requirement = ChangeRequirement(
        requirement_id="requirement-1",
        description="Update service value",
    )
    plan = ChangePlan(
        plan_id="plan-1",
        request_id=request.request_id,
        objective=request.objective,
        requirements=(requirement,),
        file_changes=(
            FileChangePlan(
                path="src/service.py",
                rationale="grounded",
                evidence_ids=("evidence-1",),
                intended_operations=(EditOperationType.REPLACE,),
                expected_effect="updated",
            ),
        ),
        validation_plan=ValidationPlan(
            validation_plan_id="validation-1",
            capabilities=("repository_tests",),
        ),
        expected_effect="updated",
        aggregate_risk=EngineeringRisk.LOW,
        evidence_ids=("evidence-1",),
    )
    operation = EditOperation(
        operation_id="operation-1",
        operation_type=EditOperationType.REPLACE,
        target_path="src/service.py",
        source_fingerprint=fingerprint,
        proposed_content="VALUE = 2\n",
        rationale="implement",
        originating_requirement_id="requirement-1",
        evidence_ids=("evidence-1",),
    )
    change_set = GeneratedChangeSet(
        change_set_id="change-set-1",
        plan_id=plan.plan_id,
        operations=(operation,),
        evidence_ids=("evidence-1",),
    )
    return target, request, plan, change_set


def test_execution_service_dry_run_does_not_mutate(tmp_path: Path) -> None:
    target, request, plan, change_set = _fixture(tmp_path)

    result = EngineeringExecutionService().execute(
        request=request,
        plan=plan,
        change_set=change_set,
        approved=False,
        dry_run=True,
    )

    assert target.read_text(encoding="utf-8") == "VALUE = 1\n"
    assert result.report.dry_run is True


def test_execution_service_apply_mutates_through_safe_editing(tmp_path: Path) -> None:
    target, request, plan, change_set = _fixture(tmp_path)

    result = EngineeringExecutionService().execute(
        request=request,
        plan=plan,
        change_set=change_set,
        approved=True,
        dry_run=False,
    )

    assert target.read_text(encoding="utf-8") == "VALUE = 2\n"
    assert result.report.approved is True
'@

Write-Utf8NoBom "tests\test_general_engineering_execution_evidence.py" @'
from forge.general_engineering.execution_evidence import summarize_execution_report
from forge.safe_code_editing.models import FileEditResult, SafeEditReport


def test_execution_report_summary_preserves_fingerprints() -> None:
    report = SafeEditReport(
        request_id="request-1",
        transaction_id="transaction-1",
        dry_run=False,
        approved=True,
        file_results=(
            FileEditResult(
                relative_path="src/service.py",
                original_fingerprint="before",
                resulting_fingerprint="after",
                unified_diff="",
                changed=True,
            ),
        ),
    )

    evidence = summarize_execution_report(report)

    assert evidence[0].path == "src/service.py"
    assert evidence[0].original_fingerprint == "before"
    assert evidence[0].resulting_fingerprint == "after"
'@

Write-Utf8NoBom "scripts\validate-m5.9-package5.ps1" @'
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
    throw "M5.9 Package 5 validation must run on an approved branch. Current: '$CurrentBranch'."
}

$Required = @(
    ".\forge\general_engineering\safe_edit_adapter.py",
    ".\forge\general_engineering\execution_policy.py",
    ".\forge\general_engineering\execution_service.py",
    ".\forge\general_engineering\execution_evidence.py",
    ".\tests\test_general_engineering_execution_policy.py",
    ".\tests\test_general_engineering_safe_edit_adapter.py",
    ".\tests\test_general_engineering_execution_service.py",
    ".\tests\test_general_engineering_execution_evidence.py"
)

foreach ($Path in $Required) {
    if (-not (Test-Path $Path)) {
        throw "Missing Package 5 file: $Path"
    }
    if ((Get-Item $Path).Length -eq 0) {
        throw "Empty Package 5 file: $Path"
    }
}

$Service = Get-Content ".\forge\general_engineering\execution_service.py" -Raw

if ($Service -notmatch "SafeCodeEditingService") {
    throw "Package 5 must execute through Safe Code Editing."
}

$ForbiddenDirectMutation = Select-String `
    -Path @(
        ".\forge\general_engineering\execution_policy.py",
        ".\forge\general_engineering\execution_service.py",
        ".\forge\general_engineering\execution_evidence.py"
    ) `
    -Pattern "write_text\(|write_bytes\(|open\(.*['`"]w|unlink\(|rmtree\(" `
    -ErrorAction SilentlyContinue

if ($ForbiddenDirectMutation) {
    $ForbiddenDirectMutation
    throw "Package 5 bypasses Safe Code Editing with direct repository mutation."
}

Write-Host ""
Write-Host "M5.9 PACKAGE 5 VALIDATION PASSED" -ForegroundColor Green
Write-Host "Execution modules: 4"
Write-Host "Focused test files: 4"
Write-Host "Mutation path: SafeCodeEditingService ONLY"
'@

Write-Host ""
Write-Host "M5.9 Package 5 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_general_engineering_execution_policy.py `
    .\tests\test_general_engineering_safe_edit_adapter.py `
    .\tests\test_general_engineering_execution_service.py `
    .\tests\test_general_engineering_execution_evidence.py `
    -p no:cacheprovider
Assert-CommandSuccess "M5.9 Package 5 focused tests"

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m5.9-package5.ps1" `
    -RepositoryRoot $RepositoryRoot
Assert-CommandSuccess "M5.9 Package 5 validation"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full repository regression"

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "M5.9 PACKAGE 5 GOVERNED EXECUTION COMPLETE" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host "All repository mutation flows through SafeCodeEditingService." -ForegroundColor Yellow
Write-Host ""
git status --short
