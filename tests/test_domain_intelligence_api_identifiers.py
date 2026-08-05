from forge.domain_intelligence.api.identifiers import (
    api_endpoint_identifier,
    api_project_identifier,
)


def test_api_project_identifier_is_deterministic() -> None:
    first = api_project_identifier(
        {"root": "apps/api", "style": "rest"}
    )
    second = api_project_identifier(
        {"style": "rest", "root": "apps/api"}
    )

    assert first == second
    assert first.startswith("api-project-")


def test_api_endpoint_identifier_changes_by_method() -> None:
    first = api_endpoint_identifier(
        {"path": "/orders", "method": "GET"}
    )
    second = api_endpoint_identifier(
        {"path": "/orders", "method": "POST"}
    )

    assert first != second