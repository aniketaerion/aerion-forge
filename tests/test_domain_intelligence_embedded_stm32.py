from pathlib import Path

from forge.domain_intelligence.embedded.stm32 import (
    detect_stm32,
    discover_stm32_components,
)


def test_stm32_detection_and_components(tmp_path: Path) -> None:
    (tmp_path / "flight_controller.ioc").write_text(
        "Mcu.Family=STM32F4",
        encoding="utf-8",
    )

    assert detect_stm32(tmp_path)
    components = discover_stm32_components(tmp_path)

    assert len(components) == 1
    assert components[0].name == "flight_controller"