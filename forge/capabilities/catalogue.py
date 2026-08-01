"""Explicit, reviewable built-in Forge capability catalogue."""

from forge.capabilities.models import (
    CapabilityAccessMode as Access,
)
from forge.capabilities.models import (
    CapabilityApprovalPolicy as Approval,
)
from forge.capabilities.models import (
    CapabilityAvailabilityScope as Scope,
)
from forge.capabilities.models import (
    CapabilityCategory as Category,
)
from forge.capabilities.models import (
    CapabilityCommand as Command,
)
from forge.capabilities.models import (
    CapabilityDefinition,
)
from forge.capabilities.models import (
    CapabilityImplementationStatus as Implementation,
)
from forge.capabilities.models import (
    CapabilityInput as Input,
)
from forge.capabilities.models import (
    CapabilityInputType as InputType,
)
from forge.capabilities.models import (
    CapabilityLifecycle as Lifecycle,
)
from forge.capabilities.models import (
    CapabilityMaturity as Maturity,
)
from forge.capabilities.models import (
    CapabilityOutput as Output,
)
from forge.capabilities.models import (
    CapabilityOutputType as OutputType,
)
from forge.workspace.models import ProjectType

ALL_PROJECT_TYPES = tuple(item.value for item in ProjectType)


def _input(
    input_id: str, kind: InputType, *, required: bool = True, producer: str | None = None
) -> Input:
    return Input(
        input_id=input_id,
        input_type=kind,
        name=input_id.replace("-", " ").title(),
        description=f"Declared {kind.value} input.",
        required=required,
        produced_by_capability=producer,
    )


def _output(output_id: str, kind: OutputType, path: str | None = None) -> Output:
    return Output(
        output_id=output_id,
        output_type=kind,
        name=output_id.replace("-", " ").title(),
        description=f"Declared {kind.value} output.",
        path_pattern=path,
        persistent=path is not None,
    )


def _completed(
    capability_id: str,
    name: str,
    description: str,
    milestone: str,
    category: Category,
    *,
    requires: tuple[str, ...] = (),
    inputs: tuple[Input, ...] = (),
    outputs: tuple[Output, ...] = (),
    commands: tuple[Command, ...] = (),
    scope: Scope = Scope.REPOSITORY,
    docs: tuple[str, ...] = (),
    limitations: tuple[str, ...] = (),
) -> CapabilityDefinition:
    return CapabilityDefinition(
        capability_id=capability_id,
        display_name=name,
        description=description,
        capability_version="1.0",
        forge_version="0.2",
        phase="1",
        milestone=milestone,
        category=category,
        lifecycle=Lifecycle.AVAILABLE,
        maturity=Maturity.STABLE,
        implementation_status=Implementation.IMPLEMENTED,
        supported_project_types=ALL_PROJECT_TYPES,
        required_capabilities=requires,
        required_inputs=inputs,
        produced_outputs=outputs,
        cli_commands=commands,
        access_mode=Access.FORGE_INTERNAL_WRITE,
        approval_policy=Approval.NONE,
        availability_scope=scope,
        documentation_paths=("README.md", "docs/ARCHITECTURE.md", *docs),
        limitations=limitations,
        tags=("phase-1",),
    )


def _planned(
    capability_id: str,
    name: str,
    milestone: str,
    category: Category,
    *,
    requires: tuple[str, ...] = (),
    access: Access = Access.READ_ONLY,
    approval: Approval = Approval.NONE,
) -> CapabilityDefinition:
    phase = milestone.split(".")[0]
    forge_version = {
        "1": "0.2",
        "2": "0.3",
        "3": "0.4",
        "4": "0.5",
        "5": "0.6",
        "6": "0.7",
    }[phase]
    return CapabilityDefinition(
        capability_id=capability_id,
        display_name=name,
        description=f"Planned Forge capability: {name}.",
        capability_version="1.0",
        forge_version=forge_version,
        phase=phase,
        milestone=milestone,
        category=category,
        lifecycle=Lifecycle.PLANNED,
        maturity=Maturity.EXPERIMENTAL,
        implementation_status=Implementation.NOT_IMPLEMENTED,
        supported_project_types=ALL_PROJECT_TYPES,
        required_capabilities=requires,
        access_mode=access,
        approval_policy=approval,
        availability_scope=Scope.GLOBAL,
        documentation_paths=("docs/CAPABILITIES.md",),
        limitations=("Not implemented.",),
        tags=("roadmap",),
    )


def built_in_catalogue() -> tuple[CapabilityDefinition, ...]:
    """Return a fresh, deterministically sorted catalogue."""
    completed = (
        _completed(
            "workspace-management",
            "Workspace Management",
            "Registers, resolves, and activates project workspaces.",
            "1.1",
            Category.WORKSPACE,
            inputs=(_input("repository-path", InputType.REPOSITORY_PATH),),
            outputs=(
                _output("workspace-state", OutputType.WORKSPACE_STATE, "memory/workspaces.json"),
                _output("workspace-cli", OutputType.CLI_OUTPUT),
            ),
            commands=(
                Command(
                    command="forge workspace",
                    description="Manage workspaces.",
                    primary=True,
                    requires_target=False,
                ),
            ),
            scope=Scope.GLOBAL,
        ),
        _completed(
            "repository-discovery",
            "Repository Discovery",
            "Detects repository structure and technology metadata.",
            "1.2",
            Category.DISCOVERY,
            requires=("workspace-management",),
            inputs=(
                _input("repository-path", InputType.REPOSITORY_PATH),
                _input(
                    "workspace-state",
                    InputType.WORKSPACE_STATE,
                    required=False,
                    producer="workspace-management",
                ),
            ),
            outputs=(
                _output("discovery-state", OutputType.DISCOVERY_STATE, "memory/discovery.json"),
                _output("project-report", OutputType.JSON_REPORT, "reports/latest/PROJECT.json"),
                _output(
                    "technology-report", OutputType.JSON_REPORT, "reports/latest/TECH_STACK.json"
                ),
            ),
            commands=(
                Command(
                    command="forge inspect",
                    description="Inspect a repository.",
                    primary=True,
                    requires_target=True,
                ),
            ),
            limitations=("Manifest reads are bounded.", "Ordinary source files are not opened."),
        ),
        _completed(
            "incremental-project-index",
            "Incremental Project Index",
            "Builds a deterministic file-level repository index.",
            "1.3",
            Category.INDEXING,
            requires=("workspace-management", "repository-discovery"),
            inputs=(
                _input("repository-path", InputType.REPOSITORY_PATH),
                _input(
                    "discovery-state",
                    InputType.DISCOVERY_STATE,
                    required=False,
                    producer="repository-discovery",
                ),
            ),
            outputs=(
                _output("index-state", OutputType.INDEX_STATE, "memory/index.json"),
                _output(
                    "index-report", OutputType.JSON_REPORT, "reports/latest/PROJECT_INDEX.json"
                ),
            ),
            commands=(
                Command(
                    command="forge index",
                    description="Build the project index.",
                    primary=True,
                    requires_target=True,
                ),
            ),
            docs=("docs/INDEXING.md",),
            limitations=("File reads and fingerprints are bounded.",),
        ),
        _completed(
            "engineering-knowledge-graph",
            "Engineering Knowledge Graph",
            "Builds conservative structural relationships from persisted discovery "
            "and index state.",
            "1.4",
            Category.KNOWLEDGE,
            requires=("workspace-management", "repository-discovery", "incremental-project-index"),
            inputs=(
                _input(
                    "workspace-state", InputType.WORKSPACE_STATE, producer="workspace-management"
                ),
                _input(
                    "discovery-state", InputType.DISCOVERY_STATE, producer="repository-discovery"
                ),
                _input("index-state", InputType.INDEX_STATE, producer="incremental-project-index"),
            ),
            outputs=(
                _output(
                    "knowledge-graph-state",
                    OutputType.KNOWLEDGE_GRAPH_STATE,
                    "memory/knowledge_graph.json",
                ),
                _output(
                    "knowledge-graph-report",
                    OutputType.JSON_REPORT,
                    "reports/latest/KNOWLEDGE_GRAPH.json",
                ),
            ),
            commands=(
                Command(
                    command="forge graph",
                    description="Build the structural graph.",
                    primary=True,
                    requires_target=True,
                ),
            ),
            docs=("docs/KNOWLEDGE_GRAPH.md",),
            limitations=("Structural only; no AST, import graph, or API extraction.",),
        ),
        _completed(
            "capability-registry",
            "Capability Registry",
            "Declares and evaluates Forge functionality without executing it.",
            "1.5",
            Category.FOUNDATION,
            requires=("workspace-management",),
            inputs=(_input("configuration", InputType.CONFIGURATION),),
            outputs=(
                _output(
                    "capability-state",
                    OutputType.CAPABILITY_REGISTRY_STATE,
                    "memory/capabilities.json",
                ),
                _output(
                    "capability-report", OutputType.JSON_REPORT, "reports/latest/CAPABILITIES.json"
                ),
                _output(
                    "capability-summary",
                    OutputType.MARKDOWN_REPORT,
                    "reports/latest/CAPABILITY_SUMMARY.md",
                ),
            ),
            commands=(
                Command(
                    command="forge capabilities",
                    description="List registered capabilities.",
                    primary=True,
                ),
                Command(command="forge capability", description="Show capability detail."),
            ),
            scope=Scope.GLOBAL,
            docs=("docs/CAPABILITIES.md",),
        ),
    )
    specs = (
        (
            "runtime-configuration",
            "Runtime Configuration",
            "1.6",
            Category.CONFIGURATION,
            Access.READ_ONLY,
            Approval.NONE,
        ),
        (
            "runtime-health-diagnostics",
            "Runtime Health Diagnostics",
            "1.7",
            Category.DIAGNOSTICS,
            Access.READ_ONLY,
            Approval.NONE,
        ),
        (
            "phase-validation-release",
            "Phase Validation Release",
            "1.8",
            Category.VERIFICATION,
            Access.FORGE_INTERNAL_WRITE,
            Approval.NONE,
        ),
        (
            "mission-planning",
            "Mission Planning",
            "2.1",
            Category.PLANNING,
            Access.READ_ONLY,
            Approval.NONE,
        ),
        (
            "task-management",
            "Task Management",
            "2.2",
            Category.PLANNING,
            Access.FORGE_INTERNAL_WRITE,
            Approval.NONE,
        ),
        (
            "impact-decision-engine",
            "Impact Decision Engine",
            "2.3",
            Category.PLANNING,
            Access.READ_ONLY,
            Approval.NONE,
        ),
        (
            "engineering-memory",
            "Engineering Memory",
            "2.4",
            Category.KNOWLEDGE,
            Access.FORGE_INTERNAL_WRITE,
            Approval.NONE,
        ),
        (
            "mission-reporting",
            "Mission Reporting",
            "2.5",
            Category.DOCUMENTATION,
            Access.FORGE_INTERNAL_WRITE,
            Approval.NONE,
        ),
        (
            "execution-controller",
            "Execution Controller",
            "3.1",
            Category.EXECUTION,
            Access.TARGET_MUTATING,
            Approval.ALWAYS_REQUIRED,
        ),
        (
            "safe-change-planning",
            "Safe Change Planning",
            "3.2",
            Category.PLANNING,
            Access.READ_ONLY,
            Approval.NONE,
        ),
        (
            "safe-code-editing",
            "Safe Code Editing",
            "3.3",
            Category.EXECUTION,
            Access.TARGET_MUTATING,
            Approval.REQUIRED_FOR_HIGH_RISK,
        ),
        (
            "build-verification",
            "Build Verification",
            "3.4",
            Category.VERIFICATION,
            Access.EXTERNAL_SIDE_EFFECT,
            Approval.REQUIRED_FOR_HIGH_RISK,
        ),
        (
            "error-recovery",
            "Error Recovery",
            "3.5",
            Category.EXECUTION,
            Access.TARGET_MUTATING,
            Approval.ALWAYS_REQUIRED,
        ),
        (
            "git-review-package",
            "Git Review Package",
            "3.6",
            Category.VERSION_CONTROL,
            Access.TARGET_MUTATING,
            Approval.ALWAYS_REQUIRED,
        ),
        (
            "documentation-generation",
            "Documentation Generation",
            "3.7",
            Category.DOCUMENTATION,
            Access.TARGET_MUTATING,
            Approval.REQUIRED_FOR_HIGH_RISK,
        ),
        (
            "frontend-analysis",
            "Frontend Analysis",
            "4.1",
            Category.FRONTEND_ANALYSIS,
            Access.READ_ONLY,
            Approval.NONE,
        ),
        (
            "backend-analysis",
            "Backend Analysis",
            "4.2",
            Category.BACKEND_ANALYSIS,
            Access.READ_ONLY,
            Approval.NONE,
        ),
        (
            "database-migration-analysis",
            "Database Migration Analysis",
            "4.3",
            Category.DATABASE_ANALYSIS,
            Access.READ_ONLY,
            Approval.NONE,
        ),
        (
            "api-contract-analysis",
            "API Contract Analysis",
            "4.4",
            Category.API_ANALYSIS,
            Access.READ_ONLY,
            Approval.NONE,
        ),
        (
            "erp-module-analysis",
            "ERP Module Analysis",
            "5.1",
            Category.ERP_ANALYSIS,
            Access.READ_ONLY,
            Approval.NONE,
        ),
        (
            "erp-workflow-analysis",
            "ERP Workflow Analysis",
            "5.2",
            Category.ERP_ANALYSIS,
            Access.READ_ONLY,
            Approval.NONE,
        ),
        (
            "erp-knowledge-model",
            "ERP Knowledge Model",
            "5.3",
            Category.ERP_ANALYSIS,
            Access.FORGE_INTERNAL_WRITE,
            Approval.NONE,
        ),
        (
            "erp-mission-execution",
            "ERP Mission Execution",
            "5.4",
            Category.ERP_ANALYSIS,
            Access.TARGET_MUTATING,
            Approval.ALWAYS_REQUIRED,
        ),
        (
            "automated-test-generation",
            "Automated Test Generation",
            "6.1",
            Category.VERIFICATION,
            Access.TARGET_MUTATING,
            Approval.REQUIRED_FOR_HIGH_RISK,
        ),
        (
            "regression-validation",
            "Regression Validation",
            "6.2",
            Category.VERIFICATION,
            Access.EXTERNAL_SIDE_EFFECT,
            Approval.REQUIRED_FOR_HIGH_RISK,
        ),
        (
            "human-approval-workflow",
            "Human Approval Workflow",
            "6.3",
            Category.EXECUTION,
            Access.FORGE_INTERNAL_WRITE,
            Approval.NOT_APPLICABLE,
        ),
    )
    planned = tuple(
        _planned(cid, name, milestone, category, access=access, approval=approval)
        for cid, name, milestone, category, access, approval in specs
    )
    return tuple(sorted((*completed, *planned), key=lambda item: item.capability_id))
