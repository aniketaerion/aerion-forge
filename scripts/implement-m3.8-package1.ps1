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

Write-Utf8NoBom "forge\agent_runtime\adapters\base.py" @'
"""Capability-adapter contracts for M3.8 Unified Agent Runtime."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from forge.agent_runtime.errors import AgentRuntimeCapabilityError
from forge.agent_runtime.models import (
    AgentCapability,
    AgentSession,
    AgentStage,
    AgentStageResult,
    AgentStageStatus,
)

CapabilityExecutor = Callable[
    [Path, AgentSession, AgentStage, Mapping[str, Any]],
    AgentStageResult,
]


class AgentCapabilityAdapter(ABC):
    """Common runtime interface for one existing Forge capability."""

    capability: AgentCapability

    @abstractmethod
    def execute(
        self,
        repository_root: Path,
        session: AgentSession,
        stage: AgentStage,
        context: Mapping[str, Any],
    ) -> AgentStageResult:
        """Execute one capability-backed runtime stage."""

    def validate_stage(self, stage: AgentStage) -> None:
        """Ensure the stage is assigned to this adapter."""
        if stage.capability is not self.capability:
            raise AgentRuntimeCapabilityError(
                "adapter capability mismatch: "
                f"expected {self.capability.value}, "
                f"received {stage.capability.value}"
            )


class CallbackCapabilityAdapter(AgentCapabilityAdapter):
    """Safe dependency-injection adapter for a native Forge service."""

    def __init__(self, executor: CapabilityExecutor) -> None:
        self._executor = executor

    def execute(
        self,
        repository_root: Path,
        session: AgentSession,
        stage: AgentStage,
        context: Mapping[str, Any],
    ) -> AgentStageResult:
        self.validate_stage(stage)
        result = self._executor(
            repository_root.resolve(),
            session,
            stage,
            context,
        )

        if result.stage_id != stage.stage_id:
            raise AgentRuntimeCapabilityError(
                "capability adapter returned a result for another stage"
            )

        return result


def succeeded_result(
    stage: AgentStage,
    summary: str,
    *,
    artifact_paths: tuple[str, ...] = (),
    evidence: Mapping[str, str] | None = None,
    started_at: datetime | None = None,
) -> AgentStageResult:
    """Create a normalized successful runtime-stage result."""
    return AgentStageResult(
        stage_id=stage.stage_id,
        status=AgentStageStatus.SUCCEEDED,
        summary=summary,
        artifact_paths=artifact_paths,
        evidence=dict(evidence or {}),
        started_at=started_at or datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )


def failed_result(
    stage: AgentStage,
    summary: str,
    *,
    evidence: Mapping[str, str] | None = None,
    started_at: datetime | None = None,
) -> AgentStageResult:
    """Create a normalized failed runtime-stage result."""
    return AgentStageResult(
        stage_id=stage.stage_id,
        status=AgentStageStatus.FAILED,
        summary=summary,
        evidence=dict(evidence or {}),
        started_at=started_at or datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
'@

Write-Utf8NoBom "forge\agent_runtime\adapters\planning.py" @'
"""Mission-planning adapter for M3.8 Unified Agent Runtime."""

from __future__ import annotations

from forge.agent_runtime.adapters.base import (
    CallbackCapabilityAdapter,
    CapabilityExecutor,
)
from forge.agent_runtime.models import AgentCapability


class PlanningAdapter(CallbackCapabilityAdapter):
    """Bridge the unified runtime to mission planning."""

    capability = AgentCapability.MISSION_PLANNING

    def __init__(self, executor: CapabilityExecutor) -> None:
        super().__init__(executor)
'@

Write-Utf8NoBom "forge\agent_runtime\adapters\impact.py" @'
"""Impact-analysis adapter for M3.8 Unified Agent Runtime."""

from __future__ import annotations

from forge.agent_runtime.adapters.base import (
    CallbackCapabilityAdapter,
    CapabilityExecutor,
)
from forge.agent_runtime.models import AgentCapability


class ImpactAdapter(CallbackCapabilityAdapter):
    """Bridge the unified runtime to impact analysis."""

    capability = AgentCapability.IMPACT_ANALYSIS

    def __init__(self, executor: CapabilityExecutor) -> None:
        super().__init__(executor)
'@

Write-Utf8NoBom "forge\agent_runtime\adapters\change_planning.py" @'
"""Safe-change-planning adapter for M3.8 Unified Agent Runtime."""

from __future__ import annotations

from forge.agent_runtime.adapters.base import (
    CallbackCapabilityAdapter,
    CapabilityExecutor,
)
from forge.agent_runtime.models import AgentCapability


class ChangePlanningAdapter(CallbackCapabilityAdapter):
    """Bridge the unified runtime to safe change planning."""

    capability = AgentCapability.SAFE_CHANGE_PLANNING

    def __init__(self, executor: CapabilityExecutor) -> None:
        super().__init__(executor)
'@

Write-Utf8NoBom "forge\agent_runtime\adapters\editing.py" @'
"""Safe-code-editing adapter for M3.8 Unified Agent Runtime."""

from __future__ import annotations

from forge.agent_runtime.adapters.base import (
    CallbackCapabilityAdapter,
    CapabilityExecutor,
)
from forge.agent_runtime.models import AgentCapability


class EditingAdapter(CallbackCapabilityAdapter):
    """Bridge the unified runtime to safe code editing."""

    capability = AgentCapability.SAFE_CODE_EDITING

    def __init__(self, executor: CapabilityExecutor) -> None:
        super().__init__(executor)
'@

Write-Utf8NoBom "forge\agent_runtime\adapters\repair.py" @'
"""Autonomous-repair adapter for M3.8 Unified Agent Runtime."""

from __future__ import annotations

from forge.agent_runtime.adapters.base import (
    CallbackCapabilityAdapter,
    CapabilityExecutor,
)
from forge.agent_runtime.models import AgentCapability


class RepairAdapter(CallbackCapabilityAdapter):
    """Bridge the unified runtime to autonomous repair."""

    capability = AgentCapability.AUTONOMOUS_REPAIR

    def __init__(self, executor: CapabilityExecutor) -> None:
        super().__init__(executor)
'@

Write-Utf8NoBom "forge\agent_runtime\adapters\verification.py" @'
"""Build-verification adapter for M3.8 Unified Agent Runtime."""

from __future__ import annotations

from forge.agent_runtime.adapters.base import (
    CallbackCapabilityAdapter,
    CapabilityExecutor,
)
from forge.agent_runtime.models import AgentCapability


class VerificationAdapter(CallbackCapabilityAdapter):
    """Bridge the unified runtime to build verification."""

    capability = AgentCapability.BUILD_VERIFICATION

    def __init__(self, executor: CapabilityExecutor) -> None:
        super().__init__(executor)
'@

Write-Utf8NoBom "forge\agent_runtime\adapters\__init__.py" @'
"""M3.8 unified-runtime capability adapters."""

from forge.agent_runtime.adapters.base import (
    AgentCapabilityAdapter,
    CallbackCapabilityAdapter,
    CapabilityExecutor,
    failed_result,
    succeeded_result,
)
from forge.agent_runtime.adapters.change_planning import (
    ChangePlanningAdapter,
)
from forge.agent_runtime.adapters.editing import EditingAdapter
from forge.agent_runtime.adapters.impact import ImpactAdapter
from forge.agent_runtime.adapters.planning import PlanningAdapter
from forge.agent_runtime.adapters.repair import RepairAdapter
from forge.agent_runtime.adapters.verification import VerificationAdapter

__all__ = [
    "AgentCapabilityAdapter",
    "CallbackCapabilityAdapter",
    "CapabilityExecutor",
    "ChangePlanningAdapter",
    "EditingAdapter",
    "ImpactAdapter",
    "PlanningAdapter",
    "RepairAdapter",
    "VerificationAdapter",
    "failed_result",
    "succeeded_result",
]
'@

Write-Utf8NoBom "forge\agent_runtime\registry.py" @'
"""Capability-adapter registry for M3.8 Unified Agent Runtime."""

from __future__ import annotations

from collections.abc import Iterable

from forge.agent_runtime.adapters import AgentCapabilityAdapter
from forge.agent_runtime.errors import AgentRuntimeCapabilityError
from forge.agent_runtime.models import AgentCapability


class AgentCapabilityRegistry:
    """Deterministic registry of unified-runtime capability adapters."""

    def __init__(
        self,
        adapters: Iterable[AgentCapabilityAdapter] = (),
    ) -> None:
        self._adapters: dict[
            AgentCapability,
            AgentCapabilityAdapter,
        ] = {}

        for adapter in adapters:
            self.register(adapter)

    def register(
        self,
        adapter: AgentCapabilityAdapter,
    ) -> None:
        """Register one adapter and reject duplicate capabilities."""
        if adapter.capability in self._adapters:
            raise AgentRuntimeCapabilityError(
                "duplicate capability adapter registration: "
                f"{adapter.capability.value}"
            )

        self._adapters[adapter.capability] = adapter

    def get(
        self,
        capability: AgentCapability,
    ) -> AgentCapabilityAdapter:
        """Return the adapter registered for a capability."""
        try:
            return self._adapters[capability]
        except KeyError as exc:
            raise AgentRuntimeCapabilityError(
                f"capability adapter is not registered: {capability.value}"
            ) from exc

    def contains(
        self,
        capability: AgentCapability,
    ) -> bool:
        """Return whether the capability is registered."""
        return capability in self._adapters

    def capabilities(self) -> tuple[AgentCapability, ...]:
        """Return registered capabilities in deterministic order."""
        return tuple(
            sorted(
                self._adapters,
                key=lambda capability: capability.value,
            )
        )

    def validate_required(
        self,
        capabilities: Iterable[AgentCapability],
    ) -> None:
        """Fail when any required capability lacks an adapter."""
        missing = tuple(
            sorted(
                {
                    capability
                    for capability in capabilities
                    if capability not in self._adapters
                },
                key=lambda capability: capability.value,
            )
        )

        if missing:
            names = ", ".join(
                capability.value for capability in missing
            )
            raise AgentRuntimeCapabilityError(
                f"required capability adapters are missing: {names}"
            )
'@

Write-Utf8NoBom "tests\test_agent_runtime_registry.py" @'
from pathlib import Path
from typing import Any

import pytest

from forge.agent_runtime.adapters.base import succeeded_result
from forge.agent_runtime.adapters.planning import PlanningAdapter
from forge.agent_runtime.errors import AgentRuntimeCapabilityError
from forge.agent_runtime.models import (
    AgentCapability,
    AgentObjective,
    AgentRuntimeRequest,
    AgentSession,
    AgentSessionStatus,
    AgentStage,
    AgentStageResult,
)
from forge.agent_runtime.registry import AgentCapabilityRegistry


def executor(
    repository_root: Path,
    session: AgentSession,
    stage: AgentStage,
    context: dict[str, Any],
) -> AgentStageResult:
    del repository_root, session, context
    return succeeded_result(stage, "planned")


def test_registry_returns_registered_adapter() -> None:
    adapter = PlanningAdapter(executor)
    registry = AgentCapabilityRegistry((adapter,))

    assert registry.get(AgentCapability.MISSION_PLANNING) is adapter


def test_registry_rejects_duplicate_capability() -> None:
    adapter = PlanningAdapter(executor)

    with pytest.raises(AgentRuntimeCapabilityError):
        AgentCapabilityRegistry((adapter, adapter))


def test_registry_reports_missing_required_capability() -> None:
    registry = AgentCapabilityRegistry()

    with pytest.raises(AgentRuntimeCapabilityError):
        registry.validate_required(
            (AgentCapability.MISSION_PLANNING,)
        )


def test_adapter_rejects_capability_mismatch() -> None:
    adapter = PlanningAdapter(executor)
    objective = AgentObjective(
        objective="Implement feature",
        repository_root=".",
    )
    request = AgentRuntimeRequest(
        request_id="request-1",
        objective=objective,
    )
    stage = AgentStage(
        stage_id="stage-1",
        sequence=1,
        capability=AgentCapability.IMPACT_ANALYSIS,
        name="Impact",
    )
    session = AgentSession(
        session_id="session-1",
        request=request,
        status=AgentSessionStatus.CREATED,
        stages=(stage,),
    )

    with pytest.raises(AgentRuntimeCapabilityError):
        adapter.execute(Path.cwd(), session, stage, {})
'@

$AdapterTests = @{
    "test_agent_runtime_planning_adapter.py" = @'
from pathlib import Path
from typing import Any

from forge.agent_runtime.adapters.base import succeeded_result
from forge.agent_runtime.adapters.planning import PlanningAdapter
from forge.agent_runtime.models import (
    AgentCapability,
    AgentObjective,
    AgentRuntimeRequest,
    AgentSession,
    AgentSessionStatus,
    AgentStage,
    AgentStageResult,
)


def test_planning_adapter_executes_callback(tmp_path: Path) -> None:
    observed: dict[str, str] = {}

    def executor(
        repository_root: Path,
        session: AgentSession,
        stage: AgentStage,
        context: dict[str, Any],
    ) -> AgentStageResult:
        del session, context
        observed["root"] = str(repository_root)
        return succeeded_result(stage, "mission plan created")

    stage = AgentStage(
        stage_id="planning",
        sequence=1,
        capability=AgentCapability.MISSION_PLANNING,
        name="Planning",
    )
    request = AgentRuntimeRequest(
        request_id="request-1",
        objective=AgentObjective(
            objective="Implement feature",
            repository_root=str(tmp_path),
        ),
    )
    session = AgentSession(
        session_id="session-1",
        request=request,
        status=AgentSessionStatus.PLANNING,
        stages=(stage,),
    )

    result = PlanningAdapter(executor).execute(
        tmp_path,
        session,
        stage,
        {},
    )

    assert result.summary == "mission plan created"
    assert observed["root"] == str(tmp_path.resolve())
'@
    "test_agent_runtime_impact_adapter.py" = @'
from pathlib import Path
from typing import Any

from forge.agent_runtime.adapters.base import succeeded_result
from forge.agent_runtime.adapters.impact import ImpactAdapter
from forge.agent_runtime.models import (
    AgentCapability,
    AgentObjective,
    AgentRuntimeRequest,
    AgentSession,
    AgentSessionStatus,
    AgentStage,
    AgentStageResult,
)


def test_impact_adapter_normalizes_result(tmp_path: Path) -> None:
    def executor(
        repository_root: Path,
        session: AgentSession,
        stage: AgentStage,
        context: dict[str, Any],
    ) -> AgentStageResult:
        del repository_root, session, context
        return succeeded_result(
            stage,
            "impact analysed",
            evidence={"risk": "low"},
        )

    stage = AgentStage(
        stage_id="impact",
        sequence=1,
        capability=AgentCapability.IMPACT_ANALYSIS,
        name="Impact",
    )
    request = AgentRuntimeRequest(
        request_id="request-1",
        objective=AgentObjective(
            objective="Analyse impact",
            repository_root=str(tmp_path),
        ),
    )
    session = AgentSession(
        session_id="session-1",
        request=request,
        status=AgentSessionStatus.EXECUTING,
        stages=(stage,),
    )

    result = ImpactAdapter(executor).execute(
        tmp_path,
        session,
        stage,
        {},
    )

    assert result.evidence["risk"] == "low"
'@
    "test_agent_runtime_change_planning_adapter.py" = @'
from pathlib import Path
from typing import Any

from forge.agent_runtime.adapters.base import succeeded_result
from forge.agent_runtime.adapters.change_planning import (
    ChangePlanningAdapter,
)
from forge.agent_runtime.models import (
    AgentCapability,
    AgentObjective,
    AgentRuntimeRequest,
    AgentSession,
    AgentSessionStatus,
    AgentStage,
    AgentStageResult,
)


def test_change_planning_adapter_returns_artifacts(
    tmp_path: Path,
) -> None:
    def executor(
        repository_root: Path,
        session: AgentSession,
        stage: AgentStage,
        context: dict[str, Any],
    ) -> AgentStageResult:
        del repository_root, session, context
        return succeeded_result(
            stage,
            "change plan created",
            artifact_paths=("reports/change-plan.json",),
        )

    stage = AgentStage(
        stage_id="change-plan",
        sequence=1,
        capability=AgentCapability.SAFE_CHANGE_PLANNING,
        name="Change plan",
    )
    request = AgentRuntimeRequest(
        request_id="request-1",
        objective=AgentObjective(
            objective="Plan changes",
            repository_root=str(tmp_path),
        ),
    )
    session = AgentSession(
        session_id="session-1",
        request=request,
        status=AgentSessionStatus.PLANNING,
        stages=(stage,),
    )

    result = ChangePlanningAdapter(executor).execute(
        tmp_path,
        session,
        stage,
        {},
    )

    assert result.artifact_paths == ("reports/change-plan.json",)
'@
    "test_agent_runtime_editing_adapter.py" = @'
from pathlib import Path
from typing import Any

from forge.agent_runtime.adapters.base import succeeded_result
from forge.agent_runtime.adapters.editing import EditingAdapter
from forge.agent_runtime.models import (
    AgentCapability,
    AgentObjective,
    AgentRuntimeRequest,
    AgentSession,
    AgentSessionStatus,
    AgentStage,
    AgentStageResult,
)


def test_editing_adapter_preserves_stage_identity(
    tmp_path: Path,
) -> None:
    def executor(
        repository_root: Path,
        session: AgentSession,
        stage: AgentStage,
        context: dict[str, Any],
    ) -> AgentStageResult:
        del repository_root, session, context
        return succeeded_result(stage, "edit applied")

    stage = AgentStage(
        stage_id="edit",
        sequence=1,
        capability=AgentCapability.SAFE_CODE_EDITING,
        name="Edit",
    )
    request = AgentRuntimeRequest(
        request_id="request-1",
        objective=AgentObjective(
            objective="Apply edit",
            repository_root=str(tmp_path),
        ),
    )
    session = AgentSession(
        session_id="session-1",
        request=request,
        status=AgentSessionStatus.EXECUTING,
        stages=(stage,),
    )

    result = EditingAdapter(executor).execute(
        tmp_path,
        session,
        stage,
        {},
    )

    assert result.stage_id == stage.stage_id
'@
    "test_agent_runtime_repair_adapter.py" = @'
from pathlib import Path
from typing import Any

from forge.agent_runtime.adapters.base import failed_result
from forge.agent_runtime.adapters.repair import RepairAdapter
from forge.agent_runtime.models import (
    AgentCapability,
    AgentObjective,
    AgentRuntimeRequest,
    AgentSession,
    AgentSessionStatus,
    AgentStage,
    AgentStageResult,
    AgentStageStatus,
)


def test_repair_adapter_can_return_failure(tmp_path: Path) -> None:
    def executor(
        repository_root: Path,
        session: AgentSession,
        stage: AgentStage,
        context: dict[str, Any],
    ) -> AgentStageResult:
        del repository_root, session, context
        return failed_result(stage, "repair exhausted")

    stage = AgentStage(
        stage_id="repair",
        sequence=1,
        capability=AgentCapability.AUTONOMOUS_REPAIR,
        name="Repair",
    )
    request = AgentRuntimeRequest(
        request_id="request-1",
        objective=AgentObjective(
            objective="Repair validation",
            repository_root=str(tmp_path),
        ),
    )
    session = AgentSession(
        session_id="session-1",
        request=request,
        status=AgentSessionStatus.REPAIRING,
        stages=(stage,),
    )

    result = RepairAdapter(executor).execute(
        tmp_path,
        session,
        stage,
        {},
    )

    assert result.status is AgentStageStatus.FAILED
'@
    "test_agent_runtime_verification_adapter.py" = @'
from pathlib import Path
from typing import Any

from forge.agent_runtime.adapters.base import succeeded_result
from forge.agent_runtime.adapters.verification import VerificationAdapter
from forge.agent_runtime.models import (
    AgentCapability,
    AgentObjective,
    AgentRuntimeRequest,
    AgentSession,
    AgentSessionStatus,
    AgentStage,
    AgentStageResult,
)


def test_verification_adapter_returns_release_evidence(
    tmp_path: Path,
) -> None:
    def executor(
        repository_root: Path,
        session: AgentSession,
        stage: AgentStage,
        context: dict[str, Any],
    ) -> AgentStageResult:
        del repository_root, session, context
        return succeeded_result(
            stage,
            "release approved",
            evidence={"decision": "approved"},
        )

    stage = AgentStage(
        stage_id="verification",
        sequence=1,
        capability=AgentCapability.BUILD_VERIFICATION,
        name="Verification",
    )
    request = AgentRuntimeRequest(
        request_id="request-1",
        objective=AgentObjective(
            objective="Verify release",
            repository_root=str(tmp_path),
        ),
    )
    session = AgentSession(
        session_id="session-1",
        request=request,
        status=AgentSessionStatus.VERIFYING,
        stages=(stage,),
    )

    result = VerificationAdapter(executor).execute(
        tmp_path,
        session,
        stage,
        {},
    )

    assert result.evidence["decision"] == "approved"
'@
}

foreach ($Entry in $AdapterTests.GetEnumerator()) {
    Write-Utf8NoBom (
        "tests\" + $Entry.Key
    ) $Entry.Value
}

Write-Host ""
Write-Host "M3.8 Package 1 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_agent_runtime_registry.py `
    .\tests\test_agent_runtime_planning_adapter.py `
    .\tests\test_agent_runtime_impact_adapter.py `
    .\tests\test_agent_runtime_change_planning_adapter.py `
    .\tests\test_agent_runtime_editing_adapter.py `
    .\tests\test_agent_runtime_repair_adapter.py `
    .\tests\test_agent_runtime_verification_adapter.py `
    -p no:cacheprovider
Assert-CommandSuccess "M3.8 Package 1 tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M3.8 PACKAGE 1 COMPLETE" -ForegroundColor Green

git status --short