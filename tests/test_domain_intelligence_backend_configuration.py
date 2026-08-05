from pathlib import Path

from forge.domain_intelligence.backend.configuration import (
    discover_configuration_files,
)


def test_configuration_discovery_excludes_secrets(
    tmp_path: Path,
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname='api'\n",
        encoding="utf-8",
    )
    (tmp_path / ".env").write_text(
        "SECRET=value",
        encoding="utf-8",
    )

    assert discover_configuration_files(tmp_path) == (
        "pyproject.toml",
    )