from pathlib import Path

from forge.domain_intelligence.business_domain.entities import (
    classify_business_entity,
    discover_business_entities,
)
from forge.domain_intelligence.business_domain.models import (
    BusinessEntityKind,
)


def test_classify_business_entity() -> None:
    assert (
        classify_business_entity("PurchaseOrder")
        is BusinessEntityKind.TRANSACTION
    )
    assert (
        classify_business_entity("Customer")
        is BusinessEntityKind.PARTY
    )


def test_discover_business_entities(
    tmp_path: Path,
) -> None:
    module = tmp_path / "procurement"
    module.mkdir()

    (module / "models.py").write_text(
        """
        class PurchaseOrder:
            pass
        """,
        encoding="utf-8",
    )

    entities = discover_business_entities(tmp_path)

    assert len(entities) == 1
    assert entities[0].name == "PurchaseOrder"
    assert entities[0].module == "procurement"