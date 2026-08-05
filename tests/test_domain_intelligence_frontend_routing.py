from pathlib import Path

from forge.domain_intelligence.frontend.routing import (
    extract_route_paths,
    route_findings,
)


def test_extract_route_paths() -> None:
    source = """
    <Route path="/dashboard" element={<Dashboard />} />
    <Route path="/settings" element={<Settings />} />
    """

    assert extract_route_paths(source) == (
        "/dashboard",
        "/settings",
    )


def test_nextjs_page_is_discovered(tmp_path: Path) -> None:
    page = tmp_path / "app" / "dashboard"
    page.mkdir(parents=True)
    (page / "page.tsx").write_text(
        "export default function Page() { return <div /> }",
        encoding="utf-8",
    )

    findings = route_findings(tmp_path)

    assert len(findings) == 1
    assert findings[0].path == "app/dashboard/page.tsx"