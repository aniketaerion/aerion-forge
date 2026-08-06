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