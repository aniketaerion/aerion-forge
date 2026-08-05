from pathlib import Path

from forge.domain_intelligence.database.configuration import (
    discover_database_configuration_files,
)


def test_database_configuration_discovery_excludes_env(
    tmp_path: Path,
) -> None:
    (tmp_path / "postgresql.conf").write_text(
        "max_connections = 100",
        encoding="utf-8",
    )
    (tmp_path / ".env").write_text(
        "DATABASE_URL=secret",
        encoding="utf-8",
    )

    assert discover_database_configuration_files(tmp_path) == (
        "postgresql.conf",
    )