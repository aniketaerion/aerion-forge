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