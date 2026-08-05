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

Write-Utf8NoBom "forge\domain_intelligence\business_domain\errors.py" @'
"""Typed errors for M4.5 Business Domain Intelligence."""

from __future__ import annotations

from forge.domain_intelligence.errors import DomainIntelligenceError


class BusinessDomainIntelligenceError(DomainIntelligenceError):
    """Base error for business-domain intelligence."""


class BusinessDomainConfigurationError(
    BusinessDomainIntelligenceError
):
    """Raised when business-domain configuration is invalid."""


class BusinessDomainPolicyError(
    BusinessDomainIntelligenceError
):
    """Raised when business-domain analysis violates policy."""


class BusinessDomainParseError(
    BusinessDomainIntelligenceError
):
    """Raised when a business-domain artifact cannot be parsed."""
'@

Write-Utf8NoBom "forge\domain_intelligence\business_domain\identifiers.py" @'
"""Deterministic identifiers for M4.5 Business Domain Intelligence."""

from __future__ import annotations

from typing import Any

from forge.domain_intelligence.identifiers import stable_identifier


def business_domain_project_identifier(payload: Any) -> str:
    return stable_identifier("business-domain-project", payload)


def business_entity_identifier(payload: Any) -> str:
    return stable_identifier("business-entity", payload)


def business_workflow_identifier(payload: Any) -> str:
    return stable_identifier("business-workflow", payload)


def business_rule_identifier(payload: Any) -> str:
    return stable_identifier("business-rule", payload)


def business_finding_identifier(payload: Any) -> str:
    return stable_identifier("business-finding", payload)


def business_report_identifier(payload: Any) -> str:
    return stable_identifier("business-report", payload)
'@

Write-Utf8NoBom "forge\domain_intelligence\business_domain\models.py" @'
"""Immutable contracts for M4.5 Business Domain Intelligence."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BusinessDomainKind(StrEnum):
    ERP = "erp"
    CRM = "crm"
    GENERIC = "generic"
    UNKNOWN = "unknown"


class BusinessEntityKind(StrEnum):
    MASTER_DATA = "master_data"
    TRANSACTION = "transaction"
    DOCUMENT = "document"
    PARTY = "party"
    PRODUCT = "product"
    LOCATION = "location"
    FINANCIAL = "financial"
    WORKFLOW = "workflow"
    UNKNOWN = "unknown"


class BusinessRuleSeverity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BusinessFindingSeverity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ImmutableBusinessDomainModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
    )


class BusinessDomainAnalysisRequest(
    ImmutableBusinessDomainModel
):
    repository_root: str = Field(min_length=1)
    project_root: str = Field(default=".", min_length=1)
    max_files: int = Field(default=10000, ge=1, le=100000)


class BusinessEntity(ImmutableBusinessDomainModel):
    entity_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    kind: BusinessEntityKind
    module: str | None = None
    source_paths: tuple[str, ...] = ()
    attributes: tuple[str, ...] = ()


class BusinessWorkflowStep(ImmutableBusinessDomainModel):
    name: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    entity_names: tuple[str, ...] = ()


class BusinessWorkflow(ImmutableBusinessDomainModel):
    workflow_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    module: str | None = None
    steps: tuple[BusinessWorkflowStep, ...] = ()

    @field_validator("steps")
    @classmethod
    def ensure_unique_step_sequence(
        cls,
        steps: tuple[BusinessWorkflowStep, ...],
    ) -> tuple[BusinessWorkflowStep, ...]:
        sequences = [step.sequence for step in steps]
        if len(sequences) != len(set(sequences)):
            raise ValueError("workflow step sequence must be unique")
        return steps


class BusinessRule(ImmutableBusinessDomainModel):
    rule_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    severity: BusinessRuleSeverity
    module: str | None = None
    entity_names: tuple[str, ...] = ()
    source_path: str | None = None


class BusinessDomainProject(ImmutableBusinessDomainModel):
    project_id: str = Field(min_length=1)
    root: str = Field(min_length=1)
    domains: tuple[BusinessDomainKind, ...] = ()
    modules: tuple[str, ...] = ()
    source_files: tuple[str, ...] = ()
    configuration_files: tuple[str, ...] = ()
    detected_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )


class BusinessDomainFinding(ImmutableBusinessDomainModel):
    finding_id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    severity: BusinessFindingSeverity
    message: str = Field(min_length=1)
    path: str | None = None
    evidence: dict[str, str] = Field(default_factory=dict)


class BusinessDomainAnalysisReport(
    ImmutableBusinessDomainModel
):
    report_id: str = Field(min_length=1)
    project: BusinessDomainProject
    entities: tuple[BusinessEntity, ...] = ()
    workflows: tuple[BusinessWorkflow, ...] = ()
    rules: tuple[BusinessRule, ...] = ()
    findings: tuple[BusinessDomainFinding, ...] = ()
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )

    @field_validator("findings")
    @classmethod
    def ensure_unique_findings(
        cls,
        findings: tuple[BusinessDomainFinding, ...],
    ) -> tuple[BusinessDomainFinding, ...]:
        identifiers = [finding.finding_id for finding in findings]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError(
                "business-domain finding identifiers must be unique"
            )
        return findings
'@

Write-Utf8NoBom "forge\domain_intelligence\business_domain\policies.py" @'
"""Safety policies for M4.5 Business Domain Intelligence."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from forge.domain_intelligence.business_domain.errors import (
    BusinessDomainPolicyError,
)
from forge.domain_intelligence.business_domain.models import (
    BusinessDomainAnalysisRequest,
)


class BusinessDomainIntelligencePolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    allow_network: bool = False
    allow_database_connections: bool = False
    allow_external_ontology_fetch: bool = False
    allow_secret_inspection: bool = False
    allow_mutation: bool = False
    require_repository_root: bool = True
    max_files: int = Field(default=10000, ge=1, le=100000)
    max_file_bytes: int = Field(
        default=5_000_000,
        ge=1,
        le=100_000_000,
    )


def resolve_business_domain_repository_root(
    repository_root: str | Path,
    policy: BusinessDomainIntelligencePolicy,
) -> Path:
    root = Path(repository_root).expanduser().resolve()

    if not root.is_dir():
        raise BusinessDomainPolicyError(
            f"repository root does not exist: {root}"
        )

    if policy.require_repository_root and not (root / ".git").exists():
        raise BusinessDomainPolicyError(
            f"repository root is not a Git repository: {root}"
        )

    return root


def validate_business_domain_request(
    request: BusinessDomainAnalysisRequest,
    policy: BusinessDomainIntelligencePolicy,
) -> None:
    if request.max_files > policy.max_files:
        raise BusinessDomainPolicyError(
            f"request exceeds maximum file count: {policy.max_files}"
        )

    project_root = Path(request.project_root)

    if project_root.is_absolute() or ".." in project_root.parts:
        raise BusinessDomainPolicyError(
            "project root must remain repository-relative"
        )
'@

Write-Utf8NoBom "forge\domain_intelligence\business_domain\__init__.py" @'
"""M4.5 Business Domain Intelligence public API."""

from forge.domain_intelligence.business_domain.errors import (
    BusinessDomainConfigurationError,
    BusinessDomainIntelligenceError,
    BusinessDomainParseError,
    BusinessDomainPolicyError,
)
from forge.domain_intelligence.business_domain.identifiers import (
    business_domain_project_identifier,
    business_entity_identifier,
    business_finding_identifier,
    business_report_identifier,
    business_rule_identifier,
    business_workflow_identifier,
)
from forge.domain_intelligence.business_domain.models import (
    BusinessDomainAnalysisReport,
    BusinessDomainAnalysisRequest,
    BusinessDomainFinding,
    BusinessDomainKind,
    BusinessDomainProject,
    BusinessEntity,
    BusinessEntityKind,
    BusinessFindingSeverity,
    BusinessRule,
    BusinessRuleSeverity,
    BusinessWorkflow,
    BusinessWorkflowStep,
)
from forge.domain_intelligence.business_domain.policies import (
    BusinessDomainIntelligencePolicy,
    resolve_business_domain_repository_root,
    validate_business_domain_request,
)

__all__ = [
    "BusinessDomainAnalysisReport",
    "BusinessDomainAnalysisRequest",
    "BusinessDomainConfigurationError",
    "BusinessDomainFinding",
    "BusinessDomainIntelligenceError",
    "BusinessDomainIntelligencePolicy",
    "BusinessDomainKind",
    "BusinessDomainParseError",
    "BusinessDomainPolicyError",
    "BusinessDomainProject",
    "BusinessEntity",
    "BusinessEntityKind",
    "BusinessFindingSeverity",
    "BusinessRule",
    "BusinessRuleSeverity",
    "BusinessWorkflow",
    "BusinessWorkflowStep",
    "business_domain_project_identifier",
    "business_entity_identifier",
    "business_finding_identifier",
    "business_report_identifier",
    "business_rule_identifier",
    "business_workflow_identifier",
    "resolve_business_domain_repository_root",
    "validate_business_domain_request",
]
'@

Write-Utf8NoBom "tests\test_domain_intelligence_business_domain_identifiers.py" @'
from forge.domain_intelligence.business_domain.identifiers import (
    business_domain_project_identifier,
    business_entity_identifier,
)


def test_business_domain_project_identifier_is_deterministic() -> None:
    first = business_domain_project_identifier(
        {"root": "apps/erp", "domain": "erp"}
    )
    second = business_domain_project_identifier(
        {"domain": "erp", "root": "apps/erp"}
    )

    assert first == second
    assert first.startswith("business-domain-project-")


def test_business_entity_identifier_changes_by_module() -> None:
    first = business_entity_identifier(
        {"name": "PurchaseOrder", "module": "procurement"}
    )
    second = business_entity_identifier(
        {"name": "PurchaseOrder", "module": "inventory"}
    )

    assert first != second
'@

Write-Utf8NoBom "tests\test_domain_intelligence_business_domain_models.py" @'
import pytest
from pydantic import ValidationError

from forge.domain_intelligence.business_domain.models import (
    BusinessDomainAnalysisReport,
    BusinessDomainFinding,
    BusinessDomainKind,
    BusinessDomainProject,
    BusinessEntity,
    BusinessEntityKind,
    BusinessFindingSeverity,
    BusinessWorkflow,
    BusinessWorkflowStep,
)


def test_business_entity_supports_module_and_attributes() -> None:
    entity = BusinessEntity(
        entity_id="entity-1",
        name="PurchaseOrder",
        kind=BusinessEntityKind.TRANSACTION,
        module="procurement",
        attributes=("supplier_id", "status"),
    )

    assert entity.module == "procurement"


def test_business_workflow_rejects_duplicate_sequences() -> None:
    with pytest.raises(ValidationError):
        BusinessWorkflow(
            workflow_id="workflow-1",
            name="Procure to Pay",
            steps=(
                BusinessWorkflowStep(
                    name="Create Requisition",
                    sequence=1,
                ),
                BusinessWorkflowStep(
                    name="Approve Requisition",
                    sequence=1,
                ),
            ),
        )


def test_business_report_rejects_duplicate_findings() -> None:
    project = BusinessDomainProject(
        project_id="project-1",
        root="apps/erp",
        domains=(BusinessDomainKind.ERP,),
    )
    finding = BusinessDomainFinding(
        finding_id="finding-1",
        category="workflow",
        severity=BusinessFindingSeverity.HIGH,
        message="Broken workflow.",
    )

    with pytest.raises(ValidationError):
        BusinessDomainAnalysisReport(
            report_id="report-1",
            project=project,
            findings=(finding, finding),
        )
'@

Write-Utf8NoBom "tests\test_domain_intelligence_business_domain_policies.py" @'
from pathlib import Path

import pytest

from forge.domain_intelligence.business_domain.errors import (
    BusinessDomainPolicyError,
)
from forge.domain_intelligence.business_domain.models import (
    BusinessDomainAnalysisRequest,
)
from forge.domain_intelligence.business_domain.policies import (
    BusinessDomainIntelligencePolicy,
    resolve_business_domain_repository_root,
    validate_business_domain_request,
)


def test_business_domain_policy_is_offline_and_read_only() -> None:
    policy = BusinessDomainIntelligencePolicy()

    assert not policy.allow_network
    assert not policy.allow_database_connections
    assert not policy.allow_external_ontology_fetch
    assert not policy.allow_secret_inspection
    assert not policy.allow_mutation


def test_business_domain_repository_requires_git(
    tmp_path: Path,
) -> None:
    with pytest.raises(BusinessDomainPolicyError):
        resolve_business_domain_repository_root(
            tmp_path,
            BusinessDomainIntelligencePolicy(),
        )


def test_business_domain_request_rejects_path_escape() -> None:
    request = BusinessDomainAnalysisRequest(
        repository_root=".",
        project_root="../outside",
    )

    with pytest.raises(BusinessDomainPolicyError):
        validate_business_domain_request(
            request,
            BusinessDomainIntelligencePolicy(),
        )
'@

Write-Utf8NoBom "docs\domain_intelligence\business_domain\ARCHITECTURE.md" @'
# M4.5 Business Domain Intelligence Architecture

M4.5 provides read-only, domain-agnostic business analysis through typed
entities, workflows, rules, findings, and reporting. ERP and CRM are adapters
over the same generic business-domain model rather than hard-coded platform
assumptions.

Package 0 establishes immutable contracts and the safety boundary.
'@

Write-Utf8NoBom "docs\domain_intelligence\business_domain\SPECIFICATION.md" @'
# M4.5 Business Domain Intelligence Specification

Business-domain intelligence shall identify:

- business entities and master data;
- transactional documents;
- workflows and state transitions;
- validation and approval rules;
- ERP and CRM module boundaries;
- cross-module dependencies and risks.

Analysis remains local, deterministic, bounded, offline, and read-only.
'@

Write-Utf8NoBom "docs\domain_intelligence\business_domain\DATA_MODEL.md" @'
# M4.5 Business Domain Data Model

Primary contracts:

- BusinessDomainAnalysisRequest
- BusinessDomainProject
- BusinessEntity
- BusinessWorkflowStep
- BusinessWorkflow
- BusinessRule
- BusinessDomainFinding
- BusinessDomainAnalysisReport
- BusinessDomainIntelligencePolicy
'@

Write-Utf8NoBom "docs\domain_intelligence\business_domain\SECURITY_MODEL.md" @'
# M4.5 Business Domain Security Model

Business-domain analysis is fail-closed.

- Network access is disabled.
- Database connections are disabled.
- External ontology fetching is disabled.
- Secret inspection is disabled.
- Source mutation is disabled.
- Repository path escape is rejected.
- File count and file-size limits are enforced.
'@

Write-Utf8NoBom "docs\domain_intelligence\business_domain\ACCEPTANCE_CRITERIA.md" @'
# M4.5 Package 0 Acceptance Criteria

- Business-domain contracts are immutable and typed.
- Identifiers are deterministic.
- ERP, CRM, generic, and unknown domains are represented.
- Entities, workflows, rules, and findings are modeled.
- Duplicate workflow sequences and findings are rejected.
- Analysis is offline and read-only by default.
- Repository path escape is rejected.
- Ruff, MyPy, focused tests, and full regression pass.
'@

Write-Host ""
Write-Host "M4.5 Package 0 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_domain_intelligence_business_domain_identifiers.py `
    .\tests\test_domain_intelligence_business_domain_models.py `
    .\tests\test_domain_intelligence_business_domain_policies.py `
    -p no:cacheprovider
Assert-CommandSuccess "M4.5 Package 0 tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M4.5 PACKAGE 0 COMPLETE" -ForegroundColor Green

git status --short