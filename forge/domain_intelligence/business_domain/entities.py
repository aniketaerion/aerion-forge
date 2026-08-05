"""Business entity discovery for M4.5."""

from __future__ import annotations

import re
from pathlib import Path

from forge.domain_intelligence.business_domain.identifiers import (
    business_entity_identifier,
)
from forge.domain_intelligence.business_domain.models import (
    BusinessEntity,
    BusinessEntityKind,
)

_ENTITY_NAME_PATTERN = re.compile(
    r"\b(?:class|interface|type|model)\s+"
    r"(?P<name>[A-Z][A-Za-z0-9_]*)",
)

_TRANSACTION_TOKENS = {
    "invoice",
    "order",
    "purchaseorder",
    "salesorder",
    "payment",
    "receipt",
    "shipment",
    "delivery",
    "quotation",
    "quote",
    "opportunity",
}

_MASTER_DATA_TOKENS = {
    "customer",
    "supplier",
    "vendor",
    "product",
    "item",
    "warehouse",
    "location",
    "employee",
    "account",
    "contact",
    "lead",
}


def classify_business_entity(
    name: str,
) -> BusinessEntityKind:
    """Classify a discovered business entity conservatively."""
    normalized = name.replace("_", "").lower()

    if normalized in _TRANSACTION_TOKENS:
        return BusinessEntityKind.TRANSACTION

    if normalized in _MASTER_DATA_TOKENS:
        if normalized in {"customer", "supplier", "vendor", "account", "contact", "lead"}:
            return BusinessEntityKind.PARTY
        if normalized in {"product", "item"}:
            return BusinessEntityKind.PRODUCT
        if normalized in {"warehouse", "location"}:
            return BusinessEntityKind.LOCATION
        return BusinessEntityKind.MASTER_DATA

    if any(
        token in normalized
        for token in ("document", "attachment", "file")
    ):
        return BusinessEntityKind.DOCUMENT

    if any(
        token in normalized
        for token in ("ledger", "journal", "accounting", "tax")
    ):
        return BusinessEntityKind.FINANCIAL

    return BusinessEntityKind.UNKNOWN


def discover_business_entities(
    project_root: Path,
) -> tuple[BusinessEntity, ...]:
    """Discover domain entities from local source files."""
    discovered: dict[tuple[str, str], BusinessEntity] = {}

    for path in project_root.rglob("*"):
        if not path.is_file():
            continue

        if path.suffix.lower() not in {
            ".py",
            ".ts",
            ".tsx",
            ".js",
            ".jsx",
            ".java",
            ".cs",
            ".prisma",
        }:
            continue

        if any(
            excluded in path.parts
            for excluded in (
                ".git",
                ".venv",
                "venv",
                "node_modules",
                "__pycache__",
                "dist",
                "build",
            )
        ):
            continue

        try:
            source = path.read_text(encoding="utf-8-sig")
        except OSError:
            continue

        relative = path.relative_to(project_root).as_posix()
        module = path.parent.name if path.parent != project_root else None

        for match in _ENTITY_NAME_PATTERN.finditer(source):
            name = match.group("name")
            key = ((module or "").lower(), name.lower())

            discovered[key] = BusinessEntity(
                entity_id=business_entity_identifier(
                    {
                        "name": name,
                        "module": module,
                        "source_path": relative,
                    }
                ),
                name=name,
                kind=classify_business_entity(name),
                module=module,
                source_paths=(relative,),
            )

    return tuple(
        sorted(
            discovered.values(),
            key=lambda entity: (
                entity.module or "",
                entity.name,
            ),
        )
    )