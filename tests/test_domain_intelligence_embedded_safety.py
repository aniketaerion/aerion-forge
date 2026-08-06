from pathlib import Path

from forge.domain_intelligence.embedded.safety import (
    analyze_embedded_safety,
)


def test_embedded_safety_analysis(tmp_path: Path) -> None:
    (tmp_path / "control.c").write_text(
        "strcpy(target, source);\nHAL_Delay(100);\n",
        encoding="utf-8",
    )

    findings = analyze_embedded_safety(tmp_path)
    categories = {finding.category for finding in findings}

    assert "unsafe-memory" in categories
    assert "blocking-delay" in categories