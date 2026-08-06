from pathlib import Path

from forge.domain_intelligence.embedded.ros2 import (
    detect_ros2,
    discover_ros2_components,
)


def test_ros2_detection_and_components(tmp_path: Path) -> None:
    package = tmp_path / "src" / "camera_node"
    package.mkdir(parents=True)
    (package / "package.xml").write_text(
        "<package><name>camera_node</name></package>",
        encoding="utf-8",
    )

    assert detect_ros2(tmp_path)
    components = discover_ros2_components(tmp_path)

    assert len(components) == 1
    assert components[0].name == "camera_node"