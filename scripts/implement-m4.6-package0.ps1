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

Write-Utf8NoBom "forge\domain_intelligence\embedded\errors.py" @'
"""Typed errors for M4.6 Embedded Domain Intelligence."""

from __future__ import annotations

from forge.domain_intelligence.errors import DomainIntelligenceError


class EmbeddedIntelligenceError(DomainIntelligenceError):
    """Base error for embedded-domain intelligence."""


class EmbeddedConfigurationError(EmbeddedIntelligenceError):
    """Raised when embedded analysis configuration is invalid."""


class EmbeddedPolicyError(EmbeddedIntelligenceError):
    """Raised when embedded analysis violates policy."""


class EmbeddedParseError(EmbeddedIntelligenceError):
    """Raised when an embedded artifact cannot be parsed."""
'@

Write-Utf8NoBom "forge\domain_intelligence\embedded\identifiers.py" @'
"""Deterministic identifiers for M4.6 Embedded Domain Intelligence."""

from __future__ import annotations

from typing import Any

from forge.domain_intelligence.identifiers import stable_identifier


def embedded_project_identifier(payload: Any) -> str:
    return stable_identifier("embedded-project", payload)


def embedded_component_identifier(payload: Any) -> str:
    return stable_identifier("embedded-component", payload)


def embedded_interface_identifier(payload: Any) -> str:
    return stable_identifier("embedded-interface", payload)


def embedded_message_identifier(payload: Any) -> str:
    return stable_identifier("embedded-message", payload)


def embedded_finding_identifier(payload: Any) -> str:
    return stable_identifier("embedded-finding", payload)


def embedded_report_identifier(payload: Any) -> str:
    return stable_identifier("embedded-report", payload)
'@

Write-Utf8NoBom "forge\domain_intelligence\embedded\models.py" @'
"""Immutable contracts for M4.6 Embedded Domain Intelligence."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EmbeddedPlatformKind(StrEnum):
    PX4 = "px4"
    ARDUPILOT = "ardupilot"
    ROS2 = "ros2"
    STM32 = "stm32"
    GENERIC = "generic"
    UNKNOWN = "unknown"


class EmbeddedComponentKind(StrEnum):
    FLIGHT_STACK = "flight_stack"
    AUTOPILOT_MODULE = "autopilot_module"
    ROS2_NODE = "ros2_node"
    DRIVER = "driver"
    FIRMWARE = "firmware"
    BOARD_SUPPORT = "board_support"
    SENSOR = "sensor"
    ACTUATOR = "actuator"
    COMMUNICATION = "communication"
    BUILD_SYSTEM = "build_system"
    UNKNOWN = "unknown"


class EmbeddedInterfaceKind(StrEnum):
    MAVLINK = "mavlink"
    DDS = "dds"
    ROS_TOPIC = "ros_topic"
    ROS_SERVICE = "ros_service"
    ROS_ACTION = "ros_action"
    UART = "uart"
    CAN = "can"
    I2C = "i2c"
    SPI = "spi"
    GPIO = "gpio"
    ETHERNET = "ethernet"
    UNKNOWN = "unknown"


class EmbeddedFindingSeverity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ImmutableEmbeddedModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
    )


class EmbeddedAnalysisRequest(ImmutableEmbeddedModel):
    repository_root: str = Field(min_length=1)
    project_root: str = Field(default=".", min_length=1)
    max_files: int = Field(default=10000, ge=1, le=100000)


class EmbeddedComponent(ImmutableEmbeddedModel):
    component_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    kind: EmbeddedComponentKind
    platform: EmbeddedPlatformKind
    source_paths: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()


class EmbeddedInterface(ImmutableEmbeddedModel):
    interface_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    kind: EmbeddedInterfaceKind
    producer: str | None = None
    consumers: tuple[str, ...] = ()
    source_path: str | None = None


class EmbeddedMessage(ImmutableEmbeddedModel):
    message_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    protocol: str = Field(min_length=1)
    fields: tuple[str, ...] = ()
    source_path: str | None = None


class EmbeddedProject(ImmutableEmbeddedModel):
    project_id: str = Field(min_length=1)
    root: str = Field(min_length=1)
    platforms: tuple[EmbeddedPlatformKind, ...] = ()
    source_files: tuple[str, ...] = ()
    configuration_files: tuple[str, ...] = ()
    build_files: tuple[str, ...] = ()
    detected_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )

    @field_validator("platforms")
    @classmethod
    def ensure_unique_platforms(
        cls,
        platforms: tuple[EmbeddedPlatformKind, ...],
    ) -> tuple[EmbeddedPlatformKind, ...]:
        if len(platforms) != len(set(platforms)):
            raise ValueError("embedded platforms must be unique")
        return platforms


class EmbeddedFinding(ImmutableEmbeddedModel):
    finding_id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    severity: EmbeddedFindingSeverity
    message: str = Field(min_length=1)
    path: str | None = None
    evidence: dict[str, str] = Field(default_factory=dict)


class EmbeddedAnalysisReport(ImmutableEmbeddedModel):
    report_id: str = Field(min_length=1)
    project: EmbeddedProject
    components: tuple[EmbeddedComponent, ...] = ()
    interfaces: tuple[EmbeddedInterface, ...] = ()
    messages: tuple[EmbeddedMessage, ...] = ()
    findings: tuple[EmbeddedFinding, ...] = ()
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )

    @field_validator("findings")
    @classmethod
    def ensure_unique_findings(
        cls,
        findings: tuple[EmbeddedFinding, ...],
    ) -> tuple[EmbeddedFinding, ...]:
        identifiers = [finding.finding_id for finding in findings]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError(
                "embedded finding identifiers must be unique"
            )
        return findings
'@

Write-Utf8NoBom "forge\domain_intelligence\embedded\policies.py" @'
"""Safety policies for M4.6 Embedded Domain Intelligence."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from forge.domain_intelligence.embedded.errors import (
    EmbeddedPolicyError,
)
from forge.domain_intelligence.embedded.models import (
    EmbeddedAnalysisRequest,
)


class EmbeddedIntelligencePolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    allow_network: bool = False
    allow_device_access: bool = False
    allow_serial_access: bool = False
    allow_firmware_flash: bool = False
    allow_build_execution: bool = False
    allow_mutation: bool = False
    require_repository_root: bool = True
    max_files: int = Field(default=10000, ge=1, le=100000)
    max_file_bytes: int = Field(
        default=5_000_000,
        ge=1,
        le=100_000_000,
    )


def resolve_embedded_repository_root(
    repository_root: str | Path,
    policy: EmbeddedIntelligencePolicy,
) -> Path:
    root = Path(repository_root).expanduser().resolve()

    if not root.is_dir():
        raise EmbeddedPolicyError(
            f"repository root does not exist: {root}"
        )

    if policy.require_repository_root and not (root / ".git").exists():
        raise EmbeddedPolicyError(
            f"repository root is not a Git repository: {root}"
        )

    return root


def validate_embedded_request(
    request: EmbeddedAnalysisRequest,
    policy: EmbeddedIntelligencePolicy,
) -> None:
    if request.max_files > policy.max_files:
        raise EmbeddedPolicyError(
            f"request exceeds maximum file count: {policy.max_files}"
        )

    project_root = Path(request.project_root)

    if project_root.is_absolute() or ".." in project_root.parts:
        raise EmbeddedPolicyError(
            "project root must remain repository-relative"
        )
'@

Write-Utf8NoBom "forge\domain_intelligence\embedded\__init__.py" @'
"""M4.6 Embedded Domain Intelligence public API."""

from forge.domain_intelligence.embedded.errors import (
    EmbeddedConfigurationError,
    EmbeddedIntelligenceError,
    EmbeddedParseError,
    EmbeddedPolicyError,
)
from forge.domain_intelligence.embedded.identifiers import (
    embedded_component_identifier,
    embedded_finding_identifier,
    embedded_interface_identifier,
    embedded_message_identifier,
    embedded_project_identifier,
    embedded_report_identifier,
)
from forge.domain_intelligence.embedded.models import (
    EmbeddedAnalysisReport,
    EmbeddedAnalysisRequest,
    EmbeddedComponent,
    EmbeddedComponentKind,
    EmbeddedFinding,
    EmbeddedFindingSeverity,
    EmbeddedInterface,
    EmbeddedInterfaceKind,
    EmbeddedMessage,
    EmbeddedPlatformKind,
    EmbeddedProject,
)
from forge.domain_intelligence.embedded.policies import (
    EmbeddedIntelligencePolicy,
    resolve_embedded_repository_root,
    validate_embedded_request,
)

__all__ = [
    "EmbeddedAnalysisReport",
    "EmbeddedAnalysisRequest",
    "EmbeddedComponent",
    "EmbeddedComponentKind",
    "EmbeddedConfigurationError",
    "EmbeddedFinding",
    "EmbeddedFindingSeverity",
    "EmbeddedIntelligenceError",
    "EmbeddedIntelligencePolicy",
    "EmbeddedInterface",
    "EmbeddedInterfaceKind",
    "EmbeddedMessage",
    "EmbeddedParseError",
    "EmbeddedPlatformKind",
    "EmbeddedPolicyError",
    "EmbeddedProject",
    "embedded_component_identifier",
    "embedded_finding_identifier",
    "embedded_interface_identifier",
    "embedded_message_identifier",
    "embedded_project_identifier",
    "embedded_report_identifier",
    "resolve_embedded_repository_root",
    "validate_embedded_request",
]
'@

Write-Utf8NoBom "tests\test_domain_intelligence_embedded_identifiers.py" @'
from forge.domain_intelligence.embedded.identifiers import (
    embedded_component_identifier,
    embedded_project_identifier,
)


def test_embedded_project_identifier_is_deterministic() -> None:
    first = embedded_project_identifier(
        {"root": "firmware", "platform": "px4"}
    )
    second = embedded_project_identifier(
        {"platform": "px4", "root": "firmware"}
    )

    assert first == second
    assert first.startswith("embedded-project-")


def test_embedded_component_identifier_changes_by_platform() -> None:
    first = embedded_component_identifier(
        {"name": "navigator", "platform": "px4"}
    )
    second = embedded_component_identifier(
        {"name": "navigator", "platform": "ardupilot"}
    )

    assert first != second
'@

Write-Utf8NoBom "tests\test_domain_intelligence_embedded_models.py" @'
import pytest
from pydantic import ValidationError

from forge.domain_intelligence.embedded.models import (
    EmbeddedAnalysisReport,
    EmbeddedComponent,
    EmbeddedComponentKind,
    EmbeddedFinding,
    EmbeddedFindingSeverity,
    EmbeddedPlatformKind,
    EmbeddedProject,
)


def test_embedded_component_supports_dependencies() -> None:
    component = EmbeddedComponent(
        component_id="component-1",
        name="navigator",
        kind=EmbeddedComponentKind.AUTOPILOT_MODULE,
        platform=EmbeddedPlatformKind.PX4,
        dependencies=("uorb", "hrt"),
    )

    assert component.platform is EmbeddedPlatformKind.PX4
    assert component.dependencies == ("uorb", "hrt")


def test_embedded_project_rejects_duplicate_platforms() -> None:
    with pytest.raises(ValidationError):
        EmbeddedProject(
            project_id="project-1",
            root="firmware",
            platforms=(
                EmbeddedPlatformKind.PX4,
                EmbeddedPlatformKind.PX4,
            ),
        )


def test_embedded_report_rejects_duplicate_findings() -> None:
    project = EmbeddedProject(
        project_id="project-1",
        root="firmware",
        platforms=(EmbeddedPlatformKind.PX4,),
    )
    finding = EmbeddedFinding(
        finding_id="finding-1",
        category="safety",
        severity=EmbeddedFindingSeverity.HIGH,
        message="Unsafe actuator path.",
    )

    with pytest.raises(ValidationError):
        EmbeddedAnalysisReport(
            report_id="report-1",
            project=project,
            findings=(finding, finding),
        )
'@

Write-Utf8NoBom "tests\test_domain_intelligence_embedded_policies.py" @'
from pathlib import Path

import pytest

from forge.domain_intelligence.embedded.errors import (
    EmbeddedPolicyError,
)
from forge.domain_intelligence.embedded.models import (
    EmbeddedAnalysisRequest,
)
from forge.domain_intelligence.embedded.policies import (
    EmbeddedIntelligencePolicy,
    resolve_embedded_repository_root,
    validate_embedded_request,
)


def test_embedded_policy_is_offline_and_read_only() -> None:
    policy = EmbeddedIntelligencePolicy()

    assert not policy.allow_network
    assert not policy.allow_device_access
    assert not policy.allow_serial_access
    assert not policy.allow_firmware_flash
    assert not policy.allow_build_execution
    assert not policy.allow_mutation


def test_embedded_repository_requires_git(
    tmp_path: Path,
) -> None:
    with pytest.raises(EmbeddedPolicyError):
        resolve_embedded_repository_root(
            tmp_path,
            EmbeddedIntelligencePolicy(),
        )


def test_embedded_request_rejects_path_escape() -> None:
    request = EmbeddedAnalysisRequest(
        repository_root=".",
        project_root="../outside",
    )

    with pytest.raises(EmbeddedPolicyError):
        validate_embedded_request(
            request,
            EmbeddedIntelligencePolicy(),
        )
'@

Write-Utf8NoBom "docs\domain_intelligence\embedded\ARCHITECTURE.md" @'
# M4.6 Embedded Domain Intelligence Architecture

M4.6 provides read-only analysis of embedded software repositories.

Package 0 establishes immutable contracts, deterministic identifiers, typed
errors, and the safety boundary for PX4, ArduPilot, ROS 2, STM32, generic
firmware, interfaces, messages, and build systems.
'@

Write-Utf8NoBom "docs\domain_intelligence\embedded\SPECIFICATION.md" @'
# M4.6 Embedded Domain Intelligence Specification

The subsystem shall discover embedded platforms, components, interfaces,
messages, configuration files, and build artifacts without connecting to
hardware, flashing firmware, opening serial devices, or executing builds.
'@

Write-Utf8NoBom "docs\domain_intelligence\embedded\DATA_MODEL.md" @'
# M4.6 Embedded Domain Intelligence Data Model

Core models:

- `EmbeddedAnalysisRequest`
- `EmbeddedProject`
- `EmbeddedComponent`
- `EmbeddedInterface`
- `EmbeddedMessage`
- `EmbeddedFinding`
- `EmbeddedAnalysisReport`

All models are immutable and reject unknown fields.
'@

Write-Utf8NoBom "docs\domain_intelligence\embedded\SECURITY_MODEL.md" @'
# M4.6 Embedded Domain Intelligence Security Model

Embedded analysis is offline and read-only by default.

The policy prohibits network use, hardware access, serial access, firmware
flashing, build execution, mutation, and project-root escape.
'@

Write-Utf8NoBom "docs\domain_intelligence\embedded\ACCEPTANCE_CRITERIA.md" @'
# M4.6 Package 0 Acceptance Criteria

- Typed embedded errors exist.
- Stable identifiers are deterministic.
- Models are immutable and validated.
- Policies prohibit hardware access and mutation.
- Repository and project-root boundaries are enforced.
- Ruff, MyPy, focused tests, and the complete test suite pass.
'@

Write-Host ""
Write-Host "M4.6 Package 0 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_domain_intelligence_embedded_identifiers.py `
    .\tests\test_domain_intelligence_embedded_models.py `
    .\tests\test_domain_intelligence_embedded_policies.py `
    -p no:cacheprovider
Assert-CommandSuccess "M4.6 Package 0 tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M4.6 PACKAGE 0 COMPLETE" -ForegroundColor Green

git status --short
