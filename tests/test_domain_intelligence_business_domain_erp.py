from pathlib import Path

from forge.domain_intelligence.business_domain.erp import (
    discover_erp_modules,
)


def test_discover_erp_modules(tmp_path: Path) -> None:
    (tmp_path / "inventory").mkdir()
    (tmp_path / "procurement").mkdir()
    (tmp_path / "crm").mkdir()

    assert discover_erp_modules(tmp_path) == (
        "inventory",
        "procurement",
    )