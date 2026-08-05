"""CRM domain discovery for M4.5."""

from __future__ import annotations

from pathlib import Path

from forge.domain_intelligence.business_domain.identifiers import (
    business_finding_identifier,
)
from forge.domain_intelligence.business_domain.models import (
    BusinessDomainFinding,
    BusinessFindingSeverity,
)

_CRM_MODULE_ALIASES = {
    "lead": "lead",
    "leads": "lead",
    "contact": "contact",
    "contacts": "contact",
    "account": "account",
    "accounts": "account",
    "opportunity": "opportunity",
    "opportunities": "opportunity",
    "campaign": "campaign",
    "campaigns": "campaign",
    "case": "case",
    "cases": "case",
    "quote": "quote",
    "quotes": "quote",
    "forecast": "forecast",
    "forecasts": "forecast",
}


def discover_crm_modules(
    project_root: Path,
) -> tuple[str, ...]:
    """Discover CRM module names from paths and filenames."""
    modules: set[str] = set()

    for path in project_root.rglob("*"):
        relative = path.relative_to(project_root).as_posix().lower()

        for alias, canonical in _CRM_MODULE_ALIASES.items():
            if (
                f"/{alias}/" in f"/{relative}/"
                or path.stem.lower() == alias
                or path.name.lower().startswith(f"{alias}_")
            ):
                modules.add(canonical)

    return tuple(sorted(modules))


def crm_findings(
    project_root: Path,
) -> tuple[BusinessDomainFinding, ...]:
    """Produce CRM discovery findings."""
    modules = discover_crm_modules(project_root)

    if not modules:
        return ()

    finding_id = business_finding_identifier(
        {
            "category": "crm",
            "modules": modules,
        }
    )

    return (
        BusinessDomainFinding(
            finding_id=finding_id,
            category="crm",
            severity=BusinessFindingSeverity.INFO,
            message="CRM modules detected.",
            evidence={
                "module_count": str(len(modules)),
                "modules": ",".join(modules),
            },
        ),
    )