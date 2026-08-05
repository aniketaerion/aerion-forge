"""Business-domain manifest generation for M4.5."""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from forge.domain_intelligence.business_domain.crm import (
    discover_crm_modules,
)
from forge.domain_intelligence.business_domain.entities import (
    discover_business_entities,
)
from forge.domain_intelligence.business_domain.erp import (
    discover_erp_modules,
)
from forge.domain_intelligence.business_domain.models import (
    BusinessDomainKind,
    BusinessEntity,
)


class BusinessDomainManifest(TypedDict):
    """Typed result of business-domain discovery."""

    domains: tuple[BusinessDomainKind, ...]
    erp_modules: tuple[str, ...]
    crm_modules: tuple[str, ...]
    modules: tuple[str, ...]
    entities: tuple[BusinessEntity, ...]


def business_domain_manifest(
    project_root: Path,
) -> BusinessDomainManifest:
    """Build a deterministic business-domain manifest."""
    erp_modules = discover_erp_modules(project_root)
    crm_modules = discover_crm_modules(project_root)
    entities = discover_business_entities(project_root)

    domains: list[BusinessDomainKind] = []

    if erp_modules:
        domains.append(BusinessDomainKind.ERP)

    if crm_modules:
        domains.append(BusinessDomainKind.CRM)

    if not domains and entities:
        domains.append(BusinessDomainKind.GENERIC)

    if not domains:
        domains.append(BusinessDomainKind.UNKNOWN)

    return {
        "domains": tuple(
            sorted(
                domains,
                key=lambda domain: domain.value,
            )
        ),
        "erp_modules": erp_modules,
        "crm_modules": crm_modules,
        "modules": tuple(
            sorted(
                set(erp_modules) | set(crm_modules)
            )
        ),
        "entities": entities,
    }