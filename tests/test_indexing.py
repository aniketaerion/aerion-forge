import logging
from pathlib import Path

import pytest

from forge.indexing import (
    FileCategory,
    FileFingerprint,
    FingerprintStrategy,
    IndexConfiguration,
)
from forge.indexing.scanner import ProjectIndexScanner
from forge.indexing.service import IndexingService
from forge.indexing.store import ProjectIndexStore


def write(path: Path, content: str = "content") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def service_at(tmp_path: Path, max_hash_bytes: int = 10 * 1024 * 1024) -> IndexingService:
    logger = logging.getLogger(f"index-test-{tmp_path.name}")
    logger.handlers = [logging.NullHandler()]
    return IndexingService(
        ProjectIndexStore(tmp_path / "memory" / "index.json"),
        tmp_path / "reports",
        logger,
        IndexConfiguration(
            max_hash_bytes=max_hash_bytes,
            hash_chunk_bytes=1024,
            max_files=10_000,
        ),
    )


@pytest.mark.parametrize(
    ("relative", "content", "category"),
    [
        ("src/main.py", "value = 1", FileCategory.SOURCE),
        ("apps/web/App.tsx", "export default 1", FileCategory.SOURCE),
        ("services/api/server.js", "module.exports = {}", FileCategory.SOURCE),
        ("erp/domain/model.py", "value = 1", FileCategory.SOURCE),
        ("native/main.cpp", "int main() {}", FileCategory.SOURCE),
        ("crates/core/lib.rs", "pub fn run() {}", FileCategory.SOURCE),
        ("cmd/server/main.go", "package main", FileCategory.SOURCE),
        ("src/main/java/App.java", "class App {}", FileCategory.SOURCE),
        ("lib/main.dart", "void main() {}", FileCategory.SOURCE),
        ("firmware/px4/main.c", "int main() {}", FileCategory.SOURCE),
        ("ros2/nodes/control.cpp", "int main() {}", FileCategory.SOURCE),
    ],
)
def test_initial_index_supports_target_repository_shapes(
    tmp_path: Path, relative: str, content: str, category: FileCategory
) -> None:
    repository = tmp_path / "repository"
    write(repository / relative, content)

    result = service_at(tmp_path).index(repository)

    assert result.project_index.generation.statistics.added_count == 1
    assert result.project_index.files[0].category is category


def test_empty_repository_creates_valid_generation(tmp_path: Path) -> None:
    repository = tmp_path / "empty"
    repository.mkdir()

    result = service_at(tmp_path).index(repository)

    assert result.project_index.files == []
    assert result.project_index.generation.statistics.total_indexed_files == 0
    assert len(result.project_index.generation.repository_state_fingerprint) == 64


def test_monorepo_area_and_role_classification(tmp_path: Path) -> None:
    repository = tmp_path / "monorepo"
    write(repository / "apps/web/components/Button.tsx")
    write(repository / "services/api/controllers/user.py")
    write(repository / "packages/shared/index.ts")
    files = service_at(tmp_path).index(repository).project_index.files
    indexed = {item.path: item for item in files}

    assert indexed["apps/web/components/Button.tsx"].repository_area == "apps/web"
    assert indexed["services/api/controllers/user.py"].engineering_role.value == "controller"
    assert indexed["packages/shared/index.ts"].engineering_role.value == "shared_library"


def test_sensitive_large_binary_and_excluded_files_are_safe(tmp_path: Path) -> None:
    repository = tmp_path / "safe"
    secret = "do-not-expose-secret-value"
    write(repository / ".env", secret)
    write(repository / "secrets.production", secret * 100)
    large = repository / "assets" / "large.bin"
    large.parent.mkdir(parents=True)
    large.write_bytes(b"\x00" + b"x" * 4096)
    write(repository / "node_modules" / "package" / "index.js")
    write(repository / "build" / "generated.py")
    write(repository / ".pytest_cache" / "cache")
    write(repository / "reports" / "PROJECT_INDEX.json")

    result = service_at(tmp_path, max_hash_bytes=1024).index(repository)
    indexed = {item.path: item for item in result.project_index.files}
    report_text = "\n".join(
        path.read_text(encoding="utf-8") for path in (tmp_path / "reports").iterdir()
    )

    assert indexed[".env"].sensitive
    assert indexed[".env"].fingerprint.strategy is FingerprintStrategy.PROTECTED
    assert (
        indexed["secrets.production"].fingerprint.strategy is FingerprintStrategy.PROTECTED_SAMPLED
    )
    assert indexed["assets/large.bin"].fingerprint.strategy is FingerprintStrategy.SAMPLED
    assert indexed["assets/large.bin"].binary
    assert not any("node_modules" in path for path in indexed)
    assert not any(path.startswith("build/") for path in indexed)
    assert not any(path.startswith("reports/") for path in indexed)
    assert secret not in report_text


def test_external_file_symlink_is_not_followed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    external = tmp_path / "external.txt"
    external.write_text("outside-secret", encoding="utf-8")
    link = repository / "link.txt"
    try:
        link.symlink_to(external)
    except OSError:
        link.write_text("link placeholder", encoding="utf-8")
        original = Path.is_symlink
        monkeypatch.setattr(Path, "is_symlink", lambda path: path == link or original(path))

    files = ProjectIndexScanner(repository, 1024, 1024, 100).scan()[1]

    assert len(files) == 1
    assert files[0].index_status.value == "skipped"
    assert files[0].fingerprint.value is None


def test_unreadable_file_is_recorded_as_failed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repo"
    write(repository / "app.py")

    def fail(*args: object, **kwargs: object) -> FileFingerprint:
        raise OSError("denied")

    monkeypatch.setattr("forge.indexing.fingerprint.FileFingerprinter.fingerprint", fail)
    files = ProjectIndexScanner(repository, 1024, 1024, 100).scan()[1]

    assert files[0].index_status.value == "failed"
    assert files[0].error == "file could not be read"
