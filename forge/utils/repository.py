"""Repository enumeration, classification, and safe text inspection."""

import json
import re
import tomllib
from collections import Counter
from pathlib import Path

from forge.models.audit import (
    DependencyGraph,
    DependencyNode,
    FileRecord,
    Finding,
    RepositoryInventory,
)

IGNORED_DIRECTORIES = {
    ".git",
    ".idea",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "target",
    "vendor",
}
LANGUAGES = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".cs": "C#",
    ".go": "Go",
    ".rs": "Rust",
    ".php": "PHP",
    ".rb": "Ruby",
    ".sql": "SQL",
    ".sh": "Shell",
    ".ps1": "PowerShell",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".vue": "Vue",
    ".svelte": "Svelte",
}
TEXT_SUFFIXES = set(LANGUAGES) | {
    ".md",
    ".txt",
    ".toml",
    ".yaml",
    ".yml",
    ".json",
    ".xml",
    ".ini",
    ".cfg",
}


class RepositoryScanner:
    """Perform bounded, read-only static inspection of an arbitrary repository."""

    def __init__(self, root: Path, max_file_bytes: int = 1_000_000) -> None:
        self.root = root.resolve()
        self.max_file_bytes = max_file_bytes

    def scan(self) -> tuple[RepositoryInventory, DependencyGraph, list[Finding]]:
        """Return inventory, dependency graph, and actionable findings."""
        if not self.root.is_dir():
            raise NotADirectoryError(
                f"Repository does not exist or is not a directory: {self.root}"
            )
        files = self._enumerate()
        records = [self._record(path) for path in files]
        inventory = self._inventory(records)
        graph, manifest_findings = self._dependencies(files)
        findings = manifest_findings + self._inspect_sources(files)
        findings.extend(self._testing_findings(inventory))
        return inventory, graph, findings

    def _enumerate(self) -> list[Path]:
        return sorted(
            (
                path
                for path in self.root.rglob("*")
                if path.is_file()
                and not any(
                    part in IGNORED_DIRECTORIES for part in path.relative_to(self.root).parts
                )
            ),
            key=lambda path: path.as_posix().lower(),
        )

    def _record(self, path: Path) -> FileRecord:
        relative = path.relative_to(self.root).as_posix()
        language = LANGUAGES.get(path.suffix.lower())
        category = "source" if language else "other"
        if "test" in path.stem.lower() or any(
            part in {"test", "tests", "spec", "specs"} for part in path.parts
        ):
            category = "test"
        elif path.suffix.lower() in {".md", ".rst"} or path.name.lower().startswith("readme"):
            category = "documentation"
        elif self._is_config(path):
            category = "configuration"
        return FileRecord(
            path=relative, category=category, size_bytes=path.stat().st_size, language=language
        )

    def _inventory(self, records: list[FileRecord]) -> RepositoryInventory:
        paths = [record.path for record in records]
        lower = {path: path.lower() for path in paths}
        languages = Counter(record.language for record in records if record.language)
        technologies, package_managers = self._technologies(paths)
        build_commands, test_commands = self._commands()
        return RepositoryInventory(
            root=str(self.root),
            files=records,
            languages=dict(languages),
            technologies=technologies,
            package_managers=package_managers,
            build_commands=build_commands,
            test_commands=test_commands,
            api_files=[p for p in paths if re.search(r"(^|/)(api|apis)(/|$)|api\.", lower[p])],
            route_files=[
                p for p in paths if "route" in Path(p).stem.lower() or "/routes/" in f"/{lower[p]}/"
            ],
            migrations=[
                p
                for p in paths
                if "migration" in lower[p] or re.search(r"(^|/)migrations?/", lower[p])
            ],
            documentation=[r.path for r in records if r.category == "documentation"],
            configuration=[p for p in paths if self._is_config(self.root / p)],
            environment_files=[p for p in paths if Path(p).name.lower().startswith(".env")],
            ci_files=[
                p
                for p in paths
                if "/.github/workflows/" in f"/{lower[p]}"
                or lower[p].startswith((".gitlab-ci", "azure-pipelines", "jenkinsfile"))
            ],
            docker_files=[
                p
                for p in paths
                if "dockerfile" in Path(p).name.lower()
                or "docker-compose" in lower[p]
                or "compose.y" in lower[p]
            ],
            backend_files=[p for p in paths if self._area(p, "backend")],
            frontend_files=[p for p in paths if self._area(p, "frontend")],
            test_files=[r.path for r in records if r.category == "test"],
        )

    @staticmethod
    def _is_config(path: Path) -> bool:
        name = path.name.lower()
        return (
            path.suffix.lower() in {".toml", ".yaml", ".yml", ".ini", ".cfg"}
            or name
            in {
                "package.json",
                "tsconfig.json",
                "pyproject.toml",
                "requirements.txt",
                "pom.xml",
                "build.gradle",
                "cargo.toml",
                "go.mod",
                "makefile",
                "vite.config.js",
                "vite.config.ts",
            }
            or name.startswith(".env")
        )

    @staticmethod
    def _area(path: str, area: str) -> bool:
        value = f"/{path.lower()}/"
        if area == "backend":
            return any(
                token in value
                for token in ("/backend/", "/server/", "/api/", "/controllers/", "/services/")
            )
        return any(
            token in value
            for token in ("/frontend/", "/client/", "/src/components/", "/src/pages/", "/ui/")
        ) or Path(path).suffix.lower() in {".jsx", ".tsx", ".vue", ".svelte"}

    def _technologies(self, paths: list[str]) -> tuple[list[str], list[str]]:
        names = {Path(path).name.lower() for path in paths}
        technologies: set[str] = set()
        managers: set[str] = set()
        mapping = {
            "pyproject.toml": ("Python", "pip"),
            "requirements.txt": ("Python", "pip"),
            "package.json": ("Node.js", "npm"),
            "yarn.lock": ("Node.js", "Yarn"),
            "pnpm-lock.yaml": ("Node.js", "pnpm"),
            "pom.xml": ("Java", "Maven"),
            "build.gradle": ("Java", "Gradle"),
            "cargo.toml": ("Rust", "Cargo"),
            "go.mod": ("Go", "Go modules"),
            "composer.json": ("PHP", "Composer"),
            "gemfile": ("Ruby", "Bundler"),
        }
        for marker, values in mapping.items():
            if marker in names:
                technologies.add(values[0])
                managers.add(values[1])
        if any("dockerfile" in name for name in names):
            technologies.add("Docker")
        if any(Path(path).suffix.lower() == ".sql" for path in paths):
            technologies.add("SQL")
        return sorted(technologies), sorted(managers)

    def _commands(self) -> tuple[list[str], list[str]]:
        build: set[str] = set()
        tests: set[str] = set()
        package = self.root / "package.json"
        if package.is_file():
            try:
                scripts = json.loads(package.read_text(encoding="utf-8")).get("scripts", {})
                for name in scripts:
                    command = f"npm run {name}"
                    (tests if "test" in name else build).add(command)
            except (json.JSONDecodeError, OSError, AttributeError):
                pass
        if (self.root / "pyproject.toml").exists() or (self.root / "pytest.ini").exists():
            tests.add("pytest")
        if (self.root / "Makefile").exists():
            build.add("make")
        if (self.root / "pom.xml").exists():
            build.add("mvn package")
            tests.add("mvn test")
        if (self.root / "build.gradle").exists():
            build.add("gradle build")
            tests.add("gradle test")
        if (self.root / "Cargo.toml").exists():
            build.add("cargo build")
            tests.add("cargo test")
        if (self.root / "go.mod").exists():
            build.add("go build ./...")
            tests.add("go test ./...")
        return sorted(build), sorted(tests)

    def _dependencies(self, files: list[Path]) -> tuple[DependencyGraph, list[Finding]]:
        graph = DependencyGraph(project=self.root.name)
        findings: list[Finding] = []
        for path in files:
            name = path.name.lower()
            try:
                dependencies: list[tuple[str, str | None, str]] = []
                if name == "package.json":
                    data = json.loads(path.read_text(encoding="utf-8"))
                    for section, scope in (
                        ("dependencies", "runtime"),
                        ("devDependencies", "development"),
                    ):
                        dependencies.extend(
                            (key, str(value), scope) for key, value in data.get(section, {}).items()
                        )
                elif name == "pyproject.toml":
                    data = tomllib.loads(path.read_text(encoding="utf-8"))
                    project = data.get("project", {})
                    dependencies.extend(
                        (str(item).split(maxsplit=1)[0].split("[")[0], str(item), "runtime")
                        for item in project.get("dependencies", [])
                    )
                elif name == "requirements.txt":
                    for line in path.read_text(encoding="utf-8").splitlines():
                        item = line.strip()
                        if item and not item.startswith(("#", "-")):
                            dependencies.append(
                                (re.split(r"[<>=!~[]", item, maxsplit=1)[0], item, "runtime")
                            )
                for dependency, version, scope in dependencies:
                    source = path.relative_to(self.root).as_posix()
                    graph.nodes.append(
                        DependencyNode(name=dependency, version=version, scope=scope, source=source)
                    )
                    graph.edges.append((self.root.name, dependency))
            except (
                OSError,
                UnicodeError,
                json.JSONDecodeError,
                tomllib.TOMLDecodeError,
                AttributeError,
            ) as exc:
                findings.append(
                    Finding(
                        category="Invalid manifest",
                        severity="high",
                        message=str(exc),
                        path=path.relative_to(self.root).as_posix(),
                    )
                )
        return graph, findings

    def _inspect_sources(self, files: list[Path]) -> list[Finding]:
        findings: list[Finding] = []
        patterns = [
            (re.compile(r"\bTODO\b", re.I), "TODO", "medium"),
            (re.compile(r"\bFIXME\b", re.I), "FIXME", "high"),
            (
                re.compile(
                    r"\bNotImplemented(Error)?\b|raise\s+NotImplementedError|^\s*pass\s*(#.*)?$"
                ),
                "Incomplete module",
                "high",
            ),
        ]
        route_pattern = re.compile(
            r"@(app|router)\.(get|post|put|patch|delete)|\b(app|router)\.(get|post|put|patch|delete)\s*\(",
            re.I,
        )
        for path in files:
            if (
                path.suffix.lower() not in TEXT_SUFFIXES
                or path.stat().st_size > self.max_file_bytes
            ):
                continue
            try:
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            relative = path.relative_to(self.root).as_posix()
            for number, line in enumerate(lines, 1):
                for pattern, category, severity in patterns:
                    if pattern.search(line):
                        findings.append(
                            Finding(
                                category=category,
                                severity=severity,
                                message=line.strip()[:300],
                                path=relative,
                                line=number,
                            )
                        )
                if route_pattern.search(line):
                    findings.append(
                        Finding(
                            category="API route",
                            severity="info",
                            message=line.strip()[:300],
                            path=relative,
                            line=number,
                        )
                    )
        return findings

    @staticmethod
    def _testing_findings(inventory: RepositoryInventory) -> list[Finding]:
        source_count = sum(1 for record in inventory.files if record.category == "source")
        if source_count and not inventory.test_files:
            return [
                Finding(
                    category="Missing tests",
                    severity="high",
                    message=f"No test files detected for {source_count} source files",
                )
            ]
        if source_count >= 10 and len(inventory.test_files) / source_count < 0.1:
            return [
                Finding(
                    category="Test coverage risk",
                    severity="medium",
                    message=(
                        f"Only {len(inventory.test_files)} test files detected for "
                        f"{source_count} source files"
                    ),
                )
            ]
        return []
