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

Write-Utf8NoBom "forge\domain_intelligence\embedded\px4.py" @'
"""PX4 repository discovery for M4.6 Package 1."""

from __future__ import annotations

from pathlib import Path

from forge.domain_intelligence.embedded.models import (
    EmbeddedComponent,
    EmbeddedComponentKind,
    EmbeddedPlatformKind,
)
from forge.domain_intelligence.embedded.identifiers import (
    embedded_component_identifier,
)


def detect_px4(project_root: Path) -> bool:
    """Return whether a repository contains strong PX4 markers."""
    markers = (
        project_root / "src" / "modules",
        project_root / "boards",
        project_root / "ROMFS",
    )
    named_markers = (
        project_root / "px4_fmu-v5_default",
        project_root / "msg",
    )
    return (
        any(path.exists() for path in markers)
        and (
            (project_root / "CMakeLists.txt").is_file()
            or (project_root / "Tools").is_dir()
        )
    ) or any(path.exists() for path in named_markers)


def discover_px4_components(
    project_root: Path,
) -> tuple[EmbeddedComponent, ...]:
    """Discover PX4 modules as embedded components."""
    modules_root = project_root / "src" / "modules"
    if not modules_root.is_dir():
        return ()

    components: list[EmbeddedComponent] = []

    for path in sorted(modules_root.iterdir()):
        if not path.is_dir():
            continue

        relative = path.relative_to(project_root).as_posix()
        payload = {
            "name": path.name,
            "platform": EmbeddedPlatformKind.PX4.value,
            "path": relative,
        }
        components.append(
            EmbeddedComponent(
                component_id=embedded_component_identifier(payload),
                name=path.name,
                kind=EmbeddedComponentKind.AUTOPILOT_MODULE,
                platform=EmbeddedPlatformKind.PX4,
                source_paths=(relative,),
            )
        )

    return tuple(components)
'@

Write-Utf8NoBom "forge\domain_intelligence\embedded\ardupilot.py" @'
"""ArduPilot repository discovery for M4.6 Package 1."""

from __future__ import annotations

from pathlib import Path

from forge.domain_intelligence.embedded.identifiers import (
    embedded_component_identifier,
)
from forge.domain_intelligence.embedded.models import (
    EmbeddedComponent,
    EmbeddedComponentKind,
    EmbeddedPlatformKind,
)

_VEHICLE_DIRECTORIES = (
    "ArduCopter",
    "ArduPlane",
    "Rover",
    "ArduSub",
    "Blimp",
    "AntennaTracker",
)


def detect_ardupilot(project_root: Path) -> bool:
    """Return whether a repository contains ArduPilot markers."""
    has_vehicle = any(
        (project_root / name).is_dir()
        for name in _VEHICLE_DIRECTORIES
    )
    return has_vehicle and (
        (project_root / "libraries").is_dir()
        or (project_root / "waf").exists()
    )


def discover_ardupilot_components(
    project_root: Path,
) -> tuple[EmbeddedComponent, ...]:
    """Discover ArduPilot vehicle stacks."""
    components: list[EmbeddedComponent] = []

    for name in _VEHICLE_DIRECTORIES:
        path = project_root / name
        if not path.is_dir():
            continue

        relative = path.relative_to(project_root).as_posix()
        payload = {
            "name": name,
            "platform": EmbeddedPlatformKind.ARDUPILOT.value,
            "path": relative,
        }
        components.append(
            EmbeddedComponent(
                component_id=embedded_component_identifier(payload),
                name=name,
                kind=EmbeddedComponentKind.FLIGHT_STACK,
                platform=EmbeddedPlatformKind.ARDUPILOT,
                source_paths=(relative,),
            )
        )

    return tuple(components)
'@

Write-Utf8NoBom "forge\domain_intelligence\embedded\ros2.py" @'
"""ROS 2 repository discovery for M4.6 Package 1."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from forge.domain_intelligence.embedded.identifiers import (
    embedded_component_identifier,
)
from forge.domain_intelligence.embedded.models import (
    EmbeddedComponent,
    EmbeddedComponentKind,
    EmbeddedPlatformKind,
)


def detect_ros2(project_root: Path) -> bool:
    """Return whether a repository contains ROS 2 packages."""
    return bool(tuple(project_root.rglob("package.xml")))


def discover_ros2_components(
    project_root: Path,
) -> tuple[EmbeddedComponent, ...]:
    """Discover ROS 2 packages from package.xml files."""
    components: list[EmbeddedComponent] = []

    for package_file in sorted(project_root.rglob("package.xml")):
        if any(
            excluded in package_file.parts
            for excluded in (
                ".git",
                ".venv",
                "venv",
                "build",
                "install",
                "log",
            )
        ):
            continue

        name = package_file.parent.name
        try:
            root = ET.fromstring(
                package_file.read_text(encoding="utf-8")
            )
            node = root.find("name")
            if node is not None and node.text:
                name = node.text.strip()
        except (ET.ParseError, OSError, UnicodeDecodeError):
            pass

        relative = package_file.parent.relative_to(
            project_root
        ).as_posix()
        payload = {
            "name": name,
            "platform": EmbeddedPlatformKind.ROS2.value,
            "path": relative,
        }
        components.append(
            EmbeddedComponent(
                component_id=embedded_component_identifier(payload),
                name=name,
                kind=EmbeddedComponentKind.ROS2_NODE,
                platform=EmbeddedPlatformKind.ROS2,
                source_paths=(relative,),
            )
        )

    return tuple(components)
'@

Write-Utf8NoBom "forge\domain_intelligence\embedded\stm32.py" @'
"""STM32 repository discovery for M4.6 Package 1."""

from __future__ import annotations

from pathlib import Path

from forge.domain_intelligence.embedded.identifiers import (
    embedded_component_identifier,
)
from forge.domain_intelligence.embedded.models import (
    EmbeddedComponent,
    EmbeddedComponentKind,
    EmbeddedPlatformKind,
)


def detect_stm32(project_root: Path) -> bool:
    """Return whether a repository contains STM32 markers."""
    return bool(
        tuple(project_root.rglob("*.ioc"))
        or tuple(project_root.rglob("stm32*.ld"))
        or (project_root / "Core").is_dir()
    )


def discover_stm32_components(
    project_root: Path,
) -> tuple[EmbeddedComponent, ...]:
    """Discover STM32 Cube projects from .ioc files."""
    components: list[EmbeddedComponent] = []

    for ioc_file in sorted(project_root.rglob("*.ioc")):
        if any(
            excluded in ioc_file.parts
            for excluded in (
                ".git",
                ".venv",
                "venv",
                "build",
            )
        ):
            continue

        relative = ioc_file.relative_to(project_root).as_posix()
        name = ioc_file.stem
        payload = {
            "name": name,
            "platform": EmbeddedPlatformKind.STM32.value,
            "path": relative,
        }
        components.append(
            EmbeddedComponent(
                component_id=embedded_component_identifier(payload),
                name=name,
                kind=EmbeddedComponentKind.FIRMWARE,
                platform=EmbeddedPlatformKind.STM32,
                source_paths=(relative,),
            )
        )

    return tuple(components)
'@

Write-Utf8NoBom "forge\domain_intelligence\embedded\build_systems.py" @'
"""Embedded build-system discovery for M4.6 Package 1."""

from __future__ import annotations

from pathlib import Path

_BUILD_FILES = (
    "CMakeLists.txt",
    "platformio.ini",
    "Makefile",
    "meson.build",
    "BUILD",
    "BUILD.bazel",
    "wscript",
    "west.yml",
)


def discover_embedded_build_files(
    project_root: Path,
) -> tuple[str, ...]:
    """Discover common embedded build-system files."""
    found: set[str] = set()

    for name in _BUILD_FILES:
        for path in project_root.rglob(name):
            if not path.is_file():
                continue
            if any(
                excluded in path.parts
                for excluded in (
                    ".git",
                    ".venv",
                    "venv",
                    "node_modules",
                    "__pycache__",
                    "dist",
                    "build",
                    "install",
                )
            ):
                continue
            found.add(path.relative_to(project_root).as_posix())

    return tuple(sorted(found))
'@

Write-Utf8NoBom "forge\domain_intelligence\embedded\registry.py" @'
"""Analyzer registry for M4.6 Embedded Domain Intelligence."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from forge.domain_intelligence.embedded.ardupilot import (
    detect_ardupilot,
    discover_ardupilot_components,
)
from forge.domain_intelligence.embedded.models import (
    EmbeddedComponent,
    EmbeddedPlatformKind,
)
from forge.domain_intelligence.embedded.px4 import (
    detect_px4,
    discover_px4_components,
)
from forge.domain_intelligence.embedded.ros2 import (
    detect_ros2,
    discover_ros2_components,
)
from forge.domain_intelligence.embedded.stm32 import (
    detect_stm32,
    discover_stm32_components,
)

Detector = Callable[[Path], bool]
ComponentDiscoverer = Callable[
    [Path],
    tuple[EmbeddedComponent, ...],
]


class EmbeddedAnalyzerRegistry:
    """Deterministic registry of embedded-platform analyzers."""

    def __init__(self) -> None:
        self._detectors: dict[EmbeddedPlatformKind, Detector] = {}
        self._discoverers: dict[
            EmbeddedPlatformKind,
            ComponentDiscoverer,
        ] = {}

    @classmethod
    def default(cls) -> "EmbeddedAnalyzerRegistry":
        registry = cls()
        registry.register(
            EmbeddedPlatformKind.PX4,
            detect_px4,
            discover_px4_components,
        )
        registry.register(
            EmbeddedPlatformKind.ARDUPILOT,
            detect_ardupilot,
            discover_ardupilot_components,
        )
        registry.register(
            EmbeddedPlatformKind.ROS2,
            detect_ros2,
            discover_ros2_components,
        )
        registry.register(
            EmbeddedPlatformKind.STM32,
            detect_stm32,
            discover_stm32_components,
        )
        return registry

    def register(
        self,
        platform: EmbeddedPlatformKind,
        detector: Detector,
        discoverer: ComponentDiscoverer,
    ) -> None:
        self._detectors[platform] = detector
        self._discoverers[platform] = discoverer

    def platforms(self) -> tuple[EmbeddedPlatformKind, ...]:
        return tuple(
            sorted(
                self._detectors,
                key=lambda item: item.value,
            )
        )

    def detect(
        self,
        project_root: Path,
    ) -> tuple[EmbeddedPlatformKind, ...]:
        return tuple(
            platform
            for platform in self.platforms()
            if self._detectors[platform](project_root)
        )

    def discover_components(
        self,
        project_root: Path,
        platforms: tuple[EmbeddedPlatformKind, ...],
    ) -> tuple[EmbeddedComponent, ...]:
        components: list[EmbeddedComponent] = []

        for platform in platforms:
            discoverer = self._discoverers.get(platform)
            if discoverer is not None:
                components.extend(discoverer(project_root))

        return tuple(
            sorted(
                components,
                key=lambda item: (
                    item.platform.value,
                    item.name,
                    item.component_id,
                ),
            )
        )
'@

Write-Utf8NoBom "forge\domain_intelligence\embedded\service.py" @'
"""Embedded analysis service for M4.6 Package 1."""

from __future__ import annotations

from pathlib import Path

from forge.domain_intelligence.embedded.build_systems import (
    discover_embedded_build_files,
)
from forge.domain_intelligence.embedded.identifiers import (
    embedded_finding_identifier,
    embedded_project_identifier,
    embedded_report_identifier,
)
from forge.domain_intelligence.embedded.models import (
    EmbeddedAnalysisReport,
    EmbeddedAnalysisRequest,
    EmbeddedFinding,
    EmbeddedFindingSeverity,
    EmbeddedPlatformKind,
    EmbeddedProject,
)
from forge.domain_intelligence.embedded.policies import (
    EmbeddedIntelligencePolicy,
    resolve_embedded_repository_root,
    validate_embedded_request,
)
from forge.domain_intelligence.embedded.registry import (
    EmbeddedAnalyzerRegistry,
)


class EmbeddedIntelligenceService:
    """Perform deterministic, offline embedded analysis."""

    def __init__(
        self,
        *,
        policy: EmbeddedIntelligencePolicy | None = None,
        registry: EmbeddedAnalyzerRegistry | None = None,
    ) -> None:
        self._policy = policy or EmbeddedIntelligencePolicy()
        self._registry = (
            registry or EmbeddedAnalyzerRegistry.default()
        )

    def analyze(
        self,
        request: EmbeddedAnalysisRequest,
    ) -> EmbeddedAnalysisReport:
        validate_embedded_request(request, self._policy)
        repository_root = resolve_embedded_repository_root(
            request.repository_root,
            self._policy,
        )
        project_root = (
            repository_root / request.project_root
        ).resolve()

        if not project_root.is_dir():
            raise ValueError(
                f"embedded project root does not exist: {project_root}"
            )

        platforms = self._registry.detect(project_root)
        if not platforms:
            platforms = (EmbeddedPlatformKind.UNKNOWN,)

        components = self._registry.discover_components(
            project_root,
            tuple(
                platform
                for platform in platforms
                if platform is not EmbeddedPlatformKind.UNKNOWN
            ),
        )
        build_files = discover_embedded_build_files(project_root)

        relative_root = project_root.relative_to(
            repository_root
        ).as_posix()
        project_payload = {
            "root": relative_root,
            "platforms": tuple(
                platform.value for platform in platforms
            ),
            "build_files": build_files,
        }

        findings: tuple[EmbeddedFinding, ...] = ()
        if platforms == (EmbeddedPlatformKind.UNKNOWN,):
            finding_payload = {
                "category": "platform",
                "path": relative_root,
                "message": "No supported embedded platform detected.",
            }
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

        project = EmbeddedProject(
            project_id=embedded_project_identifier(
                project_payload
            ),
            root=relative_root,
            platforms=platforms,
            build_files=build_files,
        )

        report_payload = {
            "project_id": project.project_id,
            "component_ids": tuple(
                component.component_id
                for component in components
            ),
            "finding_ids": tuple(
                finding.finding_id for finding in findings
            ),
        }

        return EmbeddedAnalysisReport(
            report_id=embedded_report_identifier(
                report_payload
            ),
            project=project,
            components=components,
            findings=findings,
        )
'@

Write-Utf8NoBom "tests\test_domain_intelligence_embedded_px4.py" @'
from pathlib import Path

from forge.domain_intelligence.embedded.px4 import (
    detect_px4,
    discover_px4_components,
)


def test_px4_detection_and_components(tmp_path: Path) -> None:
    modules = tmp_path / "src" / "modules" / "navigator"
    modules.mkdir(parents=True)
    (tmp_path / "CMakeLists.txt").write_text(
        "project(px4)",
        encoding="utf-8",
    )

    assert detect_px4(tmp_path)
    components = discover_px4_components(tmp_path)

    assert len(components) == 1
    assert components[0].name == "navigator"
'@

Write-Utf8NoBom "tests\test_domain_intelligence_embedded_ardupilot.py" @'
from pathlib import Path

from forge.domain_intelligence.embedded.ardupilot import (
    detect_ardupilot,
    discover_ardupilot_components,
)


def test_ardupilot_detection_and_components(
    tmp_path: Path,
) -> None:
    (tmp_path / "ArduCopter").mkdir()
    (tmp_path / "libraries").mkdir()

    assert detect_ardupilot(tmp_path)
    components = discover_ardupilot_components(tmp_path)

    assert len(components) == 1
    assert components[0].name == "ArduCopter"
'@

Write-Utf8NoBom "tests\test_domain_intelligence_embedded_ros2.py" @'
from pathlib import Path

from forge.domain_intelligence.embedded.ros2 import (
    detect_ros2,
    discover_ros2_components,
)


def test_ros2_detection_and_components(tmp_path: Path) -> None:
    package = tmp_path / "src" / "camera_node"
    package.mkdir(parents=True)
    (package / "package.xml").write_text(
        "<package><name>camera_node</name></package>",
        encoding="utf-8",
    )

    assert detect_ros2(tmp_path)
    components = discover_ros2_components(tmp_path)

    assert len(components) == 1
    assert components[0].name == "camera_node"
'@

Write-Utf8NoBom "tests\test_domain_intelligence_embedded_stm32.py" @'
from pathlib import Path

from forge.domain_intelligence.embedded.stm32 import (
    detect_stm32,
    discover_stm32_components,
)


def test_stm32_detection_and_components(tmp_path: Path) -> None:
    (tmp_path / "flight_controller.ioc").write_text(
        "Mcu.Family=STM32F4",
        encoding="utf-8",
    )

    assert detect_stm32(tmp_path)
    components = discover_stm32_components(tmp_path)

    assert len(components) == 1
    assert components[0].name == "flight_controller"
'@

Write-Utf8NoBom "tests\test_domain_intelligence_embedded_build_systems.py" @'
from pathlib import Path

from forge.domain_intelligence.embedded.build_systems import (
    discover_embedded_build_files,
)


def test_embedded_build_file_discovery(
    tmp_path: Path,
) -> None:
    (tmp_path / "CMakeLists.txt").write_text(
        "project(firmware)",
        encoding="utf-8",
    )
    (tmp_path / "platformio.ini").write_text(
        "[env]",
        encoding="utf-8",
    )

    assert discover_embedded_build_files(tmp_path) == (
        "CMakeLists.txt",
        "platformio.ini",
    )
'@

Write-Utf8NoBom "tests\test_domain_intelligence_embedded_registry.py" @'
from pathlib import Path

from forge.domain_intelligence.embedded.models import (
    EmbeddedPlatformKind,
)
from forge.domain_intelligence.embedded.registry import (
    EmbeddedAnalyzerRegistry,
)


def test_default_embedded_registry_detects_px4(
    tmp_path: Path,
) -> None:
    (tmp_path / "src" / "modules").mkdir(parents=True)
    (tmp_path / "CMakeLists.txt").write_text(
        "project(px4)",
        encoding="utf-8",
    )

    registry = EmbeddedAnalyzerRegistry.default()

    assert EmbeddedPlatformKind.PX4 in registry.detect(tmp_path)
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
    assert len(report.findings) == 1
'@

Write-Host ""
Write-Host "M4.6 Package 1 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_domain_intelligence_embedded_px4.py `
    .\tests\test_domain_intelligence_embedded_ardupilot.py `
    .\tests\test_domain_intelligence_embedded_ros2.py `
    .\tests\test_domain_intelligence_embedded_stm32.py `
    .\tests\test_domain_intelligence_embedded_build_systems.py `
    .\tests\test_domain_intelligence_embedded_registry.py `
    .\tests\test_domain_intelligence_embedded_service.py `
    -p no:cacheprovider
Assert-CommandSuccess "M4.6 Package 1 tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M4.6 PACKAGE 1 COMPLETE" -ForegroundColor Green

git status --short
