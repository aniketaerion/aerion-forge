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