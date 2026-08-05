from pathlib import Path

from forge.domain_intelligence.business_domain.crm import (
    discover_crm_modules,
)


def test_discover_crm_modules(tmp_path: Path) -> None:
    (tmp_path / "leads").mkdir()
    (tmp_path / "opportunities").mkdir()
    (tmp_path / "inventory").mkdir()

    assert discover_crm_modules(tmp_path) == (
        "lead",
        "opportunity",
    )