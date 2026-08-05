"""Business workflow discovery for M4.5."""

from __future__ import annotations

from pathlib import Path

from forge.domain_intelligence.business_domain.identifiers import (
    business_workflow_identifier,
)
from forge.domain_intelligence.business_domain.models import (
    BusinessWorkflow,
    BusinessWorkflowStep,
)

_STANDARD_WORKFLOWS: dict[
    str,
    tuple[tuple[str, tuple[str, ...]], ...],
] = {
    "procure_to_pay": (
        ("Create Requisition", ("PurchaseRequisition",)),
        ("Approve Requisition", ("PurchaseRequisition",)),
        ("Issue Purchase Order", ("PurchaseOrder",)),
        ("Receive Goods", ("GoodsReceipt",)),
        ("Process Supplier Invoice", ("SupplierInvoice",)),
        ("Pay Supplier", ("Payment",)),
    ),
    "order_to_cash": (
        ("Create Sales Order", ("SalesOrder",)),
        ("Confirm Order", ("SalesOrder",)),
        ("Dispatch Goods", ("Delivery",)),
        ("Raise Customer Invoice", ("CustomerInvoice",)),
        ("Receive Payment", ("Payment",)),
    ),
    "lead_to_order": (
        ("Capture Lead", ("Lead",)),
        ("Qualify Lead", ("Lead",)),
        ("Create Opportunity", ("Opportunity",)),
        ("Prepare Quote", ("Quote",)),
        ("Create Sales Order", ("SalesOrder",)),
    ),
}


def discover_business_workflows(
    project_root: Path,
    modules: tuple[str, ...],
) -> tuple[BusinessWorkflow, ...]:
    """Map detected modules to standard business workflows."""
    del project_root

    workflows: list[BusinessWorkflow] = []
    module_set = set(modules)

    candidates: list[tuple[str, str]] = []

    if module_set & {"procurement", "purchase"}:
        candidates.append(("procure_to_pay", "procurement"))

    if module_set & {"sales", "inventory", "logistics"}:
        candidates.append(("order_to_cash", "sales"))

    if module_set & {
        "lead",
        "opportunity",
        "quote",
        "account",
        "contact",
    }:
        candidates.append(("lead_to_order", "crm"))

    for workflow_name, module in candidates:
        steps = tuple(
            BusinessWorkflowStep(
                name=step_name,
                sequence=index,
                entity_names=entity_names,
            )
            for index, (step_name, entity_names) in enumerate(
                _STANDARD_WORKFLOWS[workflow_name],
                start=1,
            )
        )

        workflows.append(
            BusinessWorkflow(
                workflow_id=business_workflow_identifier(
                    {
                        "name": workflow_name,
                        "module": module,
                        "steps": [
                            step.name for step in steps
                        ],
                    }
                ),
                name=workflow_name.replace("_", " ").title(),
                module=module,
                steps=steps,
            )
        )

    return tuple(
        sorted(
            workflows,
            key=lambda workflow: workflow.workflow_id,
        )
    )