from forge.domain_intelligence.business_domain.identifiers import (
    business_domain_project_identifier,
    business_entity_identifier,
)


def test_business_domain_project_identifier_is_deterministic() -> None:
    first = business_domain_project_identifier(
        {"root": "apps/erp", "domain": "erp"}
    )
    second = business_domain_project_identifier(
        {"domain": "erp", "root": "apps/erp"}
    )

    assert first == second
    assert first.startswith("business-domain-project-")


def test_business_entity_identifier_changes_by_module() -> None:
    first = business_entity_identifier(
        {"name": "PurchaseOrder", "module": "procurement"}
    )
    second = business_entity_identifier(
        {"name": "PurchaseOrder", "module": "inventory"}
    )

    assert first != second