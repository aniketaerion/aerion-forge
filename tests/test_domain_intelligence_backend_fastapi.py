from pathlib import Path

from forge.domain_intelligence.backend.fastapi import detect_fastapi
from forge.domain_intelligence.backend.models import BackendFramework


def test_detect_fastapi_from_requirements(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text(
        "fastapi==0.116.0\nuvicorn==0.35.0\n",
        encoding="utf-8",
    )

    assert detect_fastapi(tmp_path) == (
        BackendFramework.FASTAPI,
    )