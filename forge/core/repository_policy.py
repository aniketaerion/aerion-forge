"""Shared read-only repository traversal policy."""

from pathlib import Path

EXCLUDED_REPOSITORY_DIRECTORIES = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        "__pycache__",
        "build",
        "coverage",
        "dist",
        "htmlcov",
        "memory",
        "node_modules",
        "reports",
        "target",
        "vendor",
    }
)


def is_excluded_directory(path: Path) -> bool:
    """Return whether a directory name is excluded from Forge traversal."""
    return path.name in EXCLUDED_REPOSITORY_DIRECTORIES
