import json
from pathlib import Path

from forge.domain_intelligence.frontend.state_management import (
    detect_state_management,
)


def test_detect_state_management(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "dependencies": {
                    "@reduxjs/toolkit": "^2.0.0",
                    "zustand": "^5.0.0",
                }
            }
        ),
        encoding="utf-8",
    )

    assert detect_state_management(tmp_path) == (
        "redux-toolkit",
        "zustand",
    )