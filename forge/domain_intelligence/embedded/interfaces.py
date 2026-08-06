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