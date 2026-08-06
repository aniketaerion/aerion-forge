from forge.autonomous_planning.analysis import (
    analyse_planning_request,
)
from forge.autonomous_planning.context import PlanningContext
from forge.autonomous_planning.models import PlanningRequest
from forge.autonomous_planning.states import (
    PlanningIntent,
    PlanningRisk,
)


def test_analysis_merges_repository_context() -> None:
    result = analyse_planning_request(
        request=PlanningRequest(
            request_id="request-1",
            objective="Implement feature",
            repository_root="repository",
            intent=PlanningIntent.IMPLEMENT_FEATURE,
            target_paths=("forge/a.py",),
            requested_capabilities=("editing",),
            created_by="Aerion",
        ),
        context=PlanningContext(
            repository_root="repository",
            repository_fingerprint="fingerprint-1",
            relevant_files=("forge/b.py",),
            known_capabilities=("testing",),
        ),
    )

    assert result.target_paths == (
        "forge/a.py",
        "forge/b.py",
    )
    assert result.required_capabilities == (
        "editing",
        "testing",
    )
    assert result.estimated_risk is PlanningRisk.LOW