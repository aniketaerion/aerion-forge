import json
from pathlib import Path

from forge.domain_intelligence.backend.dependencies import (
    node_dependencies,
    python_dependencies,
)


def test_dependency_analysis_reads_node_and_python(
    tmp_path: Path,
) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "dependencies": {
                    "express": "^5.0.0",
                }
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "requirements.txt").write_text(
        "fastapi==0.116.0\nredis>=6\n",
        encoding="utf-8",
    )

    assert node_dependencies(tmp_path) == {
        "express": "^5.0.0"
    }
    assert set(python_dependencies(tmp_path)) == {
        "fastapi",
        "redis",
    }