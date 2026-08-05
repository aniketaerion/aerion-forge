import json
from pathlib import Path

from forge.domain_intelligence.frontend.react import (
    detect_react,
    load_package_json,
    package_dependencies,
)
from forge.domain_intelligence.models import FrontendFramework


def write_package_json(
    root: Path,
    payload: dict[str, object],
) -> None:
    (root / "package.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


def test_detect_react_from_dependency(tmp_path: Path) -> None:
    write_package_json(
        tmp_path,
        {"dependencies": {"react": "^19.0.0"}},
    )

    assert detect_react(tmp_path) == (
        FrontendFramework.REACT,
    )


def test_package_dependencies_merges_sections(
    tmp_path: Path,
) -> None:
    write_package_json(
        tmp_path,
        {
            "dependencies": {"react": "^19.0.0"},
            "devDependencies": {"vite": "^7.0.0"},
        },
    )

    dependencies = package_dependencies(
        load_package_json(tmp_path)
    )

    assert dependencies == {
        "react": "^19.0.0",
        "vite": "^7.0.0",
    }