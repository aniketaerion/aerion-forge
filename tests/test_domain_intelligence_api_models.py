import pytest
from pydantic import ValidationError

from forge.domain_intelligence.api.models import (
    ApiAnalysisReport,
    ApiAuthenticationKind,
    ApiContract,
    ApiEndpoint,
    ApiFinding,
    ApiFindingSeverity,
    ApiProject,
    ApiStyle,
    HttpMethod,
)


def test_api_contract_supports_endpoint_metadata() -> None:
    endpoint = ApiEndpoint(
        endpoint_id="endpoint-1",
        path="/orders",
        method=HttpMethod.GET,
        authentication=(ApiAuthenticationKind.BEARER,),
        tags=("orders",),
    )
    contract = ApiContract(
        contract_id="contract-1",
        title="ERP API",
        version="1.0.0",
        style=ApiStyle.OPENAPI,
        source_path="openapi.yaml",
        endpoints=(endpoint,),
    )

    assert contract.endpoints[0].method is HttpMethod.GET


def test_api_contract_rejects_duplicate_endpoints() -> None:
    endpoint = ApiEndpoint(
        endpoint_id="endpoint-1",
        path="/orders",
        method=HttpMethod.GET,
    )

    with pytest.raises(ValidationError):
        ApiContract(
            contract_id="contract-1",
            title="ERP API",
            style=ApiStyle.REST,
            source_path="routes.py",
            endpoints=(endpoint, endpoint),
        )


def test_api_report_rejects_duplicate_findings() -> None:
    project = ApiProject(
        project_id="api-project-1",
        root="apps/api",
        styles=(ApiStyle.REST,),
    )
    finding = ApiFinding(
        finding_id="api-finding-1",
        category="security",
        severity=ApiFindingSeverity.HIGH,
        message="Missing authentication.",
    )

    with pytest.raises(ValidationError):
        ApiAnalysisReport(
            report_id="api-report-1",
            project=project,
            findings=(finding, finding),
        )