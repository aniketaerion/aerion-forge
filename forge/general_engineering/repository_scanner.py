"""Read-only repository scanning for M5.9 Package 2."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

_DEFAULT_IGNORED_DIRS = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "dist",
        "build",
        "coverage",
    }
)

_DEFAULT_TEXT_SUFFIXES = frozenset(
    {
        ".py", ".pyi", ".js", ".jsx", ".ts", ".tsx", ".java", ".kt",
        ".dart", ".go", ".rs", ".c", ".h", ".cc", ".cpp", ".hpp",
        ".cs", ".php", ".rb", ".swift", ".sql", ".sh", ".ps1", ".md",
        ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".xml",
        ".html", ".css", ".scss", ".vue", ".svelte",
    }
)


@dataclass(frozen=True)
class ScannedRepositoryFile:
    path: str
    size_bytes: int
    suffix: str
    fingerprint: str
    content: str


def _fingerprint(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def scan_repository(
    repository_root: str | Path,
    *,
    max_file_bytes: int = 1_000_000,
    max_files: int = 5000,
) -> tuple[ScannedRepositoryFile, ...]:
    """Read eligible text files without mutating the repository."""
    root = Path(repository_root).resolve()
    if not root.is_dir():
        raise ValueError(f"Repository root does not exist: {root}")

    scanned: list[ScannedRepositoryFile] = []
    for path in sorted(root.rglob("*")):
        if len(scanned) >= max_files:
            break
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in _DEFAULT_IGNORED_DIRS for part in relative.parts):
            continue
        suffix = path.suffix.casefold()
        if suffix not in _DEFAULT_TEXT_SUFFIXES and path.name not in {
            "Dockerfile", "Makefile", "CMakeLists.txt",
        }:
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size > max_file_bytes:
            continue
        try:
            data = path.read_bytes()
            content = data.decode("utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        scanned.append(
            ScannedRepositoryFile(
                path=relative.as_posix(),
                size_bytes=size,
                suffix=suffix,
                fingerprint=_fingerprint(data),
                content=content,
            )
        )
    return tuple(scanned)