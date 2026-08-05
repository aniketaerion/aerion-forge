[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Content
    )

    $FullPath = Join-Path $RepositoryRoot $Path
    $Directory = Split-Path $FullPath -Parent
    New-Item -ItemType Directory -Path $Directory -Force | Out-Null

    [System.IO.File]::WriteAllText(
        $FullPath,
        $Content,
        [System.Text.UTF8Encoding]::new($false)
    )

    Write-Host "WROTE $Path" -ForegroundColor Green
}

function Assert-CommandSuccess {
    param([Parameter(Mandatory)][string]$Name)

    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

Write-Utf8NoBom "forge\domain_intelligence\business_domain\entities.py" @'
"""Business entity discovery for M4.5."""

from __future__ import annotations

from typing import cast
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
'@

Write-Utf8NoBom "forge\domain_intelligence\business_domain\erp.py" @'
"""ERP domain discovery for M4.5."""

from __future__ import annotations

from typing import cast
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
'@

Write-Utf8NoBom "forge\domain_intelligence\business_domain\crm.py" @'
"""CRM domain discovery for M4.5."""

from __future__ import annotations

from typing import cast
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
'@

Write-Utf8NoBom "forge\domain_intelligence\business_domain\manifest.py" @'
"""Business-domain manifest generation for M4.5."""

from __future__ import annotations

from typing import cast
from pathlib import Path

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
)


def business_domain_manifest(
    project_root: Path,
) -> dict[str, object]:
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
            sorted(domains, key=lambda domain: domain.value)
        ),
        "erp_modules": erp_modules,
        "crm_modules": crm_modules,
        "modules": tuple(
            sorted(set(erp_modules) | set(crm_modules))
        ),
        "entities": entities,
    }
'@

Write-Utf8NoBom "forge\domain_intelligence\business_domain\registry.py" @'
"""Analyzer registry for M4.5 Business Domain Intelligence."""

from __future__ import annotations

from typing import cast
from collections.abc import Callable, Iterable
from pathlib import Path

from forge.domain_intelligence.business_domain.errors import (
    BusinessDomainConfigurationError,
)
from forge.domain_intelligence.business_domain.models import (
    BusinessDomainFinding,
)

BusinessDomainAnalyzer = Callable[
    [Path],
    tuple[BusinessDomainFinding, ...],
]


class BusinessDomainAnalyzerRegistry:
    """Deterministic registry of business-domain analyzers."""

    def __init__(
        self,
        analyzers: Iterable[
            tuple[str, BusinessDomainAnalyzer]
        ] = (),
    ) -> None:
        self._analyzers: dict[
            str,
            BusinessDomainAnalyzer,
        ] = {}

        for name, analyzer in analyzers:
            self.register(name, analyzer)

    def register(
        self,
        name: str,
        analyzer: BusinessDomainAnalyzer,
    ) -> None:
        normalized = name.strip().lower()

        if not normalized:
            raise BusinessDomainConfigurationError(
                "business-domain analyzer name cannot be empty"
            )

        if normalized in self._analyzers:
            raise BusinessDomainConfigurationError(
                f"duplicate business-domain analyzer: {normalized}"
            )

        self._analyzers[normalized] = analyzer

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._analyzers))

    def analyze(
        self,
        project_root: Path,
    ) -> tuple[BusinessDomainFinding, ...]:
        findings: list[BusinessDomainFinding] = []

        for name in self.names():
            findings.extend(
                self._analyzers[name](project_root)
            )

        return tuple(
            sorted(
                findings,
                key=lambda finding: finding.finding_id,
            )
        )
'@

Write-Utf8NoBom "forge\domain_intelligence\business_domain\service.py" @'
"""Business-domain analysis service for M4.5 Package 1."""

from __future__ import annotations

from typing import cast
from forge.domain_intelligence.business_domain.crm import (
    crm_findings,
)
from forge.domain_intelligence.business_domain.erp import (
    erp_findings,
)
from forge.domain_intelligence.business_domain.identifiers import (
    business_domain_project_identifier,
    business_report_identifier,
)
from forge.domain_intelligence.business_domain.manifest import (
    business_domain_manifest,
)
from forge.domain_intelligence.business_domain.models import (
    BusinessDomainAnalysisReport,
    BusinessDomainAnalysisRequest,
    BusinessDomainProject,
)
from forge.domain_intelligence.business_domain.policies import (
    BusinessDomainIntelligencePolicy,
    resolve_business_domain_repository_root,
    validate_business_domain_request,
)
from forge.domain_intelligence.business_domain.registry import (
    BusinessDomainAnalyzerRegistry,
)


def default_business_domain_registry() -> (
    BusinessDomainAnalyzerRegistry
):
    """Return the M4.5 Package 1 analyzer registry."""
    return BusinessDomainAnalyzerRegistry(
        (
            ("crm", crm_findings),
            ("erp", erp_findings),
        )
    )


class BusinessDomainIntelligenceService:
    """Discover business domains, modules, and entities safely."""

    def __init__(
        self,
        policy: BusinessDomainIntelligencePolicy | None = None,
        registry: BusinessDomainAnalyzerRegistry | None = None,
    ) -> None:
        self.policy = (
            policy or BusinessDomainIntelligencePolicy()
        )
        self.registry = (
            registry or default_business_domain_registry()
        )

    def analyze(
        self,
        request: BusinessDomainAnalysisRequest,
    ) -> BusinessDomainAnalysisReport:
        validate_business_domain_request(
            request,
            self.policy,
        )

        repository_root = (
            resolve_business_domain_repository_root(
                request.repository_root,
                self.policy,
            )
        )
        project_root = (
            repository_root / request.project_root
        ).resolve()

        try:
            project_root.relative_to(repository_root)
        except ValueError as exc:
            raise ValueError(
                "resolved business-domain project root "
                "escaped repository"
            ) from exc

        manifest = business_domain_manifest(project_root)
        domains = cast(
            tuple[BusinessDomainKind, ...],
            manifest["domains"],
        )

        modules = cast(
            tuple[str, ...],
            manifest["modules"],
        )

        entities = cast(
            tuple[BusinessEntity, ...],
            manifest["entities"],
        )

        source_files = tuple(
            sorted(
                {
                    source_path
                    for entity in entities
                    for source_path in entity.source_paths
                }
            )
        )

        project_payload = {
            "root": request.project_root,
            "domains": [
                domain.value for domain in domains
            ],
            "modules": modules,
            "source_files": source_files,
        }

        project = BusinessDomainProject(
            project_id=business_domain_project_identifier(
                project_payload
            ),
            root=request.project_root,
            domains=domains,
            modules=modules,
            source_files=source_files,
        )

        findings = self.registry.analyze(project_root)

        return BusinessDomainAnalysisReport(
            report_id=business_report_identifier(
                {
                    "project_id": project.project_id,
                    "entity_ids": [
                        entity.entity_id
                        for entity in entities
                    ],
                    "finding_ids": [
                        finding.finding_id
                        for finding in findings
                    ],
                }
            ),
            project=project,
            entities=entities,
            findings=findings,
        )
'@

Write-Utf8NoBom "tests\test_domain_intelligence_business_domain_entities.py" @'
from pathlib import Path

from forge.domain_intelligence.business_domain.entities import (
    classify_business_entity,
    discover_business_entities,
)
from forge.domain_intelligence.business_domain.models import (
    BusinessEntityKind,
)


def test_classify_business_entity() -> None:
    assert (
        classify_business_entity("PurchaseOrder")
        is BusinessEntityKind.TRANSACTION
    )
    assert (
        classify_business_entity("Customer")
        is BusinessEntityKind.PARTY
    )


def test_discover_business_entities(
    tmp_path: Path,
) -> None:
    module = tmp_path / "procurement"
    module.mkdir()

    (module / "models.py").write_text(
        """
        class PurchaseOrder:
            pass
        """,
        encoding="utf-8",
    )

    entities = discover_business_entities(tmp_path)

    assert len(entities) == 1
    assert entities[0].name == "PurchaseOrder"
    assert entities[0].module == "procurement"
'@

Write-Utf8NoBom "tests\test_domain_intelligence_business_domain_erp.py" @'
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
'@

Write-Utf8NoBom "tests\test_domain_intelligence_business_domain_crm.py" @'
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
'@

Write-Utf8NoBom "tests\test_domain_intelligence_business_domain_manifest.py" @'
from pathlib import Path

from forge.domain_intelligence.business_domain.manifest import (
    business_domain_manifest,
)
from forge.domain_intelligence.business_domain.models import (
    BusinessDomainKind,
)


def test_business_domain_manifest(tmp_path: Path) -> None:
    (tmp_path / "inventory").mkdir()
    (tmp_path / "leads").mkdir()

    manifest = business_domain_manifest(tmp_path)

    assert manifest["domains"] == (
        BusinessDomainKind.CRM,
        BusinessDomainKind.ERP,
    )
'@

Write-Utf8NoBom "tests\test_domain_intelligence_business_domain_registry.py" @'
from pathlib import Path

import pytest

from forge.domain_intelligence.business_domain.errors import (
    BusinessDomainConfigurationError,
)
from forge.domain_intelligence.business_domain.models import (
    BusinessDomainFinding,
)
from forge.domain_intelligence.business_domain.registry import (
    BusinessDomainAnalyzerRegistry,
)


def empty_analyzer(
    project_root: Path,
) -> tuple[BusinessDomainFinding, ...]:
    del project_root
    return ()


def test_business_domain_registry_names_are_sorted() -> None:
    registry = BusinessDomainAnalyzerRegistry(
        (
            ("erp", empty_analyzer),
            ("crm", empty_analyzer),
        )
    )

    assert registry.names() == ("crm", "erp")


def test_business_domain_registry_rejects_duplicates() -> None:
    with pytest.raises(BusinessDomainConfigurationError):
        BusinessDomainAnalyzerRegistry(
            (
                ("erp", empty_analyzer),
                ("ERP", empty_analyzer),
            )
        )
'@

Write-Utf8NoBom "tests\test_domain_intelligence_business_domain_service.py" @'
from pathlib import Path

from forge.domain_intelligence.business_domain.models import (
    BusinessDomainAnalysisRequest,
    BusinessDomainKind,
)
from forge.domain_intelligence.business_domain.service import (
    BusinessDomainIntelligenceService,
    default_business_domain_registry,
)


def initialize_repository(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()


def test_default_business_domain_registry() -> None:
    assert default_business_domain_registry().names() == (
        "crm",
        "erp",
    )


def test_service_discovers_erp_and_crm(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    inventory = tmp_path / "inventory"
    inventory.mkdir()
    leads = tmp_path / "leads"
    leads.mkdir()

    (inventory / "models.py").write_text(
        "class Product:\n    pass\n",
        encoding="utf-8",
    )
    (leads / "models.py").write_text(
        "class Lead:\n    pass\n",
        encoding="utf-8",
    )

    report = BusinessDomainIntelligenceService().analyze(
        BusinessDomainAnalysisRequest(
            repository_root=str(tmp_path),
        )
    )

    assert report.project.domains == (
        BusinessDomainKind.CRM,
        BusinessDomainKind.ERP,
    )
    assert len(report.entities) == 2


def test_service_reports_unknown_domain(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    report = BusinessDomainIntelligenceService().analyze(
        BusinessDomainAnalysisRequest(
            repository_root=str(tmp_path),
        )
    )

    assert report.project.domains == (
        BusinessDomainKind.UNKNOWN,
    )
'@

Write-Host ""
Write-Host "M4.5 Package 1 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_domain_intelligence_business_domain_entities.py `
    .\tests\test_domain_intelligence_business_domain_erp.py `
    .\tests\test_domain_intelligence_business_domain_crm.py `
    .\tests\test_domain_intelligence_business_domain_manifest.py `
    .\tests\test_domain_intelligence_business_domain_registry.py `
    .\tests\test_domain_intelligence_business_domain_service.py `
    -p no:cacheprovider
Assert-CommandSuccess "M4.5 Package 1 tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M4.5 PACKAGE 1 COMPLETE" -ForegroundColor Green

git status --short