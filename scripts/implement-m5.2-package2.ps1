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

$ExpectedBranch = "feature/m5.2-autonomous-execution-engine"
$CurrentBranch = git branch --show-current
Assert-CommandSuccess "Read current branch"

if ($CurrentBranch -ne $ExpectedBranch) {
    throw "M5.2 Package 2 must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

Write-Utf8NoBom "forge\autonomous_execution\tool_registry.py" @'
"""Registered tool catalogue for autonomous execution."""

from __future__ import annotations

from dataclasses import dataclass, field, field

from forge.autonomous_execution.errors import (
    ToolContractError,
    ToolResolutionError,
)
from forge.autonomous_execution.tool_contracts import ToolDefinition


@dataclass(slots=True)
class ToolRegistry:
    """Deterministic allowlist of executable tools."""

    _tools: dict[str, ToolDefinition] = field(default_factory=dict)

    def register(self, definition: ToolDefinition) -> None:
        if definition.tool_name in self._tools:
            raise ToolContractError(
                f"Tool already registered: {definition.tool_name}"
            )
        self._tools[definition.tool_name] = definition

    def resolve(self, tool_name: str) -> ToolDefinition:
        try:
            return self._tools[tool_name]
        except KeyError as exc:
            raise ToolResolutionError(
                f"Tool is not registered: {tool_name}"
            ) from exc

    def definitions(self) -> tuple[ToolDefinition, ...]:
        return tuple(
            self._tools[name]
            for name in sorted(self._tools)
        )

    def contains(self, tool_name: str) -> bool:
        return tool_name in self._tools
'@

Write-Utf8NoBom "forge\autonomous_execution\argument_validation.py" @'
"""Tool argument validation against registered contracts."""

from __future__ import annotations

from typing import Any

from forge.autonomous_execution.errors import ToolContractError
from forge.autonomous_execution.tool_contracts import (
    ToolDefinition,
    ToolExecutionRequest,
)


def _matches_type(
    value: Any,
    expected: str,
) -> bool:
    mapping: dict[str, type[Any] | tuple[type[Any], ...]] = {
        "str": str,
        "int": int,
        "float": (int, float),
        "bool": bool,
        "list": list,
        "dict": dict,
    }
    expected_type = mapping.get(expected)

    if expected_type is None:
        raise ToolContractError(
            f"Unsupported argument schema type: {expected}"
        )

    return isinstance(value, expected_type)


def validate_tool_arguments(
    definition: ToolDefinition,
    request: ToolExecutionRequest,
) -> None:
    """Validate tool, action, required arguments, and argument types."""
    if request.tool_name != definition.tool_name:
        raise ToolContractError(
            "Tool request does not match resolved tool definition."
        )

    if request.action_kind not in definition.action_kinds:
        raise ToolContractError(
            f"Action '{request.action_kind}' is not allowed "
            f"for tool '{definition.tool_name}'."
        )

    schema = definition.argument_schema
    unknown = set(request.arguments).difference(schema)

    if unknown:
        raise ToolContractError(
            "Unknown tool arguments: "
            + ", ".join(sorted(unknown))
        )

    missing = set(schema).difference(request.arguments)

    if missing:
        raise ToolContractError(
            "Missing tool arguments: "
            + ", ".join(sorted(missing))
        )

    for name, expected in schema.items():
        value = request.arguments[name]

        if not _matches_type(value, expected):
            raise ToolContractError(
                f"Argument '{name}' must be of type '{expected}'."
            )
'@

Write-Utf8NoBom "forge\autonomous_execution\effect_verification.py" @'
"""Verification of actual repository effects against approved scope."""

from __future__ import annotations

from pathlib import PurePosixPath

from forge.autonomous_execution.errors import ToolContractError


def _normalized(path: str) -> str:
    return PurePosixPath(path.replace("\\", "/")).as_posix().lstrip("./")


def _is_within(
    path: str,
    scope: str,
) -> bool:
    normalized_path = _normalized(path)
    normalized_scope = _normalized(scope).rstrip("/")

    return (
        normalized_path == normalized_scope
        or normalized_path.startswith(normalized_scope + "/")
    )


def verify_affected_files(
    affected_files: tuple[str, ...],
    approved_scope: tuple[str, ...],
) -> None:
    """Reject repository effects outside approved scope."""
    if not affected_files:
        return

    if not approved_scope:
        raise ToolContractError(
            "Affected files exist but approved scope is empty."
        )

    violations = tuple(
        path
        for path in affected_files
        if not any(
            _is_within(path, scope)
            for scope in approved_scope
        )
    )

    if violations:
        raise ToolContractError(
            "Tool affected files outside approved scope: "
            + ", ".join(sorted(violations))
        )
'@

Write-Utf8NoBom "forge\autonomous_execution\tool_execution.py" @'
"""Controlled in-process tool execution abstraction."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, field
from datetime import datetime, timezone
from typing import Any

from forge.autonomous_execution.errors import ToolResolutionError
from forge.autonomous_execution.states import ToolExecutionStatus
from forge.autonomous_execution.tool_contracts import (
    ToolExecutionRequest,
    ToolExecutionResult,
)

ToolHandler = Callable[
    [ToolExecutionRequest],
    tuple[int, tuple[str, ...], str | None],
]


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class ToolExecutor:
    """Execute only explicitly registered in-process handlers."""

    _handlers: dict[str, ToolHandler] = field(default_factory=dict)

    def register_handler(
        self,
        tool_name: str,
        handler: ToolHandler,
    ) -> None:
        if tool_name in self._handlers:
            raise ToolResolutionError(
                f"Tool handler already registered: {tool_name}"
            )
        self._handlers[tool_name] = handler

    def handlers(self) -> Mapping[str, ToolHandler]:
        return dict(self._handlers)

    def execute(
        self,
        request: ToolExecutionRequest,
    ) -> ToolExecutionResult:
        started_at = utc_timestamp()

        if request.dry_run:
            return ToolExecutionResult(
                invocation_id=request.invocation_id,
                status=ToolExecutionStatus.DRY_RUN,
                exit_code=0,
                affected_files=(),
                started_at=started_at,
                completed_at=utc_timestamp(),
            )

        try:
            handler = self._handlers[request.tool_name]
        except KeyError as exc:
            raise ToolResolutionError(
                f"No execution handler registered: {request.tool_name}"
            ) from exc

        exit_code, affected_files, result_digest = handler(request)
        status = (
            ToolExecutionStatus.SUCCEEDED
            if exit_code == 0
            else ToolExecutionStatus.FAILED
        )

        return ToolExecutionResult(
            invocation_id=request.invocation_id,
            status=status,
            exit_code=exit_code,
            affected_files=affected_files,
            result_digest=result_digest,
            started_at=started_at,
            completed_at=utc_timestamp(),
        )
'@

Write-Utf8NoBom "forge\autonomous_execution\tool_gateway.py" @'
"""Controlled gateway for autonomous tool invocations."""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.autonomous_execution.argument_validation import (
    validate_tool_arguments,
)
from forge.autonomous_execution.effect_verification import (
    verify_affected_files,
)
from forge.autonomous_execution.errors import ToolContractError
from forge.autonomous_execution.policies import (
    AutonomousExecutionPolicy,
)
from forge.autonomous_execution.tool_contracts import (
    ToolExecutionRequest,
    ToolExecutionResult,
)
from forge.autonomous_execution.tool_execution import ToolExecutor
from forge.autonomous_execution.tool_registry import ToolRegistry


@dataclass(slots=True)
class ControlledToolGateway:
    """Resolve, validate, execute, and verify one tool invocation."""

    registry: ToolRegistry
    executor: ToolExecutor
    policy: AutonomousExecutionPolicy = field(
        default_factory=AutonomousExecutionPolicy
    )

    def execute(
        self,
        request: ToolExecutionRequest,
    ) -> ToolExecutionResult:
        definition = self.registry.resolve(request.tool_name)

        validate_tool_arguments(definition, request)

        if (
            definition.mutates_repository
            and self.policy.gateway.require_checkpoint_for_mutation
            and request.checkpoint_id is None
        ):
            raise ToolContractError(
                "Mutating tool invocation requires a checkpoint."
            )

        result = self.executor.execute(request)

        if self.policy.gateway.require_effect_verification:
            verify_affected_files(
                result.affected_files,
                request.approved_scope,
            )

        if len(result.affected_files) > (
            self.policy.budgets.maximum_affected_files
        ):
            raise ToolContractError(
                "Tool affected more files than the execution policy allows."
            )

        return result
'@

Write-Utf8NoBom "tests\test_autonomous_execution_tool_registry.py" @'
import pytest

from forge.autonomous_execution.errors import (
    ToolContractError,
    ToolResolutionError,
)
from forge.autonomous_execution.tool_contracts import ToolDefinition
from forge.autonomous_execution.tool_registry import ToolRegistry
from forge.autonomous_runtime.states import AuthorityLevel, RiskClass


def definition() -> ToolDefinition:
    return ToolDefinition(
        tool_name="ruff",
        action_kinds=("check",),
        authority_required=AuthorityLevel.A0_READ,
        risk_class=RiskClass.R0_READ_ONLY,
        argument_schema={"path": "str"},
    )


def test_registry_resolves_registered_tool() -> None:
    registry = ToolRegistry()
    registry.register(definition())

    assert registry.resolve("ruff").tool_name == "ruff"


def test_duplicate_tool_is_rejected() -> None:
    registry = ToolRegistry()
    registry.register(definition())

    with pytest.raises(ToolContractError):
        registry.register(definition())


def test_unknown_tool_is_rejected() -> None:
    with pytest.raises(ToolResolutionError):
        ToolRegistry().resolve("unknown")
'@

Write-Utf8NoBom "tests\test_autonomous_execution_argument_validation.py" @'
import pytest

from forge.autonomous_execution.argument_validation import (
    validate_tool_arguments,
)
from forge.autonomous_execution.errors import ToolContractError
from forge.autonomous_execution.tool_contracts import (
    ToolDefinition,
    ToolExecutionRequest,
)
from forge.autonomous_runtime.states import AuthorityLevel, RiskClass


def definition() -> ToolDefinition:
    return ToolDefinition(
        tool_name="ruff",
        action_kinds=("check",),
        authority_required=AuthorityLevel.A0_READ,
        risk_class=RiskClass.R0_READ_ONLY,
        argument_schema={"path": "str"},
    )


def request(
    arguments: dict[str, object],
) -> ToolExecutionRequest:
    return ToolExecutionRequest(
        invocation_id="invocation-1",
        mission_id="mission-1",
        step_id="step-1",
        tool_name="ruff",
        action_kind="check",
        arguments=arguments,
    )


def test_valid_arguments_pass() -> None:
    validate_tool_arguments(
        definition(),
        request({"path": "."}),
    )


def test_missing_argument_is_rejected() -> None:
    with pytest.raises(ToolContractError):
        validate_tool_arguments(
            definition(),
            request({}),
        )


def test_wrong_argument_type_is_rejected() -> None:
    with pytest.raises(ToolContractError):
        validate_tool_arguments(
            definition(),
            request({"path": 1}),
        )
'@

Write-Utf8NoBom "tests\test_autonomous_execution_effect_verification.py" @'
import pytest

from forge.autonomous_execution.effect_verification import (
    verify_affected_files,
)
from forge.autonomous_execution.errors import ToolContractError


def test_files_inside_scope_pass() -> None:
    verify_affected_files(
        (
            "forge/autonomous_execution/tool_gateway.py",
            "forge/autonomous_execution/tool_registry.py",
        ),
        ("forge/autonomous_execution",),
    )


def test_file_outside_scope_is_rejected() -> None:
    with pytest.raises(ToolContractError):
        verify_affected_files(
            ("deployments/production.yml",),
            ("forge/autonomous_execution",),
        )
'@

Write-Utf8NoBom "tests\test_autonomous_execution_tool_gateway.py" @'
import pytest

from forge.autonomous_execution.errors import ToolContractError
from forge.autonomous_execution.tool_contracts import (
    ToolDefinition,
    ToolExecutionRequest,
)
from forge.autonomous_execution.tool_execution import ToolExecutor
from forge.autonomous_execution.tool_gateway import (
    ControlledToolGateway,
)
from forge.autonomous_execution.tool_registry import ToolRegistry
from forge.autonomous_runtime.states import AuthorityLevel, RiskClass


def gateway() -> ControlledToolGateway:
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            tool_name="file-editor",
            action_kinds=("apply_patch",),
            authority_required=AuthorityLevel.A2_MODIFY,
            risk_class=RiskClass.R2_MODERATE,
            mutates_repository=True,
            requires_checkpoint=True,
            argument_schema={"path": "str"},
        )
    )

    executor = ToolExecutor()
    executor.register_handler(
        "file-editor",
        lambda request: (
            0,
            (str(request.arguments["path"]),),
            "digest-1",
        ),
    )

    return ControlledToolGateway(
        registry=registry,
        executor=executor,
    )


def test_dry_run_performs_no_mutation() -> None:
    result = gateway().execute(
        ToolExecutionRequest(
            invocation_id="invocation-1",
            mission_id="mission-1",
            step_id="step-1",
            tool_name="file-editor",
            action_kind="apply_patch",
            arguments={
                "path": "forge/autonomous_execution/models.py"
            },
            approved_scope=("forge/autonomous_execution",),
            checkpoint_id="checkpoint-1",
            dry_run=True,
        )
    )

    assert result.affected_files == ()
    assert result.exit_code == 0


def test_mutating_tool_requires_checkpoint() -> None:
    with pytest.raises(ToolContractError):
        gateway().execute(
            ToolExecutionRequest(
                invocation_id="invocation-2",
                mission_id="mission-1",
                step_id="step-1",
                tool_name="file-editor",
                action_kind="apply_patch",
                arguments={
                    "path": "forge/autonomous_execution/models.py"
                },
                approved_scope=("forge/autonomous_execution",),
                dry_run=False,
            )
        )


def test_actual_effects_are_scope_checked() -> None:
    tool_gateway = gateway()

    with pytest.raises(ToolContractError):
        tool_gateway.execute(
            ToolExecutionRequest(
                invocation_id="invocation-3",
                mission_id="mission-1",
                step_id="step-1",
                tool_name="file-editor",
                action_kind="apply_patch",
                arguments={"path": "deployments/production.yml"},
                approved_scope=("forge/autonomous_execution",),
                checkpoint_id="checkpoint-1",
                dry_run=False,
            )
        )
'@

Write-Host ""
Write-Host "M5.2 Package 2 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_autonomous_execution_tool_registry.py `
    .\tests\test_autonomous_execution_argument_validation.py `
    .\tests\test_autonomous_execution_effect_verification.py `
    .\tests\test_autonomous_execution_tool_gateway.py `
    -p no:cacheprovider
Assert-CommandSuccess "M5.2 Package 2 focused tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M5.2 PACKAGE 2 COMPLETE" -ForegroundColor Green

git status --short
