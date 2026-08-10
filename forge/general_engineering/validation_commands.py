"""Bounded validation-command resolution for M5.9 Package 6."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ValidationCommand:
    capability: str
    argv: tuple[str, ...]


def resolve_validation_commands(
    repository_root: str | Path,
    capabilities: tuple[str, ...],
) -> tuple[ValidationCommand, ...]:
    """Resolve known validation capabilities without invoking a shell."""
    root = Path(repository_root).resolve()
    has_python_project = (root / "pyproject.toml").is_file()
    commands: list[ValidationCommand] = []

    for capability in capabilities:
        if capability == "repository_tests" and has_python_project:
            commands.append(
                ValidationCommand(
                    capability=capability,
                    argv=(
                        sys.executable,
                        "-m",
                        "pytest",
                        "-p",
                        "no:cacheprovider",
                    ),
                )
            )
        elif capability == "static_analysis" and has_python_project:
            commands.extend(
                (
                    ValidationCommand(
                        capability=capability,
                        argv=(sys.executable, "-m", "ruff", "check", "."),
                    ),
                    ValidationCommand(
                        capability=capability,
                        argv=(sys.executable, "-m", "mypy", "."),
                    ),
                )
            )
        elif capability == "focused_tests" and has_python_project:
            commands.append(
                ValidationCommand(
                    capability=capability,
                    argv=(
                        sys.executable,
                        "-m",
                        "pytest",
                        "-p",
                        "no:cacheprovider",
                    ),
                )
            )

    unique: list[ValidationCommand] = []
    seen: set[tuple[str, ...]] = set()
    for command in commands:
        if command.argv in seen:
            continue
        seen.add(command.argv)
        unique.append(command)
    return tuple(unique)
