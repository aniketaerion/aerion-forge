from pathlib import Path

from forge.domain_intelligence.frontend.nextjs import detect_nextjs
from forge.domain_intelligence.models import FrontendFramework


def test_detect_nextjs_from_app_directory(tmp_path: Path) -> None:
    (tmp_path / "app").mkdir()

    assert detect_nextjs(tmp_path) == (
        FrontendFramework.NEXTJS,
    )