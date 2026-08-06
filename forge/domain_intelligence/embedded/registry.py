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
    def default(cls) -> EmbeddedAnalyzerRegistry:
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