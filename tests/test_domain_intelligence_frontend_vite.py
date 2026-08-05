from pathlib import Path

from forge.domain_intelligence.frontend.vite import detect_vite
from forge.domain_intelligence.models import FrontendFramework


def test_detect_vite_from_configuration(tmp_path: Path) -> None:
    (tmp_path / "vite.config.ts").write_text(
        "export default {}",
        encoding="utf-8",
    )

    assert detect_vite(tmp_path) == (
        FrontendFramework.VITE,
    )