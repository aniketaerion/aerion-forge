from forge.general_engineering.requirement_extractor import (
    extract_change_requirements,
)


def test_requirement_extractor_splits_generic_conjunctions() -> None:
    requirements = extract_change_requirements(
        objective="Add validation and add tests.",
    )

    assert len(requirements) == 2
    assert requirements[0].description == "Add validation"
    assert requirements[1].description == "add tests"


def test_requirement_identifiers_are_deterministic() -> None:
    first = extract_change_requirements(
        objective="Create an endpoint and add tests.",
    )
    second = extract_change_requirements(
        objective="Create an endpoint and add tests.",
    )

    assert tuple(item.requirement_id for item in first) == tuple(
        item.requirement_id for item in second
    )