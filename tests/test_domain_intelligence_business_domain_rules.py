from forge.domain_intelligence.business_domain.models import (
    BusinessEntity,
    BusinessEntityKind,
    BusinessRuleSeverity,
)
from forge.domain_intelligence.business_domain.rules import (
    infer_business_rules,
)


def test_infer_business_rules() -> None:
    rules = infer_business_rules(
        (
            BusinessEntity(
                entity_id="entity-1",
                name="PurchaseOrder",
                kind=BusinessEntityKind.TRANSACTION,
                module="procurement",
            ),
            BusinessEntity(
                entity_id="entity-2",
                name="Lead",
                kind=BusinessEntityKind.PARTY,
                module="crm",
            ),
        )
    )

    assert {
        rule.name for rule in rules
    } == {
        "Lead Conversion Requires Qualification",
        "Purchase Order Requires Approval",
    }
    assert any(
        rule.severity is BusinessRuleSeverity.HIGH
        for rule in rules
    )