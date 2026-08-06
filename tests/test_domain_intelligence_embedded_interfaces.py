from pathlib import Path

from forge.domain_intelligence.embedded.interfaces import (
    discover_embedded_interfaces,
)
from forge.domain_intelligence.embedded.models import (
    EmbeddedInterfaceKind,
)


def test_embedded_interface_discovery(tmp_path: Path) -> None:
    (tmp_path / "driver.cpp").write_text(
        "UART_Init();\nMAVLINK_MSG_ID_HEARTBEAT;\n",
        encoding="utf-8",
    )

    interfaces = discover_embedded_interfaces(tmp_path)
    kinds = {interface.kind for interface in interfaces}

    assert EmbeddedInterfaceKind.UART in kinds
    assert EmbeddedInterfaceKind.MAVLINK in kinds