from pathlib import Path

from forge.domain_intelligence.api.contracts import (
    discover_api_contracts,
)
from forge.domain_intelligence.api.models import ApiStyle


def test_discover_api_contracts_combines_styles(
    tmp_path: Path,
) -> None:
    (tmp_path / "openapi.yaml").write_text(
        """
        openapi: 3.0.0
        info:
          title: ERP API
          version: 1.0.0
        paths:
          /orders:
            get:
              responses:
                "200":
                  description: Success
        """,
        encoding="utf-8",
    )
    (tmp_path / "routes.py").write_text(
        """
        @router.post("/orders")
        def create_order():
            return {}
        """,
        encoding="utf-8",
    )
    (tmp_path / "schema.graphql").write_text(
        """
        type Query {
            orders: [String!]!
        }
        """,
        encoding="utf-8",
    )

    contracts = discover_api_contracts(tmp_path)

    assert {
        contract.style for contract in contracts
    } == {
        ApiStyle.GRAPHQL,
        ApiStyle.OPENAPI,
        ApiStyle.REST,
    }