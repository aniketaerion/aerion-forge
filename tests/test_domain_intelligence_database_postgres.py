from pathlib import Path

from forge.domain_intelligence.database.models import DatabaseEngine
from forge.domain_intelligence.database.postgres import (
    detect_postgresql,
)


def test_detect_postgresql_from_compose(tmp_path: Path) -> None:
    (tmp_path / "docker-compose.yml").write_text(
        """
        services:
          db:
            image: postgres:16
        """,
        encoding="utf-8",
    )

    assert detect_postgresql(tmp_path) == (
        DatabaseEngine.POSTGRESQL,
    )


def test_detect_postgresql_returns_empty_when_absent(
    tmp_path: Path,
) -> None:
    assert detect_postgresql(tmp_path) == ()