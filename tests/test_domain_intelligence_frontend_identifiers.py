from forge.domain_intelligence.frontend.identifiers import (
    frontend_report_identifier,
)


def test_frontend_report_identifier_has_expected_prefix() -> None:
    identifier = frontend_report_identifier({"project_id": "project-1"})

    assert identifier.startswith("frontend-report-")