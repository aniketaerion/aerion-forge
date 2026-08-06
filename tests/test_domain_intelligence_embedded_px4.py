from pathlib import Path

from forge.domain_intelligence.embedded.px4 import (
    detect_px4,
    discover_px4_components,
)


def test_px4_detection_and_components(tmp_path: Path) -> None:
    modules = tmp_path / "src" / "modules" / "navigator"
    modules.mkdir(parents=True)
    (tmp_path / "CMakeLists.txt").write_text(
        "project(px4)",
        encoding="utf-8",
    )

    assert detect_px4(tmp_path)
    components = discover_px4_components(tmp_path)

    assert len(components) == 1
    assert components[0].name == "navigator"