"""PX4 repository discovery for M4.6 Package 1."""

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