from forge.domain_intelligence.api.models import (
    ApiAuthenticationKind,
    ApiContract,
    ApiEndpoint,
    ApiStyle,
    HttpMethod,
)
from forge.domain_intelligence.api.security import (
    security_findings,
)


def test_security_flags_missing_authentication() -> None:
    contract = ApiContract(
        contract_id="contract-1",
        title="ERP API",
        style=ApiStyle.REST,
        source_path="routes.py",
        endpoints=(
            ApiEndpoint(
                endpoint_id="endpoint-1",
                path="/orders",
                method=HttpMethod.GET,
            ),
            ApiEndpoint(
                endpoint_id="endpoint-2",
                path="/secure-orders",
                method=HttpMethod.GET,
                authentication=(
                    ApiAuthenticationKind.BEARER,
                ),
            ),
        ),
    )

    findings = security_findings((contract,))

    assert len(findings) == 1
    assert findings[0].evidence["path"] == "/orders"