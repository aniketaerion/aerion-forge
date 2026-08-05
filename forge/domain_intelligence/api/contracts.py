"""API contract aggregation for M4.4 API Domain Intelligence."""

from __future__ import annotations

from pathlib import Path

from forge.domain_intelligence.api.graphql import (
    parse_graphql_contract,
)
from forge.domain_intelligence.api.identifiers import (
    api_contract_identifier,
)
from forge.domain_intelligence.api.models import (
    ApiContract,
    ApiStyle,
)
from forge.domain_intelligence.api.openapi import (
    discover_openapi_files,
    parse_openapi_file,
)
from forge.domain_intelligence.api.rest import (
    discover_rest_endpoints,
)


def discover_api_contracts(
    project_root: Path,
) -> tuple[ApiContract, ...]:
    """Discover OpenAPI, REST, and GraphQL contracts."""
    contracts: list[ApiContract] = []

    for relative_path in discover_openapi_files(project_root):
        contracts.append(
            parse_openapi_file(project_root, relative_path)
        )

    rest_endpoints = discover_rest_endpoints(project_root)

    if rest_endpoints:
        contracts.append(
            ApiContract(
                contract_id=api_contract_identifier(
                    {
                        "title": "Discovered REST API",
                        "source_path": "source",
                        "endpoint_ids": [
                            endpoint.endpoint_id
                            for endpoint in rest_endpoints
                        ],
                    }
                ),
                title="Discovered REST API",
                style=ApiStyle.REST,
                source_path="source",
                endpoints=rest_endpoints,
            )
        )

    graphql_contract = parse_graphql_contract(project_root)

    if graphql_contract is not None:
        contracts.append(graphql_contract)

    return tuple(
        sorted(
            contracts,
            key=lambda contract: (
                contract.style.value,
                contract.source_path,
                contract.contract_id,
            ),
        )
    )