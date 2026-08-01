"""Bounded technology detection for registered workspace roots."""

import json
import shutil
from pathlib import Path
from typing import Any

from forge.workspace.models import TechnologyProfile


def _package_json(root: Path) -> dict[str, Any]:
    path = root / "package.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def detect_technologies(root: Path) -> TechnologyProfile:
    """Detect common tools from repository-root markers and manifests."""
    package = _package_json(root)
    dependencies = {
        str(name).lower()
        for section in ("dependencies", "devDependencies")
        for name in (package.get(section, {}) if isinstance(package.get(section, {}), dict) else {})
    }
    technologies: set[str] = set()
    python = any((root / marker).is_file() for marker in ("pyproject.toml", "requirements.txt"))
    node = bool(package)
    typescript = any(
        (root / marker).is_file() for marker in ("tsconfig.json", "tsconfig.base.json")
    )
    docker = any(
        (root / marker).is_file() for marker in ("Dockerfile", "compose.yaml", "docker-compose.yml")
    )
    git = (root / ".git").is_dir()

    signals = {
        "Python": python,
        "Node": node,
        "React": "react" in dependencies,
        "TypeScript": typescript or "typescript" in dependencies,
        "Docker": docker,
        "PostgreSQL": bool({"pg", "psycopg", "psycopg2", "asyncpg"} & dependencies)
        or (root / "postgresql.conf").is_file(),
        "Prisma": "@prisma/client" in dependencies or (root / "prisma").is_dir(),
        "Redis": "redis" in dependencies or "ioredis" in dependencies,
        "Nginx": (root / "nginx.conf").is_file() or (root / "nginx").is_dir(),
        "Git": git,
        "pytest": python and ((root / "pytest.ini").is_file() or "pytest" in _python_text(root)),
        "ruff": python and "ruff" in _python_text(root),
        "mypy": python and "mypy" in _python_text(root),
        "npm": node and (root / "package-lock.json").is_file(),
        "pnpm": node and (root / "pnpm-lock.yaml").is_file(),
        "yarn": node and (root / "yarn.lock").is_file(),
    }
    technologies.update(name for name, detected in signals.items() if detected)

    package_manager = None
    for marker, manager in (
        ("pnpm-lock.yaml", "pnpm"),
        ("yarn.lock", "yarn"),
        ("package-lock.json", "npm"),
    ):
        if (root / marker).is_file():
            package_manager = manager
            break
    if package_manager is None and python:
        package_manager = "pip"

    framework = "React" if signals["React"] else None
    database = next((name for name in ("PostgreSQL", "Prisma", "Redis") if signals[name]), None)
    test_framework = "pytest" if signals["pytest"] else None
    build_system = (
        package_manager if node else ("setuptools" if (root / "pyproject.toml").is_file() else None)
    )
    primary_language = (
        "Python"
        if python
        else ("TypeScript" if signals["TypeScript"] else ("JavaScript" if node else None))
    )
    return TechnologyProfile(
        technologies=sorted(technologies),
        primary_language=primary_language,
        framework=framework,
        database=database,
        package_manager=package_manager,
        build_system=build_system,
        test_framework=test_framework,
        docker_enabled=docker,
        git_enabled=git,
    )


def _python_text(root: Path) -> str:
    content: list[str] = []
    for filename in ("pyproject.toml", "requirements.txt"):
        try:
            content.append((root / filename).read_text(encoding="utf-8").lower())
        except OSError:
            continue
    return "\n".join(content)


def executable_available(name: str) -> bool:
    """Return whether an executable can be resolved without invoking it."""
    return shutil.which(name) is not None
