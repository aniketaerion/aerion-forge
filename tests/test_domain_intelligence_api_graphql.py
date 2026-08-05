from pathlib import Path

from forge.domain_intelligence.api.graphql import (
    discover_graphql_files,
    parse_graphql_contract,
)
from forge.domain_intelligence.api.models import ApiStyle


def test_graphql_discovery_and_contract(
    tmp_path: Path,
) -> None:
    (tmp_path / "schema.graphql").write_text(
        """
        type Query {
            orders: [Order!]!
        }

        type Mutation {
            createOrder: Order!
        }
        """,
        encoding="utf-8",
    )

    assert discover_graphql_files(tmp_path) == (
        "schema.graphql",
    )

    contract = parse_graphql_contract(tmp_path)

    assert contract is not None
    assert contract.style is ApiStyle.GRAPHQL
    assert {
        endpoint.operation_id
        for endpoint in contract.endpoints
    } == {"query", "mutation"}