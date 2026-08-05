from forge.domain_intelligence.backend.identifiers import (
    backend_finding_identifier,
    backend_project_identifier,
)


def test_backend_project_identifier_is_deterministic() -> None:
    first = backend_project_identifier(
        {"root": "apps/api", "runtime": "nodejs"}
    )
    second = backend_project_identifier(
        {"runtime": "nodejs", "root": "apps/api"}
    )

    assert first == second
    assert first.startswith("backend-project-")


def test_backend_finding_identifier_changes_with_path() -> None:
    first = backend_finding_identifier({"path": "src/app.ts"})
    second = backend_finding_identifier({"path": "src/main.py"})

    assert first != second