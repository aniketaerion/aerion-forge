from pathlib import Path

from forge.domain_intelligence.api.discovery import (
    discover_api_source_files,
)


def test_discover_api_source_files(tmp_path: Path) -> None:
    api = tmp_path / "api"
    api.mkdir()

    (api / "routes.py").write_text(
        "@router.get('/health')",
        encoding="utf-8",
    )

    assert discover_api_source_files(tmp_path) == (
        "api/routes.py",
    )