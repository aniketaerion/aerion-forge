from pathlib import Path

from forge.domain_intelligence.backend.django import detect_django
from forge.domain_intelligence.backend.models import BackendFramework


def test_detect_django_from_manage_py(tmp_path: Path) -> None:
    (tmp_path / "manage.py").write_text(
        "from django.core.management import execute_from_command_line",
        encoding="utf-8",
    )

    assert detect_django(tmp_path) == (
        BackendFramework.DJANGO,
    )