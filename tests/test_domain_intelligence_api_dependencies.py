import json
from pathlib import Path

from forge.domain_intelligence.api.dependencies import (
    discover_api_dependencies,
)


def test_discover_api_dependencies(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "dependencies": {
                    "express": "^5.0.0",
                    "graphql": "^16.0.0",
                    "react": "^19.0.0",
                }
            }
        ),
        encoding="utf-8",
    )

    assert discover_api_dependencies(tmp_path) == (
        "express",
        "graphql",
    )