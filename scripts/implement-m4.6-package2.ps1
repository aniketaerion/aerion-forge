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

Write-Utf8NoBom "forge\domain_intelligence\embedded\interfaces.py" @'
"""Embedded interface discovery for M4.6 Package 2."""

from __future__ import annotations

import re
from pathlib import Path

from forge.domain_intelligence.embedded.identifiers import (
    embedded_interface_identifier,
)
from forge.domain_intelligence.embedded.models import (
    EmbeddedInterface,
    EmbeddedInterfaceKind,
)

_INTERFACE_PATTERNS: tuple[
    tuple[EmbeddedInterfaceKind, re.Pattern[str]],
    ...,
] = (
    (
        EmbeddedInterfaceKind.MAVLINK,
        re.compile(r"\bmavlink(?:\b|_)", re.IGNORECASE),
    ),
    (
        EmbeddedInterfaceKind.ROS_TOPIC,
        re.compile(r"\bcreate_(?:publisher|subscription)\b"),
    ),
    (
        EmbeddedInterfaceKind.ROS_SERVICE,
        re.compile(r"\bcreate_service\b"),
    ),
    (
        EmbeddedInterfaceKind.ROS_ACTION,
        re.compile(r"\bActionServer\b|\bActionClient\b"),
    ),
    (
        EmbeddedInterfaceKind.UART,
        re.compile(r"\bUART(?:\b|_|\d)|\busart\d*\b", re.IGNORECASE),
    ),
    (
        EmbeddedInterfaceKind.CAN,
        re.compile(r"\bCAN\b|\bcan\d+\b"),
    ),
    (
        EmbeddedInterfaceKind.I2C,
        re.compile(r"\bI2C\b|\bi2c\d*\b", re.IGNORECASE),
    ),
    (
        EmbeddedInterfaceKind.SPI,
        re.compile(r"\bSPI\b|\bspi\d*\b", re.IGNORECASE),
    ),
    (
        EmbeddedInterfaceKind.ETHERNET,
        re.compile(r"\bethernet\b|\bUDP\b|\bTCP\b"),
    ),
)

_TEXT_SUFFIXES = {
    ".c",
    ".cc",
    ".cpp",
    ".cxx",
    ".h",
    ".hh",
    ".hpp",
    ".hxx",
    ".py",
    ".xml",
    ".msg",
    ".srv",
    ".action",
}


def discover_embedded_interfaces(
    project_root: Path,
) -> tuple[EmbeddedInterface, ...]:
    """Discover embedded communication interfaces."""
    interfaces: list[EmbeddedInterface] = []

    for path in sorted(project_root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in _TEXT_SUFFIXES:
            continue

        if any(
            excluded in path.parts
            for excluded in (
                ".git",
                ".venv",
                "venv",
                "build",
                "install",
                "dist",
                "__pycache__",
            )
        ):
            continue

        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        relative = path.relative_to(project_root).as_posix()

        for kind, pattern in _INTERFACE_PATTERNS:
            if not pattern.search(content):
                continue

            payload = {
                "kind": kind.value,
                "path": relative,
            }
            interfaces.append(
                EmbeddedInterface(
                    interface_id=embedded_interface_identifier(payload),
                    name=f"{kind.value}:{relative}",
                    kind=kind,
                    source_path=relative,
                )
            )

    return tuple(
        sorted(
            interfaces,
            key=lambda item: (
                item.kind.value,
                item.source_path or "",
                item.interface_id,
            ),
        )
    )
'@

Write-Utf8NoBom "forge\domain_intelligence\embedded\messages.py" @'
"""Embedded message discovery for M4.6 Package 2."""

from __future__ import annotations

from pathlib import Path

from forge.domain_intelligence.embedded.identifiers import (
    embedded_message_identifier,
)
from forge.domain_intelligence.embedded.models import EmbeddedMessage


def _message_fields(path: Path) -> tuple[str, ...]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return ()

    fields: list[str] = []

    for line in lines:
        candidate = line.strip()
        if (
            not candidate
            or candidate.startswith("#")
            or candidate == "---"
            or "=" in candidate
        ):
            continue

        parts = candidate.split()
        if len(parts) >= 2:
            fields.append(parts[-1])

    return tuple(fields)


def discover_embedded_messages(
    project_root: Path,
) -> tuple[EmbeddedMessage, ...]:
    """Discover ROS and MAVLink-style message definitions."""
    messages: list[EmbeddedMessage] = []

    for suffix, protocol in (
        (".msg", "ros2"),
        (".srv", "ros2-service"),
        (".action", "ros2-action"),
        (".xml", "mavlink"),
    ):
        for path in sorted(project_root.rglob(f"*{suffix}")):
            if any(
                excluded in path.parts
                for excluded in (
                    ".git",
                    ".venv",
                    "venv",
                    "build",
                    "install",
                    "dist",
                )
            ):
                continue

            relative = path.relative_to(project_root).as_posix()
            payload = {
                "name": path.stem,
                "protocol": protocol,
                "path": relative,
            }
            messages.append(
                EmbeddedMessage(
                    message_id=embedded_message_identifier(payload),
                    name=path.stem,
                    protocol=protocol,
                    fields=_message_fields(path),
                    source_path=relative,
                )
            )

    return tuple(
        sorted(
            messages,
            key=lambda item: (
                item.protocol,
                item.name,
                item.source_path or "",
            ),
        )
    )
'@

Write-Utf8NoBom "forge\domain_intelligence\embedded\safety.py" @'
"""Static embedded safety analysis for M4.6 Package 2."""

from __future__ import annotations

import re
from pathlib import Path

from forge.domain_intelligence.embedded.identifiers import (
    embedded_finding_identifier,
)
from forge.domain_intelligence.embedded.models import (
    EmbeddedFinding,
    EmbeddedFindingSeverity,
)

_SAFETY_PATTERNS: tuple[
    tuple[str, EmbeddedFindingSeverity, re.Pattern[str], str],
    ...,
] = (
    (
        "unsafe-memory",
        EmbeddedFindingSeverity.HIGH,
        re.compile(r"\b(?:strcpy|strcat|gets)\s*\("),
        "Potentially unsafe C string operation detected.",
    ),
    (
        "blocking-delay",
        EmbeddedFindingSeverity.MEDIUM,
        re.compile(r"\b(?:sleep|usleep|HAL_Delay)\s*\("),
        "Blocking delay detected in embedded code.",
    ),
    (
        "watchdog",
        EmbeddedFindingSeverity.MEDIUM,
        re.compile(r"\bwatchdog\b", re.IGNORECASE),
        "Watchdog-related logic requires review.",
    ),
    (
        "failsafe",
        EmbeddedFindingSeverity.INFO,
        re.compile(r"\bfailsafe\b", re.IGNORECASE),
        "Failsafe-related logic detected.",
    ),
)

_CODE_SUFFIXES = {
    ".c",
    ".cc",
    ".cpp",
    ".cxx",
    ".h",
    ".hh",
    ".hpp",
    ".hxx",
    ".py",
}


def analyze_embedded_safety(
    project_root: Path,
) -> tuple[EmbeddedFinding, ...]:
    """Produce deterministic safety findings from source text."""
    findings: list[EmbeddedFinding] = []

    for path in sorted(project_root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in _CODE_SUFFIXES:
            continue

        if any(
            excluded in path.parts
            for excluded in (
                ".git",
                ".venv",
                "venv",
                "build",
                "install",
                "dist",
                "__pycache__",
            )
        ):
            continue

        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        relative = path.relative_to(project_root).as_posix()

        for category, severity, pattern, message in _SAFETY_PATTERNS:
            if not pattern.search(content):
                continue

            payload = {
                "category": category,
                "path": relative,
                "message": message,
            }
            findings.append(
                EmbeddedFinding(
                    finding_id=embedded_finding_identifier(payload),
                    category=category,
                    severity=severity,
                    message=message,
                    path=relative,
                )
            )

    return tuple(
        sorted(
            findings,
            key=lambda item: (
                item.severity.value,
                item.category,
                item.path or "",
                item.finding_id,
            ),
        )
    )
'@

$ServicePath = ".\forge\domain_intelligence\embedded\service.py"
$ServiceContent = Get-Content $ServicePath -Raw

if (
    $ServiceContent -notmatch
    'from forge\.domain_intelligence\.embedded\.interfaces import'
) {
    $Anchor = @'
from forge.domain_intelligence.embedded.identifiers import (
'@
    $Insert = @'
from forge.domain_intelligence.embedded.interfaces import (
    discover_embedded_interfaces,
)
from forge.domain_intelligence.embedded.messages import (
    discover_embedded_messages,
)
from forge.domain_intelligence.embedded.safety import (
    analyze_embedded_safety,
)
from forge.domain_intelligence.embedded.identifiers import (
'@
    if (-not $ServiceContent.Contains($Anchor)) {
        throw "Service import anchor was not found."
    }
    $ServiceContent = $ServiceContent.Replace($Anchor, $Insert)
}

$Old = @'
        components = self._registry.discover_components(
            project_root,
            tuple(
                platform
                for platform in platforms
                if platform is not EmbeddedPlatformKind.UNKNOWN
            ),
        )
        build_files = discover_embedded_build_files(project_root)
'@

$New = @'
        components = self._registry.discover_components(
            project_root,
            tuple(
                platform
                for platform in platforms
                if platform is not EmbeddedPlatformKind.UNKNOWN
            ),
        )
        build_files = discover_embedded_build_files(project_root)
        interfaces = discover_embedded_interfaces(project_root)
        messages = discover_embedded_messages(project_root)
'@

if ($ServiceContent.Contains($Old)) {
    $ServiceContent = $ServiceContent.Replace($Old, $New)
}

$Old = @'
        findings: tuple[EmbeddedFinding, ...] = ()
        if platforms == (EmbeddedPlatformKind.UNKNOWN,):
'@

$New = @'
        findings = analyze_embedded_safety(project_root)

        if platforms == (EmbeddedPlatformKind.UNKNOWN,):
'@

if ($ServiceContent.Contains($Old)) {
    $ServiceContent = $ServiceContent.Replace($Old, $New)
}

$Old = @'
            findings = (
                EmbeddedFinding(
                    finding_id=embedded_finding_identifier(
                        finding_payload
                    ),
                    category="platform",
                    severity=EmbeddedFindingSeverity.INFO,
                    message=(
                        "No supported embedded platform detected."
                    ),
                    path=relative_root,
                ),
            )
'@

$New = @'
            findings = (
                *findings,
                EmbeddedFinding(
                    finding_id=embedded_finding_identifier(
                        finding_payload
                    ),
                    category="platform",
                    severity=EmbeddedFindingSeverity.INFO,
                    message=(
                        "No supported embedded platform detected."
                    ),
                    path=relative_root,
                ),
            )
'@

if ($ServiceContent.Contains($Old)) {
    $ServiceContent = $ServiceContent.Replace($Old, $New)
}

$Old = @'
            components=components,
            findings=findings,
        )
'@

$New = @'
            components=components,
            interfaces=interfaces,
            messages=messages,
            findings=findings,
        )
'@

if ($ServiceContent.Contains($Old)) {
    $ServiceContent = $ServiceContent.Replace($Old, $New)
}

[System.IO.File]::WriteAllText(
    (Resolve-Path $ServicePath),
    $ServiceContent,
    [System.Text.UTF8Encoding]::new($false)
)

Write-Host "UPDATED forge\domain_intelligence\embedded\service.py" -ForegroundColor Green

Write-Utf8NoBom "tests\test_domain_intelligence_embedded_interfaces.py" @'
from pathlib import Path

from forge.domain_intelligence.embedded.interfaces import (
    discover_embedded_interfaces,
)
from forge.domain_intelligence.embedded.models import (
    EmbeddedInterfaceKind,
)


def test_embedded_interface_discovery(tmp_path: Path) -> None:
    (tmp_path / "driver.cpp").write_text(
        "UART_Init();\nMAVLINK_MSG_ID_HEARTBEAT;\n",
        encoding="utf-8",
    )

    interfaces = discover_embedded_interfaces(tmp_path)
    kinds = {interface.kind for interface in interfaces}

    assert EmbeddedInterfaceKind.UART in kinds
    assert EmbeddedInterfaceKind.MAVLINK in kinds
'@

Write-Utf8NoBom "tests\test_domain_intelligence_embedded_messages.py" @'
from pathlib import Path

from forge.domain_intelligence.embedded.messages import (
    discover_embedded_messages,
)


def test_embedded_message_discovery(tmp_path: Path) -> None:
    msg = tmp_path / "msg"
    msg.mkdir()
    (msg / "VehicleState.msg").write_text(
        "float32 latitude\nfloat32 longitude\n",
        encoding="utf-8",
    )

    messages = discover_embedded_messages(tmp_path)

    assert len(messages) == 1
    assert messages[0].name == "VehicleState"
    assert messages[0].fields == ("latitude", "longitude")
'@

Write-Utf8NoBom "tests\test_domain_intelligence_embedded_safety.py" @'
from pathlib import Path

from forge.domain_intelligence.embedded.safety import (
    analyze_embedded_safety,
)


def test_embedded_safety_analysis(tmp_path: Path) -> None:
    (tmp_path / "control.c").write_text(
        "strcpy(target, source);\nHAL_Delay(100);\n",
        encoding="utf-8",
    )

    findings = analyze_embedded_safety(tmp_path)
    categories = {finding.category for finding in findings}

    assert "unsafe-memory" in categories
    assert "blocking-delay" in categories
'@

Write-Utf8NoBom "tests\test_domain_intelligence_embedded_service.py" @'
from pathlib import Path

from forge.domain_intelligence.embedded.models import (
    EmbeddedAnalysisRequest,
    EmbeddedPlatformKind,
)
from forge.domain_intelligence.embedded.service import (
    EmbeddedIntelligenceService,
)


def initialize_repository(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()


def test_embedded_service_analyzes_px4_project(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)
    module = tmp_path / "src" / "modules" / "navigator"
    module.mkdir(parents=True)
    (tmp_path / "CMakeLists.txt").write_text(
        "project(px4)",
        encoding="utf-8",
    )
    (tmp_path / "vehicle.msg").write_text(
        "float32 latitude\n",
        encoding="utf-8",
    )
    (module / "navigator.cpp").write_text(
        "UART_Init();\n",
        encoding="utf-8",
    )

    report = EmbeddedIntelligenceService().analyze(
        EmbeddedAnalysisRequest(
            repository_root=str(tmp_path),
        )
    )

    assert report.project.platforms == (
        EmbeddedPlatformKind.PX4,
    )
    assert report.components[0].name == "navigator"
    assert report.project.build_files == ("CMakeLists.txt",)
    assert len(report.interfaces) >= 1
    assert len(report.messages) == 1


def test_embedded_service_reports_unknown_project(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    report = EmbeddedIntelligenceService().analyze(
        EmbeddedAnalysisRequest(
            repository_root=str(tmp_path),
        )
    )

    assert report.project.platforms == (
        EmbeddedPlatformKind.UNKNOWN,
    )
    assert any(
        finding.category == "platform"
        for finding in report.findings
    )
'@

Write-Host ""
Write-Host "M4.6 Package 2 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_domain_intelligence_embedded_interfaces.py `
    .\tests\test_domain_intelligence_embedded_messages.py `
    .\tests\test_domain_intelligence_embedded_safety.py `
    .\tests\test_domain_intelligence_embedded_service.py `
    -p no:cacheprovider
Assert-CommandSuccess "M4.6 Package 2 tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M4.6 PACKAGE 2 COMPLETE" -ForegroundColor Green

git status --short
