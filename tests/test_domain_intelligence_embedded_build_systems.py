from pathlib import Path

from forge.domain_intelligence.embedded.build_systems import (
    discover_embedded_build_files,
)


def test_embedded_build_file_discovery(
    tmp_path: Path,
) -> None:
    (tmp_path / "CMakeLists.txt").write_text(
        "project(firmware)",
        encoding="utf-8",
    )
    (tmp_path / "platformio.ini").write_text(
        "[env]",
        encoding="utf-8",
    )

    assert discover_embedded_build_files(tmp_path) == (
        "CMakeLists.txt",
        "platformio.ini",
    )