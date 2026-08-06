from pathlib import Path

from forge.domain_intelligence.embedded.messages import (
    discover_embedded_messages,
)


def test_embedded_message_discovery(tmp_path: Path) -> None:
    msg = tmp_path / "msg"
    msg.mkdir()
    (msg / "VehicleState.msg").write_text(
        "float32 latitude\nfloat32 longitude\n",
        encoding="utf-8",
    )

    messages = discover_embedded_messages(tmp_path)

    assert len(messages) == 1
    assert messages[0].name == "VehicleState"
    assert messages[0].fields == ("latitude", "longitude")