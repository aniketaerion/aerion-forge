"""Manifest-first, read-only repository discovery."""

import json
import os
import re
import tomllib
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from forge.core.repository_policy import EXCLUDED_REPOSITORY_DIRECTORIES
from forge.discovery.errors import DiscoveryError
from forge.discovery.models import (
    DirectoryEntry,
    DiscoveredApplication,
    DiscoveredDependency,
    DiscoveryResult,
)

IGNORED_DIRECTORIES = EXCLUDED_REPOSITORY_DIRECTORIES
LANGUAGES = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".dart": "Dart",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".c": "C",
    ".h": "C/C++ Header",
    ".hpp": "C/C++ Header",
    ".rs": "Rust",
    ".go": "Go",
    ".java": "Java",
}
CONFIG_NAMES = {
    "pyproject.toml",
    "requirements.txt",
    "package.json",
    "tsconfig.json",
    "pubspec.yaml",
    "cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "settings.gradle",
    "cmakelists.txt",
    "makefile",
    "dockerfile",
    "compose.yaml",
    "compose.yml",
    "docker-compose.yaml",
    "docker-compose.yml",
    "nginx.conf",
    "openapi.yaml",
    "openapi.json",
    "swagger.yaml",
    "swagger.json",
}
MANIFEST_NAMES = {
    "pyproject.toml",
    "requirements.txt",
    "package.json",
    "pubspec.yaml",
    "cargo.toml",
    "go.mod",
    "pom.xml",
}


class RepositoryDiscoveryScanner:
    """Discover repository metadata without parsing application source files."""

    def __init__(self, root: Path, max_manifest_bytes: int = 1_000_000) -> None:
        self.root = root.expanduser()
        self.max_manifest_bytes = max_manifest_bytes

    def scan(self) -> DiscoveryResult:
        """Validate and inspect the repository, returning sorted structured metadata."""
        root = self._validated_root()
        files, directories = self._enumerate(root)
        relative_files = [path.relative_to(root).as_posix() for path in files]
        manifests = [path for path in files if path.name.lower() in MANIFEST_NAMES]
        manifest_text = {path: self._read_manifest(path) for path in manifests}
        package_data = {
            path: self._json_manifest(path) for path in manifests if path.name == "package.json"
        }
        dependencies, scripts = self._dependencies(manifests, manifest_text, package_data)
        signals = self._signals(relative_files, manifest_text, package_data, dependencies)
        applications = self._applications(root, files, signals)
        languages = Counter(
            LANGUAGES[path.suffix.lower()] for path in files if path.suffix.lower() in LANGUAGES
        )
        configuration = sorted(
            relative
            for path, relative in zip(files, relative_files, strict=True)
            if self._is_configuration(path)
        )
        environments = sorted(
            relative
            for path, relative in zip(files, relative_files, strict=True)
            if path.name.startswith(".env")
        )
        documentation = sorted(
            relative
            for path, relative in zip(files, relative_files, strict=True)
            if path.suffix.lower() in {".md", ".rst"} or path.name.lower().startswith("readme")
        )
        license_file = next(
            (
                relative
                for relative in relative_files
                if Path(relative).name.lower().startswith("license")
            ),
            None,
        )
        kubernetes = sorted(
            relative for relative in relative_files if self._is_kubernetes_path(relative)
        )
        ci_cd = self._ci_cd(relative_files)
        directory_structure = self._directory_statistics(root, files, directories)
        repository_size = sum(self._size(path) for path in files)
        kinds = defaultdict(list)
        for application in applications:
            kinds[application.kind].append(application.path)
        return DiscoveryResult(
            repository_name=root.name,
            repository_root=root,
            project_type=self._project_type(signals),
            languages=dict(sorted(languages.items())),
            frameworks=sorted(signals["frameworks"]),
            technologies=sorted(signals["technologies"]),
            applications=applications,
            libraries=sorted(kinds["library"]),
            microservices=sorted(kinds["backend service"]),
            dependencies=dependencies,
            package_managers=sorted(signals["package_managers"]),
            build_systems=sorted(signals["build_systems"]),
            scripts=dict(sorted(scripts.items())),
            test_frameworks=sorted(signals["test_frameworks"]),
            linting=sorted(signals["linting"]),
            formatting=sorted(signals["formatting"]),
            databases=sorted(signals["databases"]),
            docker="Docker" in signals["technologies"],
            docker_compose="Docker Compose" in signals["technologies"],
            kubernetes_manifests=kubernetes,
            ci_cd=ci_cd,
            configuration_files=configuration,
            environment_files=environments,
            documentation=documentation,
            license_file=license_file,
            git=(root / ".git").is_dir(),
            repository_size_bytes=repository_size,
            file_count=len(files),
            directory_count=len(directories),
            directory_structure=directory_structure,
        )

    def _validated_root(self) -> Path:
        try:
            root = self.root.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise DiscoveryError(f"Repository does not exist: {self.root}") from exc
        if not root.is_dir():
            raise DiscoveryError(f"Repository is not a directory: {root}")
        if not os.access(root, os.R_OK):
            raise DiscoveryError(f"Repository is not readable: {root}")
        return root

    @staticmethod
    def _enumerate(root: Path) -> tuple[list[Path], list[Path]]:
        files: list[Path] = []
        directories: list[Path] = []
        try:
            for current, names, filenames in os.walk(root):
                names[:] = sorted(name for name in names if name not in IGNORED_DIRECTORIES)
                current_path = Path(current)
                if current_path != root:
                    directories.append(current_path)
                files.extend(current_path / filename for filename in sorted(filenames))
        except OSError as exc:
            raise DiscoveryError(f"Unable to traverse repository {root}: {exc}") from exc
        return files, directories

    def _read_manifest(self, path: Path) -> str:
        try:
            if path.stat().st_size > self.max_manifest_bytes:
                return ""
            return path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    def _json_manifest(self, path: Path) -> dict[str, Any]:
        try:
            data = json.loads(self._read_manifest(path))
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}

    def _dependencies(
        self,
        manifests: list[Path],
        texts: dict[Path, str],
        packages: dict[Path, dict[str, Any]],
    ) -> tuple[list[DiscoveredDependency], dict[str, str]]:
        dependencies: list[DiscoveredDependency] = []
        scripts: dict[str, str] = {}
        for path in manifests:
            relative = path.relative_to(self.root.resolve()).as_posix()
            name = path.name.lower()
            if name == "package.json":
                package = packages[path]
                for section, scope in (
                    ("dependencies", "runtime"),
                    ("devDependencies", "development"),
                ):
                    values = package.get(section, {})
                    if isinstance(values, dict):
                        dependencies.extend(
                            DiscoveredDependency(
                                name=str(key), version=str(value), scope=scope, source=relative
                            )
                            for key, value in values.items()
                        )
                values = package.get("scripts", {})
                if isinstance(values, dict):
                    scripts.update(
                        {f"{relative}:{key}": str(value) for key, value in values.items()}
                    )
            elif name == "requirements.txt":
                for line in texts[path].splitlines():
                    value = line.strip()
                    if value and not value.startswith(("#", "-")):
                        dependency = re.split(r"[<>=!~[]", value, maxsplit=1)[0]
                        dependencies.append(
                            DiscoveredDependency(name=dependency, version=value, source=relative)
                        )
            elif name == "pyproject.toml":
                try:
                    project = tomllib.loads(texts[path]).get("project", {})
                    for value in project.get("dependencies", []):
                        item = str(value)
                        dependencies.append(
                            DiscoveredDependency(
                                name=re.split(r"[<>=!~[]", item, maxsplit=1)[0],
                                version=item,
                                source=relative,
                            )
                        )
                except (tomllib.TOMLDecodeError, AttributeError):
                    continue
            elif name == "cargo.toml":
                try:
                    cargo = tomllib.loads(texts[path])
                    for section, scope in (
                        ("dependencies", "runtime"),
                        ("dev-dependencies", "development"),
                    ):
                        values = cargo.get(section, {})
                        if isinstance(values, dict):
                            dependencies.extend(
                                DiscoveredDependency(
                                    name=str(key),
                                    version=str(value),
                                    scope=scope,
                                    source=relative,
                                )
                                for key, value in values.items()
                            )
                except tomllib.TOMLDecodeError:
                    continue
            elif name == "go.mod":
                for dependency, version in re.findall(
                    r"^\s*([\w./-]+)\s+(v[^\s]+)", texts[path], re.MULTILINE
                ):
                    dependencies.append(
                        DiscoveredDependency(name=dependency, version=version, source=relative)
                    )
            elif name == "pubspec.yaml":
                dependencies.extend(self._yaml_dependencies(texts[path], relative))
            elif name == "pom.xml":
                dependencies.extend(self._maven_dependencies(texts[path], relative))
        return sorted(
            dependencies, key=lambda item: (item.name.casefold(), item.source, item.scope)
        ), scripts

    @staticmethod
    def _yaml_dependencies(text: str, source: str) -> list[DiscoveredDependency]:
        dependencies: list[DiscoveredDependency] = []
        scope: str | None = None
        for line in text.splitlines():
            if line in {"dependencies:", "dev_dependencies:"}:
                scope = "development" if line.startswith("dev_") else "runtime"
                continue
            if scope and line and not line.startswith(" "):
                scope = None
            match = re.match(r"^\s{2}([\w.-]+):\s*([^#]*)", line)
            if scope and match and match.group(1) != "flutter":
                dependencies.append(
                    DiscoveredDependency(
                        name=match.group(1),
                        version=match.group(2).strip() or None,
                        scope=scope,
                        source=source,
                    )
                )
        return dependencies

    @staticmethod
    def _maven_dependencies(text: str, source: str) -> list[DiscoveredDependency]:
        try:
            root = ET.fromstring(text)
        except ET.ParseError:
            return []
        dependencies: list[DiscoveredDependency] = []
        for element in root.findall(".//{*}dependency"):
            group = element.findtext("{*}groupId", default="")
            artifact = element.findtext("{*}artifactId", default="")
            if artifact:
                dependencies.append(
                    DiscoveredDependency(
                        name=f"{group}:{artifact}" if group else artifact,
                        version=element.findtext("{*}version"),
                        scope=element.findtext("{*}scope", default="runtime"),
                        source=source,
                    )
                )
        return dependencies

    def _signals(
        self,
        files: list[str],
        texts: dict[Path, str],
        packages: dict[Path, dict[str, Any]],
        dependencies: list[DiscoveredDependency],
    ) -> dict[str, set[str]]:
        names = {Path(path).name.lower() for path in files}
        paths = {path.lower() for path in files}
        dependency_names = {item.name.lower() for item in dependencies}
        combined = "\n".join(texts.values()).lower()
        technologies: set[str] = set()
        frameworks: set[str] = set()
        managers: set[str] = set()
        builds: set[str] = set()
        tests: set[str] = set()
        linting: set[str] = set()
        formatting: set[str] = set()
        databases: set[str] = set()
        if {"pyproject.toml", "requirements.txt"} & names:
            technologies.add("Python")
            managers.add("pip")
            builds.add("setuptools")
        if "package.json" in names:
            technologies.update(("Node", "JavaScript"))
            managers.add("npm")
        if "tsconfig.json" in names or "typescript" in dependency_names:
            technologies.add("TypeScript")
        if "react" in dependency_names:
            frameworks.add("React")
        if "next" in dependency_names:
            frameworks.add("NextJS")
        if "express" in dependency_names:
            frameworks.add("Express")
        if "@nestjs/core" in dependency_names:
            frameworks.add("NestJS")
        if "pubspec.yaml" in names:
            technologies.update(("Flutter", "Dart"))
            frameworks.add("Flutter")
            managers.add("pub")
        if "cargo.toml" in names:
            technologies.add("Rust")
            managers.add("Cargo")
            builds.add("Cargo")
        if "go.mod" in names:
            technologies.add("Go")
            managers.add("Go modules")
            builds.add("Go")
        if {"pom.xml", "build.gradle"} & names:
            technologies.add("Java")
            builds.add("Maven" if "pom.xml" in names else "Gradle")
        if "cmakelists.txt" in names:
            builds.add("CMake")
        if "makefile" in names:
            builds.add("Make")
        if any(path.endswith((".cpp", ".cc", ".cxx")) for path in paths):
            technologies.add("C++")
        docker_files = {
            "dockerfile",
            "compose.yaml",
            "compose.yml",
            "docker-compose.yaml",
            "docker-compose.yml",
        }
        if names & docker_files:
            technologies.add("Docker")
        if names & (docker_files - {"dockerfile"}):
            technologies.add("Docker Compose")
        for marker, label in (
            ("package-lock.json", "npm"),
            ("pnpm-lock.yaml", "pnpm"),
            ("yarn.lock", "yarn"),
        ):
            if marker in names:
                managers.add(label)
        markers = {
            "PostgreSQL": ("postgres", "psycopg", "pg"),
            "Redis": ("redis", "ioredis"),
            "Kafka": ("kafka", "kafkajs"),
            "Prisma": ("prisma", "@prisma/client"),
            "SQLite": ("sqlite", "better-sqlite3"),
            "MySQL": ("mysql", "mysql2"),
            "MongoDB": ("mongodb", "mongoose"),
        }
        for label, terms in markers.items():
            if any(term in dependency_names or term in combined for term in terms):
                databases.add(label)
        if {"openapi.yaml", "openapi.json"} & names:
            technologies.update(("OpenAPI", "REST"))
        if {"swagger.yaml", "swagger.json"} & names or "swagger" in dependency_names:
            technologies.update(("Swagger", "REST"))
        if "graphql" in dependency_names:
            technologies.add("GraphQL")
        if frameworks & {"Express", "NestJS"}:
            technologies.add("REST")
        for marker, target in (
            ("pytest", tests),
            ("ruff", linting),
            ("mypy", linting),
            ("jest", tests),
            ("vitest", tests),
            ("eslint", linting),
            ("prettier", formatting),
        ):
            if marker in dependency_names or marker in combined:
                target.add(marker)
        technologies.update(frameworks)
        technologies.update(databases)
        return {
            "technologies": technologies,
            "frameworks": frameworks,
            "package_managers": managers,
            "build_systems": builds,
            "test_frameworks": tests,
            "linting": linting,
            "formatting": formatting,
            "databases": databases,
        }

    def _applications(
        self, root: Path, files: list[Path], signals: dict[str, set[str]]
    ) -> list[DiscoveredApplication]:
        candidates: set[Path] = set()
        for path in files:
            path_relative = path.relative_to(root)
            if path.name.lower() in MANIFEST_NAMES:
                candidates.add(path.parent)
            if (
                path_relative.parts
                and path_relative.parts[0].lower() in {"apps", "services", "packages", "libs"}
                and len(path_relative.parts) > 2
            ):
                candidates.add(root.joinpath(*path_relative.parts[:2]))
        if not candidates and files:
            candidates.add(root)
        applications: list[DiscoveredApplication] = []
        for candidate in sorted(candidates, key=lambda item: item.as_posix().lower()):
            candidate_relative = candidate.relative_to(root).as_posix() or "."
            lower = candidate_relative.lower()
            if lower.startswith(("packages/", "libs/")):
                kind = "library"
            elif any(token in lower for token in ("worker", "job")):
                kind = "worker"
            elif "scheduler" in lower:
                kind = "scheduler"
            elif "infra" in lower:
                kind = "infrastructure"
            elif "cli" in lower:
                kind = "CLI application"
            elif lower.startswith("services/") or any(
                token in lower for token in ("api", "backend", "server")
            ):
                kind = "backend service"
            elif any(token in lower for token in ("frontend", "web", "client", "ui")) or signals[
                "frameworks"
            ] & {"React", "NextJS", "Flutter"}:
                kind = "frontend application"
            else:
                kind = "application"
            applications.append(
                DiscoveredApplication(
                    name=root.name if candidate_relative == "." else candidate.name,
                    path=candidate_relative,
                    kind=kind,
                    technologies=sorted(signals["technologies"]),
                )
            )
        return applications

    @staticmethod
    def _project_type(signals: dict[str, set[str]]) -> str:
        priority = (
            "NextJS",
            "NestJS",
            "Express",
            "React",
            "Flutter",
            "Python",
            "Node",
            "C++",
            "Rust",
            "Go",
            "Java",
        )
        for value in priority:
            if value in signals["technologies"] or value in signals["frameworks"]:
                return value
        return "Generic"

    @staticmethod
    def _is_configuration(path: Path) -> bool:
        name = path.name.lower()
        return name in CONFIG_NAMES or path.suffix.lower() in {
            ".toml",
            ".yaml",
            ".yml",
            ".ini",
            ".cfg",
        }

    @staticmethod
    def _is_kubernetes_path(relative: str) -> bool:
        lower = relative.lower()
        return Path(lower).suffix in {".yaml", ".yml"} and any(
            token in f"/{lower}/" for token in ("/k8s/", "/kubernetes/", "/helm/", "/charts/")
        )

    @staticmethod
    def _ci_cd(files: list[str]) -> list[str]:
        detected: set[str] = set()
        for path in files:
            lower = path.lower()
            if lower.startswith(".github/workflows/"):
                detected.add("GitHub Actions")
            if Path(lower).name == "azure-pipelines.yml":
                detected.add("Azure DevOps")
            if Path(lower).name == ".gitlab-ci.yml":
                detected.add("GitLab CI")
        return sorted(detected)

    @staticmethod
    def _size(path: Path) -> int:
        try:
            return path.stat().st_size
        except OSError:
            return 0

    def _directory_statistics(
        self, root: Path, files: list[Path], directories: list[Path]
    ) -> list[DirectoryEntry]:
        entries: list[DirectoryEntry] = []
        for directory in [root, *directories]:
            direct_files = [path for path in files if path.parent == directory]
            direct_directories = [path for path in directories if path.parent == directory]
            entries.append(
                DirectoryEntry(
                    path=directory.relative_to(root).as_posix() or ".",
                    files=len(direct_files),
                    directories=len(direct_directories),
                    size_bytes=sum(self._size(path) for path in direct_files),
                )
            )
        return sorted(entries, key=lambda item: item.path.casefold())
