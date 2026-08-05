from pathlib import Path

from forge.domain_intelligence.backend.workers import (
    discover_worker_files,
)


def test_worker_file_discovery(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()

    (source / "invoice_worker.ts").write_text(
        "export const run = () => undefined",
        encoding="utf-8",
    )

    assert discover_worker_files(tmp_path) == (
        "src/invoice_worker.ts",
    )