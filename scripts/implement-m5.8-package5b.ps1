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

$ExpectedBranch = "feature/m5.8-package5-production-runtime-cli"
$Branch = git branch --show-current
Assert-CommandSuccess "Read current branch"
if ($Branch -ne $ExpectedBranch) {
    throw "Package 5B must run on '$ExpectedBranch'. Current branch: '$Branch'."
}

$Dirty = @(git status --porcelain)
$UnexpectedDirty = @(
    $Dirty | Where-Object {
        $_ -notmatch '^\?\? scripts/implement-m5\.8-package5b\.ps1$'
    }
)
if ($UnexpectedDirty.Count -gt 0) {
    Write-Host "Unexpected working-tree changes:" -ForegroundColor Red
    $UnexpectedDirty | ForEach-Object { Write-Host $_ -ForegroundColor Red }
    throw "Working tree must otherwise be clean before M5.8 Package 5B."
}

Write-Utf8NoBom "forge\agent_runtime\production_executors.py" @'
"""Bounded production executors for M5.8 Package 5B.

This module proves the real Safe Code Editing and Build Verification path for
an explicitly bounded function-addition mission. Unsupported edit grammars
fail closed instead of being fabricated.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from forge.agent_runtime.adapters.base import failed_result, succeeded_result
from forge.agent_runtime.models import AgentSession, AgentStage, AgentStageResult
from forge.build_verification.models import (
    BuildVerificationPolicy,
    ReleaseDecision,
    VerificationTool,
)
from forge.build_verification.service import BuildVerificationService
from forge.safe_code_editing.loader import load_text_file
from forge.safe_code_editing.models import (
    EditOperation,
    EditOperationType,
    FileEditPlan,
    SafeEditRequest,
)
from forge.safe_code_editing.policies import SafeEditPolicy
from forge.safe_code_editing.service import SafeCodeEditingService

_FUNCTION_ADD_RE = re.compile(
    r"^\s*Add\s+"
    r"(?P<name>[A-Za-z_]\w*)"
    r"\((?P<params>[^)]*)\)"
    r"\s*->\s*(?P<return_type>[A-Za-z_][A-Za-z0-9_\[\], .|]*)"
    r"\s+to\s+"
    r"(?P<path>[A-Za-z0-9_./\\-]+)"
    r"\s+and\s+change\s+nothing\s+else\.?\s*$",
    re.IGNORECASE,
)


def _stable_id(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]
    return f"{prefix}-{digest}"


def _parse_parameter_names(params: str) -> tuple[str, ...]:
    names: list[str] = []
    for item in params.split(","):
        candidate = item.strip()
        if not candidate:
            continue
        name = candidate.split(":", 1)[0].strip()
        if not re.fullmatch(r"[A-Za-z_]\w*", name):
            raise ValueError(f"unsupported parameter declaration: {candidate}")
        names.append(name)
    return tuple(names)


def _bounded_function_change(objective: str) -> tuple[str, str, str]:
    match = _FUNCTION_ADD_RE.fullmatch(objective)
    if match is None:
        raise ValueError(
            "Package 5B accepts only 'Add name(args) -> type to path.py "
            "and change nothing else.'"
        )

    name = match.group("name")
    params = match.group("params").strip()
    return_type = match.group("return_type").strip()
    relative_path = match.group("path").replace("\\", "/")
    parameter_names = _parse_parameter_names(params)
    if len(parameter_names) != 2:
        raise ValueError("bounded arithmetic acceptance requires two parameters")

    left, right = parameter_names
    operators = {
        "add": "+",
        "subtract": "-",
        "multiply": "*",
        "divide": "/",
    }
    operator = operators.get(name.lower())
    if operator is None:
        raise ValueError(
            "Package 5B acceptance supports add/subtract/multiply/divide only"
        )

    rendered = (
        f"def {name}({params}) -> {return_type}:\n"
        f"    return {left} {operator} {right}\n"
    )
    return relative_path, name, rendered


def planning_executor(
    repository_root: Path,
    session: AgentSession,
    stage: AgentStage,
    context: Mapping[str, Any],
) -> AgentStageResult:
    del context
    try:
        relative_path, function_name, _ = _bounded_function_change(
            session.request.objective.objective
        )
        if not (repository_root / relative_path).is_file():
            return failed_result(stage, f"target does not exist: {relative_path}")
        return succeeded_result(
            stage,
            f"bounded plan prepared for {relative_path}",
            evidence={"target_path": relative_path, "function_name": function_name},
        )
    except ValueError as exc:
        return failed_result(stage, f"planning rejected objective: {exc}")


def impact_executor(
    repository_root: Path,
    session: AgentSession,
    stage: AgentStage,
    context: Mapping[str, Any],
) -> AgentStageResult:
    del context
    try:
        relative_path, function_name, _ = _bounded_function_change(
            session.request.objective.objective
        )
        content = (repository_root / relative_path).read_text(encoding="utf-8-sig")
        if re.search(rf"(?m)^\s*def\s+{re.escape(function_name)}\s*\(", content):
            return failed_result(stage, f"function already exists: {function_name}")
        return succeeded_result(
            stage,
            "impact analysis restricted the mission to one source file",
            evidence={"target_path": relative_path, "scope": "single_file"},
        )
    except (OSError, ValueError) as exc:
        return failed_result(stage, f"impact analysis failed: {exc}")


def change_planning_executor(
    repository_root: Path,
    session: AgentSession,
    stage: AgentStage,
    context: Mapping[str, Any],
) -> AgentStageResult:
    del context
    try:
        relative_path, _, rendered = _bounded_function_change(
            session.request.objective.objective
        )
        loaded = load_text_file(repository_root, relative_path, SafeEditPolicy())
        return succeeded_result(
            stage,
            "safe edit plan validated against source fingerprint",
            evidence={
                "target_path": relative_path,
                "source_fingerprint": loaded.fingerprint,
                "planned_insert_bytes": str(len(rendered.encode("utf-8"))),
            },
        )
    except Exception as exc:
        return failed_result(stage, f"safe-change planning failed: {exc}")


def editing_executor(
    repository_root: Path,
    session: AgentSession,
    stage: AgentStage,
    context: Mapping[str, Any],
) -> AgentStageResult:
    del context
    try:
        relative_path, function_name, rendered = _bounded_function_change(
            session.request.objective.objective
        )
        policy = SafeEditPolicy()
        loaded = load_text_file(repository_root, relative_path, policy)

        separator = ""
        if loaded.content:
            if not loaded.content.endswith(("\n", "\r")):
                separator = loaded.newline * 2
            elif not loaded.content.endswith(loaded.newline * 2):
                separator = loaded.newline
        insertion = separator + rendered.replace("\n", loaded.newline)

        operation = EditOperation(
            operation_id=_stable_id(
                "edit-operation",
                session.session_id + relative_path + loaded.fingerprint + insertion,
            ),
            operation_type=EditOperationType.INSERT,
            relative_path=relative_path,
            start_offset=len(loaded.content),
            end_offset=len(loaded.content),
            replacement_text=insertion,
            source_fingerprint=loaded.fingerprint,
        )
        file_plan = FileEditPlan(
            relative_path=relative_path,
            source_fingerprint=loaded.fingerprint,
            operations=(operation,),
        )
        request = SafeEditRequest(
            request_id=_stable_id("safe-edit-request", session.session_id + operation.operation_id),
            change_plan_id=_stable_id("change-plan", session.session_id + relative_path),
            repository_root=str(repository_root),
            file_plans=(file_plan,),
            dry_run=False,
            approved=True,
        )

        report = SafeCodeEditingService(policy).execute(request)
        changed = tuple(item.relative_path for item in report.file_results if item.changed)
        if changed != (relative_path,):
            return failed_result(
                stage,
                "safe editor did not produce exactly the approved file change",
                evidence={"changed_paths": ",".join(changed)},
            )

        return succeeded_result(
            stage,
            f"safe code edit added {function_name} to {relative_path}",
            artifact_paths=(relative_path,),
            evidence={
                "target_path": relative_path,
                "transaction_id": report.transaction_id,
            },
        )
    except Exception as exc:
        return failed_result(stage, f"safe code editing failed: {exc}")


def verification_executor(
    repository_root: Path,
    session: AgentSession,
    stage: AgentStage,
    context: Mapping[str, Any],
) -> AgentStageResult:
    del context
    try:
        policy = BuildVerificationPolicy(
            allowed_tools=(VerificationTool.PYTEST,),
            require_clean_working_tree=False,
        )
        service = BuildVerificationService(policy)
        request = service.create_request(
            repository_root,
            objective=session.request.objective.objective,
            tools=(VerificationTool.PYTEST,),
        )
        decision = service.verify(request)
        if decision.decision is not ReleaseDecision.APPROVED:
            return failed_result(
                stage,
                "build verification rejected the edited repository",
                evidence={
                    "decision": decision.decision.value,
                    "decision_id": decision.decision_id,
                },
            )
        return succeeded_result(
            stage,
            "target repository pytest verification passed",
            evidence={
                "decision": decision.decision.value,
                "decision_id": decision.decision_id,
                "evidence_id": decision.evidence_id,
            },
        )
    except Exception as exc:
        return failed_result(stage, f"build verification failed: {exc}")
'@

Write-Utf8NoBom "forge\agent_runtime\production_service.py" @'
"""Production Agent Runtime registry for bounded M5.8 execution."""

from __future__ import annotations

from forge.agent_runtime.adapters.change_planning import ChangePlanningAdapter
from forge.agent_runtime.adapters.editing import EditingAdapter
from forge.agent_runtime.adapters.impact import ImpactAdapter
from forge.agent_runtime.adapters.planning import PlanningAdapter
from forge.agent_runtime.adapters.verification import VerificationAdapter
from forge.agent_runtime.models import AgentCapability, AgentRuntimePolicy
from forge.agent_runtime.production_executors import (
    change_planning_executor,
    editing_executor,
    impact_executor,
    planning_executor,
    verification_executor,
)
from forge.agent_runtime.registry import AgentCapabilityRegistry
from forge.agent_runtime.service import AgentRuntimeService

PRODUCTION_CAPABILITIES = (
    AgentCapability.MISSION_PLANNING,
    AgentCapability.IMPACT_ANALYSIS,
    AgentCapability.SAFE_CHANGE_PLANNING,
    AgentCapability.SAFE_CODE_EDITING,
    AgentCapability.BUILD_VERIFICATION,
)


def production_agent_service() -> AgentRuntimeService:
    registry = AgentCapabilityRegistry(
        (
            PlanningAdapter(planning_executor),
            ImpactAdapter(impact_executor),
            ChangePlanningAdapter(change_planning_executor),
            EditingAdapter(editing_executor),
            VerificationAdapter(verification_executor),
        )
    )
    policy = AgentRuntimePolicy(
        allowed_capabilities=PRODUCTION_CAPABILITIES,
        allow_code_changes=True,
        allow_network=False,
        allow_self_modification=False,
        require_clean_working_tree=True,
        require_plan_approval=True,
        require_edit_approval=True,
        require_release_approval=True,
    )
    return AgentRuntimeService(registry, policy)
'@

Write-Utf8NoBom "forge\mission_runtime\runner.py" @'
"""Production-facing mission-runtime facade over unified Agent Runtime."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

from forge.agent_runtime.models import AgentApproval, AgentObjective, AgentSession, ApprovalKind
from forge.agent_runtime.production_service import PRODUCTION_CAPABILITIES, production_agent_service
from forge.agent_runtime.store import AgentRuntimeStore


@dataclass(frozen=True, slots=True)
class MissionRuntimeRunResult:
    session: AgentSession

    @property
    def session_id(self) -> str:
        return self.session.session_id

    @property
    def status(self) -> str:
        return self.session.status.value


def _state_store(repository_root: Path) -> AgentRuntimeStore:
    override = os.environ.get("AERION_FORGE_RUNTIME_STATE_ROOT")
    base = (
        Path(override).expanduser().resolve()
        if override
        else Path.home() / ".aerion-forge" / "mission_runtime"
    )
    repository_key = hashlib.sha256(
        str(repository_root.resolve()).encode("utf-8")
    ).hexdigest()[:24]
    return AgentRuntimeStore(base / repository_key)


def _next_approval_kind(session: AgentSession) -> ApprovalKind:
    completed = {result.stage_id for result in session.stage_results}
    for stage in session.stages:
        if stage.stage_id in completed:
            continue
        if not set(stage.depends_on).issubset(completed):
            continue
        if stage.requires_approval is None:
            raise RuntimeError("next mission stage does not require approval")
        return stage.requires_approval
    raise RuntimeError("mission has no pending approval boundary")


def run_objective(*, objective: str, repository_root: Path) -> MissionRuntimeRunResult:
    root = repository_root.expanduser().resolve()
    service = production_agent_service()
    request = service.create_request(
        AgentObjective(
            objective=objective,
            repository_root=str(root),
            requested_capabilities=PRODUCTION_CAPABILITIES,
        ),
        dry_run=False,
        allow_code_changes=True,
    )
    session = service.create_session(request)
    updated = service.run_to_boundary(session)
    _state_store(root).save_session(updated)
    return MissionRuntimeRunResult(session=updated)


def approve_current_boundary(
    *,
    session_id: str,
    repository_root: Path,
    approved_by: str,
    reason: str,
) -> MissionRuntimeRunResult:
    root = repository_root.expanduser().resolve()
    store = _state_store(root)
    service = production_agent_service()
    session = store.load_session(session_id)
    kind = _next_approval_kind(session)
    approval = AgentApproval(
        approval_id=f"{session_id}-{kind.value}-approval-{len(session.approvals) + 1}",
        kind=kind,
        approved=True,
        approved_by=approved_by,
        reason=reason,
    )
    approved = service.add_approval(session, approval)
    updated = service.run_to_boundary(approved)
    store.save_session(updated)
    return MissionRuntimeRunResult(session=updated)


def load_session(*, session_id: str, repository_root: Path) -> AgentSession:
    return _state_store(repository_root.expanduser().resolve()).load_session(session_id)


def list_sessions(*, repository_root: Path) -> tuple[str, ...]:
    return _state_store(repository_root.expanduser().resolve()).list_session_ids()
'@

$CliPath = Join-Path $RepositoryRoot "forge\mission_runtime\cli.py"
$Cli = Get-Content $CliPath -Raw
$Cli = $Cli.Replace("    approve_plan,", "    approve_current_boundary,")
$Cli = $Cli.Replace("    result = approve_plan(", "    result = approve_current_boundary(")
$Cli = $Cli.Replace(
    '    """Approve the plan boundary and resume the mission."""',
    '    """Approve the current mission boundary and resume execution."""'
)
[System.IO.File]::WriteAllText(
    $CliPath,
    $Cli,
    [System.Text.UTF8Encoding]::new($false)
)
Write-Host "PATCHED forge\mission_runtime\cli.py" -ForegroundColor Green

Write-Utf8NoBom "tests\test_agent_runtime_production_service.py" @'
from forge.agent_runtime.models import AgentCapability
from forge.agent_runtime.production_service import PRODUCTION_CAPABILITIES, production_agent_service


def test_production_service_registers_required_capabilities() -> None:
    service = production_agent_service()
    assert set(service.registry.capabilities()) == set(PRODUCTION_CAPABILITIES)
    assert AgentCapability.SAFE_CODE_EDITING in PRODUCTION_CAPABILITIES
    assert AgentCapability.BUILD_VERIFICATION in PRODUCTION_CAPABILITIES
    assert service.policy.allow_code_changes
'@

Write-Host ""
Write-Host "M5.8 Package 5B files written. Running validation..." -ForegroundColor Cyan

python -m ruff check `
    .\forge\agent_runtime\production_executors.py `
    .\forge\agent_runtime\production_service.py `
    .\forge\mission_runtime\runner.py `
    .\forge\mission_runtime\cli.py `
    .\tests\test_agent_runtime_production_service.py `
    --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_agent_runtime_production_service.py `
    .\tests\test_mission_runtime_runner.py `
    .\tests\test_mission_runtime_cli.py `
    .\tests\test_agent_runtime_end_to_end.py `
    -p no:cacheprovider
Assert-CommandSuccess "M5.8 Package 5B focused tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full repository test suite"

Write-Host ""
Write-Host "====================================================" -ForegroundColor Green
Write-Host "M5.8 PACKAGE 5B BOUNDED EXECUTION INTEGRATION COMPLETE" -ForegroundColor Green
Write-Host "====================================================" -ForegroundColor Green
Write-Host "Package 5B wires Safe Code Editing and Build Verification." -ForegroundColor Green
Write-Host "Unsupported natural-language edit grammars fail closed." -ForegroundColor Yellow
Write-Host "This is a bounded acceptance executor, not yet a general code-synthesis engine." -ForegroundColor Yellow
Write-Host ""

git status --short