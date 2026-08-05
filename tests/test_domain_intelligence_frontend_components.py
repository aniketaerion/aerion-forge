from pathlib import Path

from forge.domain_intelligence.frontend.components import (
    component_findings,
    extract_component_names,
)


def test_extract_component_names() -> None:
    source = """
    function Dashboard() { return <div /> }
    const StatusCard = () => <section />
    """

    assert extract_component_names(source) == (
        "Dashboard",
        "StatusCard",
    )


def test_component_findings_include_file(
    tmp_path: Path,
) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "Dashboard.tsx").write_text(
        "export function Dashboard() { return <div /> }",
        encoding="utf-8",
    )

    findings = component_findings(tmp_path)

    assert len(findings) == 1
    assert findings[0].path == "src/Dashboard.tsx"