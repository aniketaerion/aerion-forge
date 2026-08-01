import hashlib
import logging
import os
from pathlib import Path

from forge.indexing import IndexConfiguration
from forge.indexing.models import EngineeringRole
from forge.indexing.service import IndexingService
from forge.indexing.store import ProjectIndexStore


def write(path: Path, content: str = "content") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def service_at(tmp_path: Path) -> IndexingService:
    logger = logging.getLogger(f"incremental-test-{tmp_path.name}")
    logger.handlers = [logging.NullHandler()]
    return IndexingService(
        ProjectIndexStore(tmp_path / "memory" / "index.json"),
        tmp_path / "reports",
        logger,
        IndexConfiguration(max_hash_bytes=1024 * 1024, hash_chunk_bytes=1024, max_files=1000),
    )


def report_hashes(path: Path) -> dict[str, str]:
    return {
        item.name: hashlib.sha256(item.read_bytes()).hexdigest()
        for item in sorted(path.iterdir())
        if item.name.startswith(("INDEX_", "PROJECT_INDEX", "FILE_CATALOG"))
    }


def test_incremental_add_modify_remove_unchanged_and_generation_chain(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    write(repository / "app.py", "first")
    service = service_at(tmp_path)

    first = service.index(repository)
    second = service.index(repository)
    write(repository / "app.py", "second")
    modified = service.index(repository)
    write(repository / "added.py", "new")
    added = service.index(repository)
    (repository / "app.py").unlink()
    removed = service.index(repository)

    assert first.project_index.generation.statistics.added_count == 1
    assert second.project_index.generation.statistics.unchanged_count == 1
    assert (
        second.project_index.generation.repository_state_fingerprint
        == first.project_index.generation.repository_state_fingerprint
    )
    assert modified.project_index.generation.statistics.modified_count == 1
    assert (
        modified.project_index.generation.previous_generation_id
        == first.project_index.generation.generation_id
    )
    assert added.project_index.generation.statistics.added_count == 1
    assert removed.project_index.generation.statistics.removed_count == 1


def test_unambiguous_move_is_renamed(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    write(repository / "old.py", "unique")
    service = service_at(tmp_path)
    service.index(repository)
    (repository / "old.py").rename(repository / "new.py")

    result = service.index(repository)

    assert len(result.changes.renamed) == 1
    assert result.changes.renamed[0].previous_path == "old.py"
    assert result.changes.renamed[0].path == "new.py"
    assert result.changes.added == []
    assert result.changes.removed == []


def test_ambiguous_duplicate_fingerprints_are_not_renamed(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    write(repository / "a.py", "duplicate")
    write(repository / "b.py", "duplicate")
    service = service_at(tmp_path)
    service.index(repository)
    (repository / "a.py").unlink()
    (repository / "b.py").unlink()
    write(repository / "c.py", "duplicate")
    write(repository / "d.py", "duplicate")

    result = service.index(repository)

    assert result.changes.renamed == []
    assert len(result.changes.added) == 2
    assert len(result.changes.removed) == 2


def test_timestamp_only_change_is_unchanged(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    path = repository / "app.py"
    write(path, "same")
    service = service_at(tmp_path)
    service.index(repository)
    stat = path.stat()
    os.utime(path, (stat.st_atime + 100, stat.st_mtime + 100))

    result = service.index(repository)

    assert result.project_index.generation.statistics.unchanged_count == 1
    assert result.project_index.generation.statistics.modified_count == 0


def test_repeated_unchanged_reports_are_byte_identical_and_portable(tmp_path: Path) -> None:
    repository = tmp_path / "absolute" / "repo"
    write(repository / "src" / "app.py", "same")
    service = service_at(tmp_path)
    service.index(repository)
    service.index(repository)
    second_hashes = report_hashes(tmp_path / "reports")
    second_state = service.index(repository).project_index.generation.repository_state_fingerprint
    third_hashes = report_hashes(tmp_path / "reports")
    portable = "\n".join(
        path.read_text(encoding="utf-8") for path in (tmp_path / "reports").iterdir()
    )

    assert second_hashes == third_hashes
    assert (
        second_state
        == service.index(repository).project_index.generation.repository_state_fingerprint
    )
    assert str(repository.resolve()) not in portable


def test_persisted_classification_change_is_reconsidered(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    write(repository / "controllers" / "user.py", "same")
    service = service_at(tmp_path)
    first = service.index(repository)
    identity = first.project_index.generation.repository_identity
    old_file = first.project_index.files[0].model_copy(
        update={"engineering_role": EngineeringRole.UNKNOWN}
    )
    service.store.save(identity, first.project_index.model_copy(update={"files": [old_file]}))

    refreshed = service.index(repository)

    assert refreshed.project_index.generation.statistics.modified_count == 1
