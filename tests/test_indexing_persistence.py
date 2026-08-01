import logging
from pathlib import Path

import pytest

from forge.indexing import (
    IndexConfiguration,
    IndexCorruptionError,
    IndexLimitExceededError,
    IndexReportError,
    IndexResult,
)
from forge.indexing.service import IndexingService
from forge.indexing.store import ProjectIndexStore


def service_at(tmp_path: Path, max_files: int = 1000) -> IndexingService:
    logger = logging.getLogger(f"persistence-test-{tmp_path.name}")
    logger.handlers = [logging.NullHandler()]
    return IndexingService(
        ProjectIndexStore(tmp_path / "memory" / "index.json"),
        tmp_path / "reports",
        logger,
        IndexConfiguration(
            max_hash_bytes=1024 * 1024,
            hash_chunk_bytes=1024,
            max_files=max_files,
        ),
    )


def repository(path: Path, filename: str = "app.py") -> Path:
    path.mkdir(parents=True)
    (path / filename).write_text("value = 1", encoding="utf-8")
    return path


def test_multiple_direct_repositories_remain_isolated(tmp_path: Path) -> None:
    first = repository(tmp_path / "first")
    second = repository(tmp_path / "second")
    service = service_at(tmp_path)

    service.index(first)
    service.index(second)
    store = service.store.load()

    assert len(store.repositories) == 2
    assert {item.generation.repository_name for item in store.repositories.values()} == {
        "first",
        "second",
    }


def test_workspace_identity_is_used_as_persistence_key(tmp_path: Path) -> None:
    root = repository(tmp_path / "workspace")
    service = service_at(tmp_path)

    service.index(root, workspace_id="workspace-id")

    assert "workspace-id" in service.store.load().repositories


@pytest.mark.parametrize(
    "content",
    ["not-json", '{"schema_version":"9.0","repositories":{}}'],
)
def test_corrupt_or_incompatible_persistence_is_reported(tmp_path: Path, content: str) -> None:
    path = tmp_path / "memory" / "index.json"
    path.parent.mkdir()
    path.write_text(content, encoding="utf-8")

    with pytest.raises(IndexCorruptionError):
        ProjectIndexStore(path).load()


def test_failed_index_preserves_previous_valid_store(tmp_path: Path) -> None:
    root = repository(tmp_path / "repo")
    service = service_at(tmp_path, max_files=1)
    service.index(root)
    store_path = tmp_path / "memory" / "index.json"
    previous = store_path.read_bytes()
    (root / "second.py").write_text("value = 2", encoding="utf-8")

    with pytest.raises(IndexLimitExceededError):
        service.index(root)

    assert store_path.read_bytes() == previous
    assert not store_path.with_suffix(".json.tmp").exists()


def test_report_failure_preserves_previous_valid_store(tmp_path: Path) -> None:
    root = repository(tmp_path / "repo")
    service = service_at(tmp_path)
    service.index(root)
    store_path = tmp_path / "memory" / "index.json"
    previous = store_path.read_bytes()
    (root / "app.py").write_text("changed", encoding="utf-8")

    class BrokenRenderer:
        def render(self, result: IndexResult) -> dict[str, str]:
            raise IndexReportError("report failure")

    service.renderer = BrokenRenderer()  # type: ignore[assignment]
    with pytest.raises(IndexReportError):
        service.index(root)

    assert store_path.read_bytes() == previous


def test_index_store_inside_repository_is_not_self_indexed(tmp_path: Path) -> None:
    root = repository(tmp_path / "repo")
    logger = logging.getLogger("self-index-test")
    service = IndexingService(
        ProjectIndexStore(root / "memory" / "index.json"),
        tmp_path / "reports",
        logger,
        IndexConfiguration(max_hash_bytes=1024, hash_chunk_bytes=1024, max_files=100),
    )
    first = service.index(root)
    second = service.index(root)

    assert (
        first.project_index.generation.repository_state_fingerprint
        == second.project_index.generation.repository_state_fingerprint
    )
    assert all(item.path != "memory/index.json" for item in second.project_index.files)
