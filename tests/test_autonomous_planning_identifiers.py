from forge.autonomous_planning.identifiers import (
    planning_plan_identifier,
    planning_step_identifier,
)


def test_identifiers_are_deterministic() -> None:
    payload = {"objective": "Implement feature", "paths": {"b.py", "a.py"}}
    assert planning_plan_identifier(payload) == planning_plan_identifier(payload)


def test_identifier_prefixes_are_distinct() -> None:
    payload = {"name": "step"}
    assert planning_plan_identifier(payload).startswith("planning-plan-")
    assert planning_step_identifier(payload).startswith("planning-step-")