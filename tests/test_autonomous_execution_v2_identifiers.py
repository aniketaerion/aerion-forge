from forge.autonomous_execution_v2.identifiers import (
    execution_run_identifier,
    execution_step_identifier,
)


def test_identifiers_are_deterministic() -> None:
    payload = {"plan_id": "plan-1", "paths": {"b.py", "a.py"}}

    assert execution_run_identifier(
        payload
    ) == execution_run_identifier(payload)


def test_identifier_prefixes_are_distinct() -> None:
    payload = {"step": "step-1"}

    assert execution_run_identifier(
        payload
    ).startswith("execution-run-v2-")

    assert execution_step_identifier(
        payload
    ).startswith("execution-step-v2-")