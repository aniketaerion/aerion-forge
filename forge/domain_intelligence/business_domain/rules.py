"""Business rule inference for M4.5."""

from __future__ import annotations

from forge.domain_intelligence.business_domain.identifiers import (
    business_rule_identifier,
)
from forge.domain_intelligence.business_domain.models import (
    BusinessEntity,
    BusinessRule,
    BusinessRuleSeverity,
)


def infer_business_rules(
    entities: tuple[BusinessEntity, ...],
) -> tuple[BusinessRule, ...]:
    """Infer conservative rules from known business entities."""
    rules: list[BusinessRule] = []
    names = {entity.name.lower() for entity in entities}

    def add_rule(
        *,
        name: str,
        description: str,
        severity: BusinessRuleSeverity,
        entity_names: tuple[str, ...],
        module: str | None = None,
    ) -> None:
        rules.append(
            BusinessRule(
                rule_id=business_rule_identifier(
                    {
                        "name": name,
                        "entities": entity_names,
                        "module": module,
                    }
                ),
                name=name,
                description=description,
                severity=severity,
                module=module,
                entity_names=entity_names,
            )
        )

    if "purchaseorder" in names:
        add_rule(
            name="Purchase Order Requires Approval",
            description=(
                "Purchase orders should pass an approval control "
                "before supplier commitment."
            ),
            severity=BusinessRuleSeverity.HIGH,
            entity_names=("PurchaseOrder",),
            module="procurement",
        )

    if "salesorder" in names:
        add_rule(
            name="Sales Order Requires Customer",
            description=(
                "Sales orders should reference a valid customer "
                "or account."
            ),
            severity=BusinessRuleSeverity.HIGH,
            entity_names=("SalesOrder", "Customer"),
            module="sales",
        )

    if "invoice" in names or {
        "customerinvoice",
        "supplierinvoice",
    } & names:
        add_rule(
            name="Invoice Totals Must Balance",
            description=(
                "Invoice line totals, tax, discounts, and payable "
                "amount should reconcile."
            ),
            severity=BusinessRuleSeverity.CRITICAL,
            entity_names=(
                "CustomerInvoice",
                "SupplierInvoice",
            ),
            module="finance",
        )

    if "lead" in names:
        add_rule(
            name="Lead Conversion Requires Qualification",
            description=(
                "A lead should be qualified before conversion to "
                "an opportunity."
            ),
            severity=BusinessRuleSeverity.MEDIUM,
            entity_names=("Lead", "Opportunity"),
            module="crm",
        )

    return tuple(
        sorted(
            rules,
            key=lambda rule: rule.rule_id,
        )
    )