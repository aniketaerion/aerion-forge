from pathlib import Path

from forge.general_engineering.repository_grounding import RepositoryGroundingService
from forge.general_engineering.request_builder import build_engineering_request


def test_grounding_selects_relevant_file_without_task_specific_logic(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "shipment_service.py").write_text(
        "def schedule_shipment():\n    return 'scheduled'\n",
        encoding="utf-8",
    )
    (tmp_path / "src" / "logger.py").write_text(
        "def log_event():\n    pass\n",
        encoding="utf-8",
    )
    (tmp_path / "tests" / "test_shipment.py").write_text(
        "def test_schedule_shipment():\n    pass\n",
        encoding="utf-8",
    )

    request = build_engineering_request(
        objective="Change shipment scheduling behavior and update shipment tests",
        repository_root=tmp_path,
    )
    result = RepositoryGroundingService().ground(request)
    paths = {item.path for item in result.context.relevant_files}
    assert "src/shipment_service.py" in paths
    assert "tests/test_shipment.py" in paths
    assert "src/logger.py" not in paths