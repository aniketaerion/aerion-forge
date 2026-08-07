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

$ExpectedBranch = "feature/m5.8-autonomous-agent-runtime"
$CurrentBranch = git branch --show-current
Assert-CommandSuccess "Read current branch"

if ($CurrentBranch -ne $ExpectedBranch) {
    throw "M5.8 Package 2 must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

Write-Utf8NoBom "forge\mission_runtime\memory_integration.py" @'
"""M5.5 memory integration for mission planning."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_memory.identifiers import memory_query_identifier
from forge.autonomous_memory.memory_service import AutonomousMemoryService
from forge.autonomous_memory.models import MemoryQuery
from forge.mission_runtime.context import MissionEngineeringContext
from forge.mission_runtime.models import MissionRequest


@dataclass(frozen=True, slots=True)
class MissionMemoryContext:
    query_id: str
    memory_ids: tuple[str, ...]
    evidence_references: tuple[str, ...]


@dataclass(slots=True)
class MissionMemoryIntegration:
    """Retrieve repository-scoped memory for one mission."""

    service: AutonomousMemoryService

    def retrieve(
        self,
        *,
        request: MissionRequest,
        context: MissionEngineeringContext,
    ) -> MissionMemoryContext:
        query_payload = {
            "repository_scope": context.workspace.repository_root,
            "capability_scope": context.capabilities.capability_ids,
            "requested_by": request.requested_by,
            "statement": request.statement,
        }
        query_id = memory_query_identifier(query_payload)
        query = MemoryQuery(
            query_id=query_id,
            repository_scope=context.workspace.repository_root,
            capability_scope=context.capabilities.capability_ids,
            requested_by=request.requested_by,
        )
        result = self.service.retrieve(
            query=query,
            query_text=request.statement,
        )

        memory_ids = tuple(
            match.memory_id
            for match in result.matches
        )

        evidence = tuple(
            f"memory:{memory_id}"
            for memory_id in memory_ids
        )

        return MissionMemoryContext(
            query_id=query_id,
            memory_ids=memory_ids,
            evidence_references=evidence,
        )
'@

Write-Utf8NoBom "forge\mission_runtime\planning_integration.py" @'
"""M5.6 planning integration for mission runtime."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_planning.context import PlanningContext
from forge.autonomous_planning.identifiers import (
    planning_request_identifier,
)
from forge.autonomous_planning.models import (
    PlanningPlan,
    PlanningRequest,
    PlanningValidationResult,
)
from forge.autonomous_planning.service import AutonomousPlanningService
from forge.autonomous_planning.states import PlanningIntent
from forge.mission_runtime.context import MissionEngineeringContext
from forge.mission_runtime.memory_integration import MissionMemoryContext
from forge.mission_runtime.models import MissionRequest


@dataclass(frozen=True, slots=True)
class MissionPlanningResult:
    planning_request: PlanningRequest
    plan: PlanningPlan
    validation: PlanningValidationResult
    memory_query_id: str


@dataclass(slots=True)
class MissionPlanningIntegration:
    """Translate a mission into the existing M5.6 planner."""

    service: AutonomousPlanningService

    def create_plan(
        self,
        *,
        request: MissionRequest,
        context: MissionEngineeringContext,
        memory: MissionMemoryContext,
    ) -> MissionPlanningResult:
        planning_request_id = planning_request_identifier(
            {
                "mission_request_id": request.request_id,
                "repository_root": context.workspace.repository_root,
                "objective": request.statement,
                "capabilities": context.capabilities.capability_ids,
            }
        )

        planning_request = PlanningRequest(
            request_id=planning_request_id,
            objective=request.statement,
            repository_root=context.workspace.repository_root,
            intent=PlanningIntent.IMPLEMENT_FEATURE,
            requested_capabilities=(
                context.capabilities.capability_ids
            ),
            created_by=request.requested_by,
        )

        planning_context = PlanningContext(
            repository_root=context.workspace.repository_root,
            repository_fingerprint="mission-runtime-context",
            known_capabilities=context.capabilities.capability_ids,
            architecture_constraints=(),
            operational_constraints=(),
            evidence_references=(
                *context.context_references,
                *memory.evidence_references,
            ),
        )

        generated, validation = self.service.create_plan(
            request=planning_request,
            context=planning_context,
        )

        return MissionPlanningResult(
            planning_request=planning_request,
            plan=generated.plan,
            validation=validation,
            memory_query_id=memory.query_id,
        )
'@

Write-Utf8NoBom "forge\mission_runtime\approval.py" @'
"""Mission-level approval orchestration."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_planning.models import PlanningPlan
from forge.autonomous_planning.states import PlanningRisk
from forge.mission_runtime.errors import MissionApprovalError
from forge.mission_runtime.models import MissionApproval
from forge.mission_runtime.policies import MissionRuntimePolicy
from forge.mission_runtime.states import (
    MissionApprovalDecision,
    MissionApprovalKind,
)


@dataclass(frozen=True, slots=True)
class MissionApprovalRequirement:
    required: bool
    rationale: tuple[str, ...]


def plan_approval_requirement(
    *,
    plan: PlanningPlan,
    policy: MissionRuntimePolicy,
) -> MissionApprovalRequirement:
    reasons: list[str] = []

    if plan.requires_approval:
        reasons.append(
            "Planning engine marked the plan as requiring approval."
        )

    if (
        policy.approvals.require_plan_approval_for_high_risk
        and plan.risk
        in {PlanningRisk.HIGH, PlanningRisk.CRITICAL}
    ):
        reasons.append(
            "High-risk mission plan requires human approval."
        )

    if (
        policy.approvals
        .require_plan_approval_for_destructive_changes
        and any(step.destructive for step in plan.steps)
    ):
        reasons.append(
            "Destructive plan step requires human approval."
        )

    return MissionApprovalRequirement(
        required=bool(reasons),
        rationale=tuple(reasons),
    )


def assert_plan_approved(
    *,
    requirement: MissionApprovalRequirement,
    approval: MissionApproval | None,
) -> None:
    if not requirement.required:
        return

    if approval is None:
        raise MissionApprovalError(
            "Mission plan requires approval before execution."
        )

    if approval.kind is not MissionApprovalKind.PLAN:
        raise MissionApprovalError(
            "Mission approval is not a plan approval."
        )

    if (
        approval.decision
        is not MissionApprovalDecision.APPROVED
    ):
        raise MissionApprovalError(
            "Mission plan approval has not been granted."
        )
'@

Write-Utf8NoBom "forge\mission_runtime\planning_orchestrator.py" @'
"""Mission planning orchestration for M5.8 Package 2."""

from __future__ import annotations

from dataclasses import dataclass

from forge.mission_runtime.approval import (
    MissionApprovalRequirement,
    plan_approval_requirement,
)
from forge.mission_runtime.context import MissionEngineeringContext
from forge.mission_runtime.memory_integration import (
    MissionMemoryContext,
    MissionMemoryIntegration,
)
from forge.mission_runtime.models import MissionRequest
from forge.mission_runtime.planning_integration import (
    MissionPlanningIntegration,
    MissionPlanningResult,
)
from forge.mission_runtime.policies import MissionRuntimePolicy


@dataclass(frozen=True, slots=True)
class MissionPlanPreparation:
    memory: MissionMemoryContext
    planning: MissionPlanningResult
    approval: MissionApprovalRequirement


@dataclass(slots=True)
class MissionPlanningOrchestrator:
    """Connect mission context, M5.5 memory, and M5.6 planning."""

    memory: MissionMemoryIntegration
    planning: MissionPlanningIntegration
    policy: MissionRuntimePolicy

    def prepare(
        self,
        *,
        request: MissionRequest,
        context: MissionEngineeringContext,
    ) -> MissionPlanPreparation:
        memory_context = self.memory.retrieve(
            request=request,
            context=context,
        )
        planning_result = self.planning.create_plan(
            request=request,
            context=context,
            memory=memory_context,
        )
        approval = plan_approval_requirement(
            plan=planning_result.plan,
            policy=self.policy,
        )

        return MissionPlanPreparation(
            memory=memory_context,
            planning=planning_result,
            approval=approval,
        )
'@

Write-Utf8NoBom "tests\test_mission_runtime_approval.py" @'
import pytest

from forge.autonomous_planning.models import (
    PlanningPlan,
    PlanningStep,
)
from forge.autonomous_planning.states import (
    ApprovalRequirement,
    PlanningRisk,
    StepKind,
)
from forge.mission_runtime.approval import (
    assert_plan_approved,
    plan_approval_requirement,
)
from forge.mission_runtime.errors import MissionApprovalError
from forge.mission_runtime.models import MissionApproval
from forge.mission_runtime.policies import MissionRuntimePolicy
from forge.mission_runtime.states import (
    MissionApprovalDecision,
    MissionApprovalKind,
)


def plan(
    *,
    risk: PlanningRisk = PlanningRisk.LOW,
    destructive: bool = False,
    requires_approval: bool = False,
) -> PlanningPlan:
    return PlanningPlan(
        plan_id="plan-1",
        request_id="request-1",
        summary="Test plan.",
        steps=(
            PlanningStep(
                step_id="step-1",
                sequence=1,
                name="Change",
                description="Perform approved change.",
                kind=StepKind.CODE_CHANGE,
                risk=risk,
                destructive=destructive,
                approval_requirement=(
                    ApprovalRequirement.PLAN
                    if destructive
                    else ApprovalRequirement.NONE
                ),
            ),
        ),
        risk=risk,
        requires_approval=requires_approval,
    )


def test_high_risk_plan_requires_approval() -> None:
    requirement = plan_approval_requirement(
        plan=plan(risk=PlanningRisk.HIGH),
        policy=MissionRuntimePolicy(),
    )

    assert requirement.required


def test_required_plan_without_approval_is_blocked() -> None:
    requirement = plan_approval_requirement(
        plan=plan(requires_approval=True),
        policy=MissionRuntimePolicy(),
    )

    with pytest.raises(MissionApprovalError):
        assert_plan_approved(
            requirement=requirement,
            approval=None,
        )


def test_approved_plan_passes_gate() -> None:
    requirement = plan_approval_requirement(
        plan=plan(requires_approval=True),
        policy=MissionRuntimePolicy(),
    )
    approval = MissionApproval(
        approval_id="approval-1",
        session_id="session-1",
        kind=MissionApprovalKind.PLAN,
        decision=MissionApprovalDecision.APPROVED,
        decided_by="reviewer",
        rationale="Approved.",
    )

    assert_plan_approved(
        requirement=requirement,
        approval=approval,
    )
'@

Write-Host ""
Write-Host "M5.8 Package 2 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check forge tests --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check forge tests
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_mission_runtime_approval.py `
    -p no:cacheprovider
Assert-CommandSuccess "M5.8 Package 2 focused tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full repository tests"

Write-Host ""
Write-Host "M5.8 PACKAGE 2 COMPLETE" -ForegroundColor Green

git status --short
