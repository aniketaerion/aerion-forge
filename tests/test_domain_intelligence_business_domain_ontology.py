from forge.domain_intelligence.business_domain.models import (
    BusinessEntity,
    BusinessEntityKind,
)
from forge.domain_intelligence.business_domain.ontology import (
    build_business_ontology,
    ontology_relationships,
)


def test_build_business_ontology() -> None:
    entities = (
        BusinessEntity(
            entity_id="entity-1",
            name="Customer",
            kind=BusinessEntityKind.PARTY,
            module="sales",
        ),
        BusinessEntity(
            entity_id="entity-2",
            name="Product",
            kind=BusinessEntityKind.PRODUCT,
            module="inventory",
        ),
    )

    assert build_business_ontology(entities) == {
        "inventory": ("Product",),
        "sales": ("Customer",),
    }


def test_ontology_relationships_detect_shared_concept() -> None:
    entities = (
        BusinessEntity(
            entity_id="entity-1",
            name="Customer",
            kind=BusinessEntityKind.PARTY,
            module="sales",
        ),
        BusinessEntity(
            entity_id="entity-2",
            name="Customer",
            kind=BusinessEntityKind.PARTY,
            module="crm",
        ),
    )

    assert ontology_relationships(entities) == (
        (
            "entity-2",
            "entity-1",
            "shared_business_concept",
        ),
    )