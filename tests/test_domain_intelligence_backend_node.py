import json
from pathlib import Path

from forge.domain_intelligence.backend.models import (
    BackendFramework,
    BackendRuntime,
)
from forge.domain_intelligence.backend.node import (
    detect_node_frameworks,
    detect_node_runtime,
)


def test_detect_node_express_project(tmp_path: Path) -> None:
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

    assert detect_node_runtime(tmp_path) == (
        BackendRuntime.NODEJS,
    )
    assert detect_node_frameworks(tmp_path) == (
        BackendFramework.EXPRESS,
        BackendFramework.NODE,
    )