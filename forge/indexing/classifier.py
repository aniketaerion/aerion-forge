"""Deterministic file classification using paths, names, and extensions."""

from dataclasses import dataclass
from pathlib import PurePosixPath

from forge.indexing.models import EngineeringRole, FileCategory

SOURCE_EXTENSIONS = {
    ".c",
    ".cc",
    ".cpp",
    ".cs",
    ".cxx",
    ".dart",
    ".go",
    ".h",
    ".hpp",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".php",
    ".py",
    ".rb",
    ".rs",
    ".swift",
    ".ts",
    ".tsx",
    ".vue",
}
SCRIPT_EXTENSIONS = {".bat", ".cmd", ".ps1", ".sh"}
ASSET_EXTENSIONS = {
    ".avif",
    ".bmp",
    ".css",
    ".gif",
    ".ico",
    ".jpeg",
    ".jpg",
    ".mp3",
    ".mp4",
    ".png",
    ".scss",
    ".svg",
    ".ttf",
    ".wav",
    ".webp",
    ".woff",
    ".woff2",
}
MANIFESTS = {
    "cargo.toml",
    "composer.json",
    "go.mod",
    "package.json",
    "pom.xml",
    "pubspec.yaml",
    "pyproject.toml",
    "requirements.txt",
}
LOCKFILES = {
    "cargo.lock",
    "composer.lock",
    "go.sum",
    "package-lock.json",
    "pnpm-lock.yaml",
    "pubspec.lock",
    "yarn.lock",
}
BUILD_FILES = {
    "build.gradle",
    "build.gradle.kts",
    "cmakelists.txt",
    "makefile",
    "settings.gradle",
    "settings.gradle.kts",
}
CONTAINER_FILES = {
    "compose.yaml",
    "compose.yml",
    "docker-compose.yaml",
    "docker-compose.yml",
    "dockerfile",
}
SENSITIVE_SUFFIXES = {".key", ".p12", ".pem", ".pfx"}


@dataclass(frozen=True)
class FileClassification:
    category: FileCategory
    role: EngineeringRole
    repository_area: str | None
    generated: bool
    manifest: bool
    test: bool
    configuration: bool
    documentation: bool
    migration: bool
    infrastructure: bool
    sensitive: bool


def is_sensitive_path(path: str) -> bool:
    """Recognize protected file names without inspecting their content."""
    name = PurePosixPath(path).name.casefold()
    return (
        name == ".env"
        or name.startswith(".env.")
        or PurePosixPath(name).suffix in SENSITIVE_SUFFIXES
        or name.startswith(("credentials", "secrets"))
        or name in {"id_rsa", "id_ed25519"}
    )


def classify_file(path: str) -> FileClassification:
    """Classify a normalized repository-relative path conservatively."""
    pure = PurePosixPath(path)
    name = pure.name.casefold()
    extension = pure.suffix.casefold()
    parts = tuple(part.casefold() for part in pure.parts)
    joined = f"/{'/'.join(parts)}/"
    test = (
        name.startswith("test_")
        or name.endswith((".test.js", ".test.ts", ".spec.js", ".spec.ts"))
        or any(part in {"test", "tests", "spec", "specs"} for part in parts)
    )
    generated = any(part in {"generated", "gen"} for part in parts) or any(
        marker in name for marker in (".generated.", ".g.dart", ".min.js", ".min.css")
    )
    migration = any(part in {"migration", "migrations"} for part in parts)
    documentation = extension in {".md", ".rst"} or name.startswith("readme")
    kubernetes = extension in {".yaml", ".yml"} and any(
        part in {"charts", "helm", "k8s", "kubernetes"} for part in parts
    )
    ci_cd = name in {".gitlab-ci.yml", "azure-pipelines.yml"} or joined.startswith(
        "/.github/workflows/"
    )
    infrastructure = kubernetes or any(
        part in {"deploy", "deployment", "infra", "infrastructure", "terraform"} for part in parts
    )
    configuration = (
        extension in {".cfg", ".ini", ".toml", ".yaml", ".yml"}
        or name.startswith(".env")
        or name in {"nginx.conf", "tsconfig.json"}
    )
    if generated:
        category = FileCategory.GENERATED
    elif test:
        category = FileCategory.TEST
    elif migration:
        category = FileCategory.MIGRATION
    elif name in MANIFESTS:
        category = FileCategory.MANIFEST
    elif name in LOCKFILES:
        category = FileCategory.LOCKFILE
    elif name in BUILD_FILES:
        category = FileCategory.BUILD
    elif name in CONTAINER_FILES:
        category = FileCategory.CONTAINER
    elif kubernetes:
        category = FileCategory.KUBERNETES
    elif ci_cd:
        category = FileCategory.CI_CD
    elif extension in {".graphql", ".prisma", ".proto", ".sql"}:
        category = FileCategory.SCHEMA
    elif documentation:
        category = FileCategory.DOCUMENTATION
    elif infrastructure or extension in {".tf", ".tfvars"}:
        category = FileCategory.INFRASTRUCTURE
    elif extension in SCRIPT_EXTENSIONS:
        category = FileCategory.SCRIPT
    elif extension in ASSET_EXTENSIONS:
        category = FileCategory.ASSET
    elif any(part in {"i18n", "l10n", "locale", "locales"} for part in parts):
        category = FileCategory.LOCALIZATION
    elif extension in SOURCE_EXTENSIONS:
        category = FileCategory.SOURCE
    elif configuration:
        category = FileCategory.CONFIGURATION
    else:
        category = FileCategory.UNKNOWN

    role = _engineering_role(parts, name, extension, category)
    area = _repository_area(parts)
    return FileClassification(
        category=category,
        role=role,
        repository_area=area,
        generated=generated,
        manifest=name in MANIFESTS,
        test=test,
        configuration=configuration,
        documentation=documentation,
        migration=migration,
        infrastructure=infrastructure
        or category in {FileCategory.CONTAINER, FileCategory.KUBERNETES, FileCategory.CI_CD},
        sensitive=is_sensitive_path(path),
    )


def _engineering_role(
    parts: tuple[str, ...], name: str, extension: str, category: FileCategory
) -> EngineeringRole:
    joined = "/".join(parts)
    if category is FileCategory.TEST:
        return EngineeringRole.TEST
    if category is FileCategory.DOCUMENTATION:
        return EngineeringRole.DOCUMENTATION
    if category is FileCategory.BUILD:
        return EngineeringRole.BUILD
    if category in {FileCategory.CI_CD, FileCategory.CONTAINER, FileCategory.KUBERNETES}:
        return EngineeringRole.DEPLOYMENT
    if category is FileCategory.INFRASTRUCTURE:
        return EngineeringRole.INFRASTRUCTURE
    if category in {FileCategory.CONFIGURATION, FileCategory.MANIFEST, FileCategory.LOCKFILE}:
        return EngineeringRole.CONFIGURATION
    rules = (
        (("controllers", "controller"), EngineeringRole.CONTROLLER),
        (("models", "model"), EngineeringRole.MODEL),
        (("repositories", "repository"), EngineeringRole.REPOSITORY),
        (("packages", "libs", "shared"), EngineeringRole.SHARED_LIBRARY),
        (("components", "ui", "views"), EngineeringRole.UI),
        (("state", "store", "stores"), EngineeringRole.STATE_MANAGEMENT),
        (("frontend", "client", "web"), EngineeringRole.FRONTEND),
        (("backend", "server"), EngineeringRole.BACKEND),
        (("database", "db", "migration", "migrations"), EngineeringRole.DATABASE),
        (("api", "routes"), EngineeringRole.API),
        (("domain",), EngineeringRole.DOMAIN),
        (("services", "service"), EngineeringRole.SERVICE),
        (("mobile", "android", "ios"), EngineeringRole.MOBILE),
        (("embedded",), EngineeringRole.EMBEDDED),
        (("ros", "ros2"), EngineeringRole.ROBOTICS),
        (("firmware", "px4"), EngineeringRole.FIRMWARE),
    )
    for tokens, role in rules:
        if any(
            token in parts or token in name or f"/{token}/" in f"/{joined}/" for token in tokens
        ):
            return role
    if extension == ".dart":
        return EngineeringRole.MOBILE
    return EngineeringRole.UNKNOWN


def _repository_area(parts: tuple[str, ...]) -> str | None:
    if len(parts) >= 2 and parts[0] in {"apps", "libs", "packages", "services"}:
        return f"{parts[0]}/{parts[1]}"
    if parts and parts[0] in {
        "backend",
        "client",
        "embedded",
        "firmware",
        "frontend",
        "infra",
        "mobile",
        "ros2",
        "src",
    }:
        return parts[0]
    return None
