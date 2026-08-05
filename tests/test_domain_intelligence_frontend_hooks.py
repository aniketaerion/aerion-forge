from pathlib import Path

from forge.domain_intelligence.frontend.hooks import (
    extract_hook_names,
    hook_findings,
)


def test_extract_hook_names() -> None:
    source = """
    const [value, setValue] = useState(0)
    const mission = useMission()
    useEffect(() => {}, [])
    """

    assert extract_hook_names(source) == (
        "useEffect",
        "useMission",
        "useState",
    )


def test_hook_findings_include_custom_hooks(
    tmp_path: Path,
) -> None:
    path = tmp_path / "Component.tsx"
    path.write_text(
        "export const Component = () => { useMission(); return null }",
        encoding="utf-8",
    )

    findings = hook_findings(tmp_path)

    assert len(findings) == 1
    assert findings[0].evidence["hooks"] == "useMission"