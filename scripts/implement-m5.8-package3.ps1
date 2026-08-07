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

$ExpectedBranch = "feature/m5.8-autonomous-agent-runtime"
$CurrentBranch = git branch --show-current
Assert-CommandSuccess "Read current branch"

if ($CurrentBranch -ne $ExpectedBranch) {
    throw "M5.8 Package 3 must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

Write-Utf8NoBom "forge\mission_runtime\execution_conversion.py" @'
"""Convert an approved M5.6 plan into an M5.7 execution run."""

from __future__ import annotations

from forge.autonomous_execution_v2.identifiers import (
    execution_request_identifier,
    execution_run_identifier,
    execution_step_identifier,
)
from forge.autonomous_execution_v2.models import (
    ExecutionDependency,
    ExecutionRequest,
    ExecutionRun,
    ExecutionStep,
)
from forge.autonomous_planning.models import PlanningPlan
from forge.mission_runtime.context import MissionEngineeringContext
from forge.mission_runtime.models import MissionRequest


def execution_request_from_plan(
    *,
    request: MissionRequest,
    context: MissionEngineeringContext,
    plan: PlanningPlan,
    repository_fingerprint: str,
) -> ExecutionRequest:
    request_id = execution_request_identifier(
        {
            "mission_request_id": request.request_id,
            "plan_id": plan.plan_id,
            "plan_version": plan.version,
            "repository_root": context.workspace.repository_root,
            "repository_fingerprint": repository_fingerprint,
        }
    )

    return ExecutionRequest(
        request_id=request_id,
        plan_id=plan.plan_id,
        plan_version=plan.version,
        repository_root=context.workspace.repository_root,
        repository_fingerprint=repository_fingerprint,
        requested_by=request.requested_by,
    )


def execution_run_from_plan(
    *,
    execution_request: ExecutionRequest,
    plan: PlanningPlan,
) -> ExecutionRun:
    execution_steps: list[ExecutionStep] = []
    planning_to_execution: dict[str, str] = {}

    for planning_step in plan.steps:
        step_id = execution_step_identifier(
            {
                "execution_request_id": execution_request.request_id,
                "planning_step_id": planning_step.step_id,
                "sequence": planning_step.sequence,
            }
        )
        planning_to_execution[planning_step.step_id] = step_id

        execution_steps.append(
            ExecutionStep(
                step_id=step_id,
                planning_step_id=planning_step.step_id,
                sequence=planning_step.sequence,
                name=planning_step.name,
                description=planning_step.description,
                required_tools=planning_step.required_tools,
                expected_outputs=planning_step.expected_outputs,
                acceptance_criteria=planning_step.acceptance_criteria,
                risk=planning_step.risk.value,
                requires_approval=(
                    planning_step.approval_requirement.value != "none"
                ),
                destructive=planning_step.destructive,
            )
        )

    dependencies = tuple(
        ExecutionDependency(
            dependency_id=dependency.dependency_id,
            source_step_id=planning_to_execution[
                dependency.source_step_id
            ],
            target_step_id=planning_to_execution[
                dependency.target_step_id
            ],
            rationale=dependency.rationale,
        )
        for dependency in plan.dependencies
    )

    run_id = execution_run_identifier(
        {
            "execution_request_id": execution_request.request_id,
            "plan_id": plan.plan_id,
            "plan_version": plan.version,
            "steps": tuple(
                step.step_id
                for step in execution_steps
            ),
        }
    )

    return ExecutionRun(
        run_id=run_id,
        request_id=execution_request.request_id,
        plan_id=plan.plan_id,
        plan_version=plan.version,
        repository_root=execution_request.repository_root,
        repository_fingerprint=(
            execution_request.repository_fingerprint
        ),
        steps=tuple(execution_steps),
        dependencies=dependencies,
    )
'@

Write-Utf8NoBom "forge\mission_runtime\execution_authority.py" @'
"""Translate mission approval into M5.7 execution authority."""

from __future__ import annotations

from forge.autonomous_execution_v2.authority import ExecutionAuthority
from forge.autonomous_planning.models import PlanningPlan
from forge.mission_runtime.context import MissionEngineeringContext
from forge.mission_runtime.models import (
    MissionApproval,
    MissionRequest,
)
from forge.mission_runtime.states import MissionApprovalDecision


def execution_authority_for_plan(
    *,
    request: MissionRequest,
    context: MissionEngineeringContext,
    plan: PlanningPlan,
    approval: MissionApproval | None,
) -> ExecutionAuthority:
    approved = (
        approval is not None
        and approval.decision
        is MissionApprovalDecision.APPROVED
    )

    tools = tuple(
        sorted(
            {
                tool
                for step in plan.steps
                for tool in step.required_tools
            }
        )
    )

    return ExecutionAuthority(
        subject=request.requested_by,
        repository_root=context.workspace.repository_root,
        permitted_tools=tools,
        permitted_capabilities=(
            context.capabilities.capability_ids
        ),
        high_risk_approved=approved,
        destructive_approved=approved,
    )
'@

Write-Utf8NoBom "forge\mission_runtime\verification.py" @'
"""Mission-level verification result aggregation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MissionVerificationResult:
    passed: bool
    references: tuple[str, ...]
    summary: str

    def __post_init__(self) -> None:
        if not self.summary.strip():
            raise ValueError(
                "Verification summary cannot be empty."
            )

        if self.passed and not self.references:
            raise ValueError(
                "Passed verification requires evidence references."
            )
'@

Write-Utf8NoBom "forge\mission_runtime\execution_orchestrator.py" @'
"""M5.8 orchestration over the existing M5.7 execution service."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_execution_v2.authority import ExecutionAuthority
from forge.autonomous_execution_v2.models import ExecutionRun
from forge.autonomous_execution_v2.service import (
    AutonomousExecutionService,
)
from forge.autonomous_execution_v2.step_execution import (
    StepToolInvocation,
)


@dataclass(frozen=True, slots=True)
class MissionExecutionResult:
    run: ExecutionRun
    executed_step_ids: tuple[str, ...]
    evidence_references: tuple[str, ...]


@dataclass(slots=True)
class MissionExecutionOrchestrator:
    """Register and advance M5.7 execution runs."""

    service: AutonomousExecutionService

    def register(
        self,
        run: ExecutionRun,
    ) -> None:
        self.service.register_run(run)

    def execute_next(
        self,
        *,
        run_id: str,
        invocations_by_step: dict[
            str,
            tuple[StepToolInvocation, ...],
        ],
        authority: ExecutionAuthority,
        attempt_number: int = 1,
    ) -> MissionExecutionResult:
        result = self.service.execute_next(
            run_id=run_id,
            invocations_by_step=invocations_by_step,
            authority=authority,
            attempt_number=attempt_number,
        )

        evidence_references = tuple(
            f"execution-evidence:{item.evidence_id}"
            for item in result.outcome.evidence
        )

        return MissionExecutionResult(
            run=result.run,
            executed_step_ids=(
                result.outcome.step_id,
            ),
            evidence_references=evidence_references,
        )
'@

Write-Utf8NoBom "forge\mission_runtime\execution_preparation.py" @'
"""Prepare an approved mission plan for M5.7 execution."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_execution_v2.authority import ExecutionAuthority
from forge.autonomous_execution_v2.models import (
    ExecutionRequest,
    ExecutionRun,
)
from forge.autonomous_planning.models import PlanningPlan
from forge.mission_runtime.approval import (
    MissionApprovalRequirement,
    assert_plan_approved,
)
from forge.mission_runtime.context import MissionEngineeringContext
from forge.mission_runtime.execution_authority import (
    execution_authority_for_plan,
)
from forge.mission_runtime.execution_conversion import (
    execution_request_from_plan,
    execution_run_from_plan,
)
from forge.mission_runtime.models import (
    MissionApproval,
    MissionRequest,
)


@dataclass(frozen=True, slots=True)
class MissionExecutionPreparation:
    execution_request: ExecutionRequest
    run: ExecutionRun
    authority: ExecutionAuthority


def prepare_execution(
    *,
    request: MissionRequest,
    context: MissionEngineeringContext,
    plan: PlanningPlan,
    approval_requirement: MissionApprovalRequirement,
    approval: MissionApproval | None,
    repository_fingerprint: str,
) -> MissionExecutionPreparation:
    assert_plan_approved(
        requirement=approval_requirement,
        approval=approval,
    )

    execution_request = execution_request_from_plan(
        request=request,
        context=context,
        plan=plan,
        repository_fingerprint=repository_fingerprint,
    )

    run = execution_run_from_plan(
        execution_request=execution_request,
        plan=plan,
    )

    authority = execution_authority_for_plan(
        request=request,
        context=context,
        plan=plan,
        approval=approval,
    )

    return MissionExecutionPreparation(
        execution_request=execution_request,
        run=run,
        authority=authority,
    )
'@

Write-Utf8NoBom "tests\test_mission_runtime_execution_conversion.py" @'
from forge.autonomous_planning.models import (
    PlanningPlan,
    PlanningStep,
)
from forge.autonomous_planning.states import (
    PlanningRisk,
    StepKind,
)
from forge.mission_runtime.context import (
    MissionCapabilitySelection,
    MissionEngineeringContext,
    MissionTechnologyContext,
    MissionWorkspaceContext,
)
from forge.mission_runtime.execution_conversion import (
    execution_request_from_plan,
    execution_run_from_plan,
)
from forge.mission_runtime.models import MissionRequest
from forge.workspace.models import (
    ProjectType,
    WorkspaceHealth,
    WorkspaceStatus,
)


def context() -> MissionEngineeringContext:
    return MissionEngineeringContext(
        workspace=MissionWorkspaceContext(
            workspace_id="workspace-1",
            workspace_name="ERP",
            repository_root="repository",
            status=WorkspaceStatus.READY,
            health=WorkspaceHealth.HEALTHY,
            technology=MissionTechnologyContext(
                project_type=ProjectType.ERP,
            ),
        ),
        capabilities=MissionCapabilitySelection(
            capability_ids=("safe-code-editing",),
        ),
    )


def plan() -> PlanningPlan:
    return PlanningPlan(
        plan_id="plan-1",
        request_id="planning-request-1",
        summary="Implement approved change.",
        steps=(
            PlanningStep(
                step_id="planning-step-1",
                sequence=1,
                name="Edit code",
                description="Apply approved code change.",
                kind=StepKind.CODE_CHANGE,
                required_tools=("filesystem",),
                risk=PlanningRisk.LOW,
            ),
        ),
    )


def test_plan_converts_to_execution_run() -> None:
    request = MissionRequest(
        request_id="mission-request-1",
        workspace_id="workspace-1",
        repository_root="repository",
        statement="Implement approved change.",
        requested_by="Aerion",
    )

    execution_request = execution_request_from_plan(
        request=request,
        context=context(),
        plan=plan(),
        repository_fingerprint="fingerprint-1",
    )
    run = execution_run_from_plan(
        execution_request=execution_request,
        plan=plan(),
    )

    assert run.plan_id == "plan-1"
    assert run.repository_fingerprint == "fingerprint-1"
    assert len(run.steps) == 1
    assert run.steps[0].planning_step_id == "planning-step-1"
    assert run.steps[0].required_tools == ("filesystem",)
'@

Write-Utf8NoBom "tests\test_mission_runtime_execution_authority.py" @'
from forge.autonomous_planning.models import (
    PlanningPlan,
    PlanningStep,
)
from forge.autonomous_planning.states import (
    PlanningRisk,
    StepKind,
)
from forge.mission_runtime.context import (
    MissionCapabilitySelection,
    MissionEngineeringContext,
    MissionTechnologyContext,
    MissionWorkspaceContext,
)
from forge.mission_runtime.execution_authority import (
    execution_authority_for_plan,
)
from forge.mission_runtime.models import (
    MissionApproval,
    MissionRequest,
)
from forge.mission_runtime.states import (
    MissionApprovalDecision,
    MissionApprovalKind,
)
from forge.workspace.models import (
    ProjectType,
    WorkspaceHealth,
    WorkspaceStatus,
)


def test_approved_plan_grants_explicit_authority() -> None:
    context = MissionEngineeringContext(
        workspace=MissionWorkspaceContext(
            workspace_id="workspace-1",
            workspace_name="ERP",
            repository_root="repository",
            status=WorkspaceStatus.READY,
            health=WorkspaceHealth.HEALTHY,
            technology=MissionTechnologyContext(
                project_type=ProjectType.ERP,
            ),
        ),
        capabilities=MissionCapabilitySelection(
            capability_ids=("safe-code-editing",),
        ),
    )
    request = MissionRequest(
        request_id="request-1",
        workspace_id="workspace-1",
        repository_root="repository",
        statement="Implement approved change.",
        requested_by="Aerion",
    )
    plan = PlanningPlan(
        plan_id="plan-1",
        request_id="planning-request-1",
        summary="Approved plan.",
        steps=(
            PlanningStep(
                step_id="step-1",
                sequence=1,
                name="Edit",
                description="Edit approved source.",
                kind=StepKind.CODE_CHANGE,
                required_tools=("filesystem",),
                risk=PlanningRisk.HIGH,
            ),
        ),
    )
    approval = MissionApproval(
        approval_id="approval-1",
        session_id="session-1",
        kind=MissionApprovalKind.PLAN,
        decision=MissionApprovalDecision.APPROVED,
        decided_by="reviewer",
        rationale="Approved.",
    )

    authority = execution_authority_for_plan(
        request=request,
        context=context,
        plan=plan,
        approval=approval,
    )

    assert authority.subject == "Aerion"
    assert authority.permitted_tools == ("filesystem",)
    assert authority.high_risk_approved
'@

Write-Utf8NoBom "tests\test_mission_runtime_verification.py" @'
import pytest

from forge.mission_runtime.verification import (
    MissionVerificationResult,
)


def test_passed_verification_requires_evidence() -> None:
    with pytest.raises(ValueError):
        MissionVerificationResult(
            passed=True,
            references=(),
            summary="Validation passed.",
        )


def test_verification_accepts_evidence() -> None:
    result = MissionVerificationResult(
        passed=True,
        references=("pytest:1741-passed",),
        summary="All required validation passed.",
    )

    assert result.passed
'@

Write-Host ""
Write-Host "M5.8 Package 3 files written. Running validation..." `
    -ForegroundColor Cyan

python -m ruff check forge tests --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check forge tests
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_mission_runtime_execution_conversion.py `
    .\tests\test_mission_runtime_execution_authority.py `
    .\tests\test_mission_runtime_verification.py `
    -p no:cacheprovider
Assert-CommandSuccess "M5.8 Package 3 focused tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full repository tests"

Write-Host ""
Write-Host "M5.8 PACKAGE 3 COMPLETE" -ForegroundColor Green

git status --short