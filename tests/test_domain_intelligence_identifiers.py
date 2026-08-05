from forge.domain_intelligence.identifiers import (
    domain_plugin_identifier,
    frontend_project_identifier,
)


def test_domain_plugin_identifier_is_deterministic() -> None:
    first = domain_plugin_identifier({"name": "frontend", "version": "1.0"})
    second = domain_plugin_identifier({"version": "1.0", "name": "frontend"})

    assert first == second
    assert first.startswith("domain-plugin-")


def test_frontend_project_identifier_changes_with_root() -> None:
    first = frontend_project_identifier({"root": "apps/erp"})
    second = frontend_project_identifier({"root": "apps/crm"})

    assert first != second