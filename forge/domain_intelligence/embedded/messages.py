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