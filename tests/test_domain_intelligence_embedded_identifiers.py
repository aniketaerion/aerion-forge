from forge.domain_intelligence.embedded.identifiers import (
    embedded_component_identifier,
    embedded_project_identifier,
)


def test_embedded_project_identifier_is_deterministic() -> None:
    first = embedded_project_identifier(
        {"root": "firmware", "platform": "px4"}
    )
    second = embedded_project_identifier(
        {"platform": "px4", "root": "firmware"}
    )

    assert first == second
    assert first.startswith("embedded-project-")


def test_embedded_component_identifier_changes_by_platform() -> None:
    first = embedded_component_identifier(
        {"name": "navigator", "platform": "px4"}
    )
    second = embedded_component_identifier(
        {"name": "navigator", "platform": "ardupilot"}
    )

    assert first != second