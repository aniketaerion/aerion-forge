from forge.general_engineering.identifiers import (
    deterministic_engineering_identifier,
)


def test_identifier_is_deterministic_and_order_independent() -> None:
    first = deterministic_engineering_identifier(
        "engineering-test",
        {
            "objective": "add validation",
            "paths": ["src/service.py", "tests/test_service.py"],
            "meta": {"b": 2, "a": 1},
        },
    )
    second = deterministic_engineering_identifier(
        "engineering-test",
        {
            "meta": {"a": 1, "b": 2},
            "paths": ["src/service.py", "tests/test_service.py"],
            "objective": "add validation",
        },
    )

    assert first == second
    assert first.startswith("engineering-test-")