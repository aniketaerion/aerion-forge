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

Write-Utf8NoBom "forge\domain_intelligence\business_domain\ontology.py" @'
"""Business ontology construction for M4.5."""

from __future__ import annotations

from collections import defaultdict

from forge.domain_intelligence.business_domain.models import (
    BusinessEntity,
)


def build_business_ontology(
    entities: tuple[BusinessEntity, ...],
) -> dict[str, tuple[str, ...]]:
    """Build a deterministic module-to-entity ontology."""
    ontology: dict[str, set[str]] = defaultdict(set)

    for entity in entities:
        module = entity.module or "unassigned"
        ontology[module].add(entity.name)

    return {
        module: tuple(sorted(names))
        for module, names in sorted(ontology.items())
    }


def ontology_relationships(
    entities: tuple[BusinessEntity, ...],
) -> tuple[tuple[str, str, str], ...]:
    """Infer conservative cross-module relationships by shared names."""
    by_name: dict[str, list[BusinessEntity]] = defaultdict(list)

    for entity in entities:
        by_name[entity.name.lower()].append(entity)

    relationships: set[tuple[str, str, str]] = set()

    for matching_entities in by_name.values():
        if len(matching_entities) < 2:
            continue

        ordered = sorted(
            matching_entities,
            key=lambda entity: (
                entity.module or "",
                entity.entity_id,
            ),
        )

        for index, source in enumerate(ordered):
            for target in ordered[index + 1 :]:
                relationships.add(
                    (
                        source.entity_id,
                        target.entity_id,
                        "shared_business_concept",
                    )
                )

    return tuple(sorted(relationships))
'@

Write-Utf8NoBom "forge\domain_intelligence\business_domain\workflows.py" @'
"""Business workflow discovery for M4.5."""

from __future__ import annotations

from pathlib import Path

from forge.domain_intelligence.business_domain.identifiers import (
    business_workflow_identifier,
)
from forge.domain_intelligence.business_domain.models import (
    BusinessWorkflow,
    BusinessWorkflowStep,
)

_STANDARD_WORKFLOWS: dict[
    str,
    tuple[tuple[str, tuple[str, ...]], ...],
] = {
    "procure_to_pay": (
        ("Create Requisition", ("PurchaseRequisition",)),
        ("Approve Requisition", ("PurchaseRequisition",)),
        ("Issue Purchase Order", ("PurchaseOrder",)),
        ("Receive Goods", ("GoodsReceipt",)),
        ("Process Supplier Invoice", ("SupplierInvoice",)),
        ("Pay Supplier", ("Payment",)),
    ),
    "order_to_cash": (
        ("Create Sales Order", ("SalesOrder",)),
        ("Confirm Order", ("SalesOrder",)),
        ("Dispatch Goods", ("Delivery",)),
        ("Raise Customer Invoice", ("CustomerInvoice",)),
        ("Receive Payment", ("Payment",)),
    ),
    "lead_to_order": (
        ("Capture Lead", ("Lead",)),
        ("Qualify Lead", ("Lead",)),
        ("Create Opportunity", ("Opportunity",)),
        ("Prepare Quote", ("Quote",)),
        ("Create Sales Order", ("SalesOrder",)),
    ),
}


def discover_business_workflows(
    project_root: Path,
    modules: tuple[str, ...],
) -> tuple[BusinessWorkflow, ...]:
    """Map detected modules to standard business workflows."""
    del project_root

    workflows: list[BusinessWorkflow] = []
    module_set = set(modules)

    candidates: list[tuple[str, str]] = []

    if module_set & {"procurement", "purchase"}:
        candidates.append(("procure_to_pay", "procurement"))

    if module_set & {"sales", "inventory", "logistics"}:
        candidates.append(("order_to_cash", "sales"))

    if module_set & {
        "lead",
        "opportunity",
        "quote",
        "account",
        "contact",
    }:
        candidates.append(("lead_to_order", "crm"))

    for workflow_name, module in candidates:
        steps = tuple(
            BusinessWorkflowStep(
                name=step_name,
                sequence=index,
                entity_names=entity_names,
            )
            for index, (step_name, entity_names) in enumerate(
                _STANDARD_WORKFLOWS[workflow_name],
                start=1,
            )
        )

        workflows.append(
            BusinessWorkflow(
                workflow_id=business_workflow_identifier(
                    {
                        "name": workflow_name,
                        "module": module,
                        "steps": [
                            step.name for step in steps
                        ],
                    }
                ),
                name=workflow_name.replace("_", " ").title(),
                module=module,
                steps=steps,
            )
        )

    return tuple(
        sorted(
            workflows,
            key=lambda workflow: workflow.workflow_id,
        )
    )
'@

Write-Utf8NoBom "forge\domain_intelligence\business_domain\rules.py" @'
"""Business rule inference for M4.5."""

from __future__ import annotations

from forge.domain_intelligence.business_domain.identifiers import (
    business_rule_identifier,
)
from forge.domain_intelligence.business_domain.models import (
    BusinessEntity,
    BusinessRule,
    BusinessRuleSeverity,
)


def infer_business_rules(
    entities: tuple[BusinessEntity, ...],
) -> tuple[BusinessRule, ...]:
    """Infer conservative rules from known business entities."""
    rules: list[BusinessRule] = []
    names = {entity.name.lower() for entity in entities}

    def add_rule(
        *,
        name: str,
        description: str,
        severity: BusinessRuleSeverity,
        entity_names: tuple[str, ...],
        module: str | None = None,
    ) -> None:
        rules.append(
            BusinessRule(
                rule_id=business_rule_identifier(
                    {
                        "name": name,
                        "entities": entity_names,
                        "module": module,
                    }
                ),
                name=name,
                description=description,
                severity=severity,
                module=module,
                entity_names=entity_names,
            )
        )

    if "purchaseorder" in names:
        add_rule(
            name="Purchase Order Requires Approval",
            description=(
                "Purchase orders should pass an approval control "
                "before supplier commitment."
            ),
            severity=BusinessRuleSeverity.HIGH,
            entity_names=("PurchaseOrder",),
            module="procurement",
        )

    if "salesorder" in names:
        add_rule(
            name="Sales Order Requires Customer",
            description=(
                "Sales orders should reference a valid customer "
                "or account."
            ),
            severity=BusinessRuleSeverity.HIGH,
            entity_names=("SalesOrder", "Customer"),
            module="sales",
        )

    if "invoice" in names or {
        "customerinvoice",
        "supplierinvoice",
    } & names:
        add_rule(
            name="Invoice Totals Must Balance",
            description=(
                "Invoice line totals, tax, discounts, and payable "
                "amount should reconcile."
            ),
            severity=BusinessRuleSeverity.CRITICAL,
            entity_names=(
                "CustomerInvoice",
                "SupplierInvoice",
            ),
            module="finance",
        )

    if "lead" in names:
        add_rule(
            name="Lead Conversion Requires Qualification",
            description=(
                "A lead should be qualified before conversion to "
                "an opportunity."
            ),
            severity=BusinessRuleSeverity.MEDIUM,
            entity_names=("Lead", "Opportunity"),
            module="crm",
        )

    return tuple(
        sorted(
            rules,
            key=lambda rule: rule.rule_id,
        )
    )
'@

Write-Utf8NoBom "forge\domain_intelligence\business_domain\plugin.py" @'
"""Business-domain plugin surface for M4.5."""

from __future__ import annotations

from dataclasses import dataclass

from forge.domain_intelligence.business_domain.models import (
    BusinessDomainAnalysisReport,
    BusinessDomainAnalysisRequest,
)
from forge.domain_intelligence.business_domain.service import (
    BusinessDomainIntelligenceService,
)


@dataclass(frozen=True, slots=True)
class BusinessDomainPlugin:
    """Adapter exposing business-domain intelligence as a plugin."""

    name: str = "business-domain"
    version: str = "m4.5"

    def analyze(
        self,
        request: BusinessDomainAnalysisRequest,
    ) -> BusinessDomainAnalysisReport:
        return BusinessDomainIntelligenceService().analyze(request)


def business_domain_plugin() -> BusinessDomainPlugin:
    """Return the default business-domain plugin."""
    return BusinessDomainPlugin()
'@

Write-Utf8NoBom "forge\domain_intelligence\business_domain\service.py" @'
"""Complete business-domain analysis service for M4.5."""

from __future__ import annotations

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
from forge.domain_intelligence.business_domain.ontology import (
    build_business_ontology,
)
from forge.domain_intelligence.business_domain.policies import (
    BusinessDomainIntelligencePolicy,
    resolve_business_domain_repository_root,
    validate_business_domain_request,
)
from forge.domain_intelligence.business_domain.registry import (
    BusinessDomainAnalyzerRegistry,
)
from forge.domain_intelligence.business_domain.rules import (
    infer_business_rules,
)
from forge.domain_intelligence.business_domain.workflows import (
    discover_business_workflows,
)


def default_business_domain_registry() -> (
    BusinessDomainAnalyzerRegistry
):
    """Return the M4.5 analyzer registry."""
    return BusinessDomainAnalyzerRegistry(
        (
            ("crm", crm_findings),
            ("erp", erp_findings),
        )
    )


class BusinessDomainIntelligenceService:
    """Discover and analyze business-domain architecture."""

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
        """Run the M4.5 business-domain analysis pipeline."""
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
        domains = manifest["domains"]
        modules = manifest["modules"]
        entities = manifest["entities"]

        source_files = tuple(
            sorted(
                {
                    source_path
                    for entity in entities
                    for source_path in entity.source_paths
                }
            )
        )

        ontology = build_business_ontology(entities)
        workflows = discover_business_workflows(
            project_root,
            modules,
        )
        rules = infer_business_rules(entities)

        project_payload = {
            "root": request.project_root,
            "domains": [
                domain.value for domain in domains
            ],
            "modules": modules,
            "source_files": source_files,
            "ontology": ontology,
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
                    "workflow_ids": [
                        workflow.workflow_id
                        for workflow in workflows
                    ],
                    "rule_ids": [
                        rule.rule_id for rule in rules
                    ],
                    "finding_ids": [
                        finding.finding_id
                        for finding in findings
                    ],
                }
            ),
            project=project,
            entities=entities,
            workflows=workflows,
            rules=rules,
            findings=findings,
        )
'@

Write-Utf8NoBom "tests\test_domain_intelligence_business_domain_ontology.py" @'
from forge.domain_intelligence.business_domain.models import (
    BusinessEntity,
    BusinessEntityKind,
)
from forge.domain_intelligence.business_domain.ontology import (
    build_business_ontology,
    ontology_relationships,
)


def test_build_business_ontology() -> None:
    entities = (
        BusinessEntity(
            entity_id="entity-1",
            name="Customer",
            kind=BusinessEntityKind.PARTY,
            module="sales",
        ),
        BusinessEntity(
            entity_id="entity-2",
            name="Product",
            kind=BusinessEntityKind.PRODUCT,
            module="inventory",
        ),
    )

    assert build_business_ontology(entities) == {
        "inventory": ("Product",),
        "sales": ("Customer",),
    }


def test_ontology_relationships_detect_shared_concept() -> None:
    entities = (
        BusinessEntity(
            entity_id="entity-1",
            name="Customer",
            kind=BusinessEntityKind.PARTY,
            module="sales",
        ),
        BusinessEntity(
            entity_id="entity-2",
            name="Customer",
            kind=BusinessEntityKind.PARTY,
            module="crm",
        ),
    )

    assert ontology_relationships(entities) == (
        (
            "entity-2",
            "entity-1",
            "shared_business_concept",
        ),
    )
'@

Write-Utf8NoBom "tests\test_domain_intelligence_business_domain_workflows.py" @'
from pathlib import Path

from forge.domain_intelligence.business_domain.workflows import (
    discover_business_workflows,
)


def test_discover_standard_workflows(
    tmp_path: Path,
) -> None:
    workflows = discover_business_workflows(
        tmp_path,
        (
            "procurement",
            "sales",
            "lead",
        ),
    )

    assert {
        workflow.name for workflow in workflows
    } == {
        "Lead To Order",
        "Order To Cash",
        "Procure To Pay",
    }
'@

Write-Utf8NoBom "tests\test_domain_intelligence_business_domain_rules.py" @'
from forge.domain_intelligence.business_domain.models import (
    BusinessEntity,
    BusinessEntityKind,
    BusinessRuleSeverity,
)
from forge.domain_intelligence.business_domain.rules import (
    infer_business_rules,
)


def test_infer_business_rules() -> None:
    rules = infer_business_rules(
        (
            BusinessEntity(
                entity_id="entity-1",
                name="PurchaseOrder",
                kind=BusinessEntityKind.TRANSACTION,
                module="procurement",
            ),
            BusinessEntity(
                entity_id="entity-2",
                name="Lead",
                kind=BusinessEntityKind.PARTY,
                module="crm",
            ),
        )
    )

    assert {
        rule.name for rule in rules
    } == {
        "Lead Conversion Requires Qualification",
        "Purchase Order Requires Approval",
    }
    assert any(
        rule.severity is BusinessRuleSeverity.HIGH
        for rule in rules
    )
'@

Write-Utf8NoBom "tests\test_domain_intelligence_business_domain_plugin.py" @'
from pathlib import Path

from forge.domain_intelligence.business_domain.models import (
    BusinessDomainAnalysisRequest,
)
from forge.domain_intelligence.business_domain.plugin import (
    business_domain_plugin,
)


def test_business_domain_plugin_analyzes_repository(
    tmp_path: Path,
) -> None:
    (tmp_path / ".git").mkdir()

    plugin = business_domain_plugin()
    report = plugin.analyze(
        BusinessDomainAnalysisRequest(
            repository_root=str(tmp_path),
        )
    )

    assert plugin.name == "business-domain"
    assert report.project.root == "."
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


def test_service_discovers_workflows_and_rules(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    procurement = tmp_path / "procurement"
    procurement.mkdir()

    (procurement / "models.py").write_text(
        """
        class PurchaseOrder:
            pass
        """,
        encoding="utf-8",
    )

    report = BusinessDomainIntelligenceService().analyze(
        BusinessDomainAnalysisRequest(
            repository_root=str(tmp_path),
        )
    )

    assert report.project.domains == (
        BusinessDomainKind.ERP,
    )
    assert report.workflows
    assert report.rules
    assert {
        rule.name for rule in report.rules
    } == {"Purchase Order Requires Approval"}


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
    assert not report.workflows
    assert not report.rules
'@

Write-Host ""
Write-Host "M4.5 Package 2 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_domain_intelligence_business_domain_ontology.py `
    .\tests\test_domain_intelligence_business_domain_workflows.py `
    .\tests\test_domain_intelligence_business_domain_rules.py `
    .\tests\test_domain_intelligence_business_domain_plugin.py `
    .\tests\test_domain_intelligence_business_domain_service.py `
    -p no:cacheprovider
Assert-CommandSuccess "M4.5 Package 2 tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M4.5 PACKAGE 2 COMPLETE" -ForegroundColor Green

git status --short