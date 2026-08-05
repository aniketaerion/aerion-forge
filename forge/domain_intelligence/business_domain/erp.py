"""ERP domain discovery for M4.5."""

from __future__ import annotations

from pathlib import Path

from forge.domain_intelligence.business_domain.identifiers import (
    business_finding_identifier,
)
from forge.domain_intelligence.business_domain.models import (
    BusinessDomainFinding,
    BusinessFindingSeverity,
)

_ERP_MODULES = (
    "finance",
    "accounting",
    "inventory",
    "procurement",
    "purchase",
    "sales",
    "manufacturing",
    "production",
    "quality",
    "warehouse",
    "logistics",
    "hr",
    "payroll",
)


def discover_erp_modules(
    project_root: Path,
) -> tuple[str, ...]:
    """Discover ERP module names from paths and filenames."""
    modules: set[str] = set()

    for path in project_root.rglob("*"):
        relative = path.relative_to(project_root).as_posix().lower()

        for module in _ERP_MODULES:
            if (
                f"/{module}/" in f"/{relative}/"
                or path.stem.lower() == module
                or path.name.lower().startswith(f"{module}_")
            ):
                modules.add(module)

    return tuple(sorted(modules))


def erp_findings(
    project_root: Path,
) -> tuple[BusinessDomainFinding, ...]:
    """Produce ERP discovery findings."""
    modules = discover_erp_modules(project_root)

    if not modules:
        return ()

    finding_id = business_finding_identifier(
        {
            "category": "erp",
            "modules": modules,
        }
    )

    return (
        BusinessDomainFinding(
            finding_id=finding_id,
            category="erp",
            severity=BusinessFindingSeverity.INFO,
            message="ERP modules detected.",
            evidence={
                "module_count": str(len(modules)),
                "modules": ",".join(modules),
            },
        ),
    )