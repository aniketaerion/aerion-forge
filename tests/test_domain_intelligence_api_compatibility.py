from forge.domain_intelligence.api.compatibility import (
    compatibility_findings,
)
from forge.domain_intelligence.api.models import (
    ApiContract,
    ApiEndpoint,
    ApiStyle,
    HttpMethod,
)


def test_compatibility_detects_duplicate_routes() -> None:
    first = ApiContract(
        contract_id="contract-1",
        title="First API",
        style=ApiStyle.REST,
        source_path="routes.py",
        endpoints=(
            ApiEndpoint(
                endpoint_id="endpoint-1",
                path="/orders",
                method=HttpMethod.GET,
            ),
        ),
    )
    second = ApiContract(
        contract_id="contract-2",
        title="Second API",
        style=ApiStyle.OPENAPI,
        source_path="openapi.yaml",
        endpoints=(
            ApiEndpoint(
                endpoint_id="endpoint-2",
                path="/orders",
                method=HttpMethod.GET,
            ),
        ),
    )

    assert {
        finding.category
        for finding in compatibility_findings(
            (first, second)
        )
    } == {"duplicate_route_contract"}