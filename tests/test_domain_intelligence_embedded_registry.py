from pathlib import Path

from forge.domain_intelligence.embedded.models import (
    EmbeddedPlatformKind,
)
from forge.domain_intelligence.embedded.registry import (
    EmbeddedAnalyzerRegistry,
)


def test_default_embedded_registry_detects_px4(
    tmp_path: Path,
) -> None:
    (tmp_path / "src" / "modules").mkdir(parents=True)
    (tmp_path / "CMakeLists.txt").write_text(
        "project(px4)",
        encoding="utf-8",
    )

    registry = EmbeddedAnalyzerRegistry.default()

    assert EmbeddedPlatformKind.PX4 in registry.detect(tmp_path)