from pathlib import Path

from forge.general_engineering.request_builder import (
    build_engineering_request,
)
from forge.general_engineering.request_understanding import (
    EngineeringRequestUnderstandingService,
)


def test_understanding_builds_change_specification(
    tmp_path: Path,
) -> None:
    request = build_engineering_request(
        objective="Add validation and add tests.",
        repository_root=tmp_path,
        constraints=(
            "Preserve existing behavior.",
            "Do not modify configuration.",
        ),
        acceptance_criteria=("Existing tests continue to pass.",),
    )

    result = EngineeringRequestUnderstandingService().understand(request)

    assert result.request == request
    assert len(result.specification.requirements) == 2
    assert result.specification.constraints == request.constraints
    assert result.specification.invariants == (
        "Preserve existing behavior.",
        "Do not modify configuration.",
    )


def test_understanding_is_domain_agnostic(
    tmp_path: Path,
) -> None:
    objectives = (
        "Add a parser and add tests.",
        "Create a route and document the behavior.",
        "Update a calculation and preserve existing behavior.",
    )

    service = EngineeringRequestUnderstandingService()

    for objective in objectives:
        request = build_engineering_request(
            objective=objective,
            repository_root=tmp_path,
        )
        result = service.understand(request)
        assert result.specification.requirements