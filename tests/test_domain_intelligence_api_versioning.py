from forge.domain_intelligence.api.models import (
    ApiContract,
    ApiEndpoint,
    ApiStyle,
    HttpMethod,
)
from forge.domain_intelligence.api.versioning import (
    contract_versions,
    versioning_findings,
)


def test_contract_versions_and_multiple_version_finding() -> None:
    contract = ApiContract(
        contract_id="contract-1",
        title="ERP API",
        version="1.0.0",
        style=ApiStyle.REST,
        source_path="routes.py",
        endpoints=(
            ApiEndpoint(
                endpoint_id="endpoint-1",
                path="/v2/orders",
                method=HttpMethod.GET,
            ),
        ),
    )

    assert contract_versions((contract,)) == (
        "1.0.0",
        "2",
    )
    assert {
        finding.category
        for finding in versioning_findings((contract,))
    } == {"multiple_versions"}