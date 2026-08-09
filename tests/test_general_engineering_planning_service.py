from pathlib import Path

from forge.general_engineering.planning_service import EngineeringChangePlanningService
from forge.general_engineering.repository_grounding import RepositoryGroundingService
from forge.general_engineering.request_builder import build_engineering_request
from forge.general_engineering.request_understanding import EngineeringRequestUnderstandingService


def test_planning_service_runs_request_to_grounded_plan(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "shipment.py").write_text(
        "def schedule_shipment():\n    return True\n",
        encoding="utf-8",
    )
    request = build_engineering_request(
        objective="Update shipment scheduling",
        repository_root=tmp_path,
    )
    specification = EngineeringRequestUnderstandingService().understand(request).specification
    context = RepositoryGroundingService().ground(request).context

    result = EngineeringChangePlanningService().plan(
        request=request,
        specification=specification,
        context=context,
    )

    assert result.planned_file_count == 1
    assert result.plan.file_changes[0].path == "src/shipment.py"
    assert result.plan.validation_plan.capabilities