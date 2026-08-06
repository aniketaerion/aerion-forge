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