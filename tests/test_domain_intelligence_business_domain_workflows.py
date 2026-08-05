from pathlib import Path

from forge.domain_intelligence.business_domain.workflows import (
    discover_business_workflows,
)


def test_discover_standard_workflows(
    tmp_path: Path,
) -> None:
    workflows = discover_business_workflows(
        tmp_path,
        (
            "procurement",
            "sales",
            "lead",
        ),
    )

    assert {
        workflow.name for workflow in workflows
    } == {
        "Lead To Order",
        "Order To Cash",
        "Procure To Pay",
    }