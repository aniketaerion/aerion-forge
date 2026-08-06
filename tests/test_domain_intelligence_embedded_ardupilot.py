from pathlib import Path

from forge.domain_intelligence.embedded.ardupilot import (
    detect_ardupilot,
    discover_ardupilot_components,
)


def test_ardupilot_detection_and_components(
    tmp_path: Path,
) -> None:
    (tmp_path / "ArduCopter").mkdir()
    (tmp_path / "libraries").mkdir()

    assert detect_ardupilot(tmp_path)
    components = discover_ardupilot_components(tmp_path)

    assert len(components) == 1
    assert components[0].name == "ArduCopter"