import json
from pathlib import Path

from forge.domain_intelligence.frontend.styling import (
    detect_styling_technologies,
)


def test_detect_styling_packages_and_files(
    tmp_path: Path,
) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "devDependencies": {
                    "tailwindcss": "^4.0.0",
                }
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "app.module.css").write_text(
        ".root {}",
        encoding="utf-8",
    )

    assert detect_styling_technologies(tmp_path) == (
        "css",
        "css-modules",
        "tailwindcss",
    )