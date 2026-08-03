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
    completed: tuple[CapabilityDefinition, ...] = (
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
        _completed(
            "runtime-configuration",
            "Runtime Configuration",
            "Resolves typed Forge runtime settings with deterministic provenance.",
            "1.6",
            Category.CONFIGURATION,
            outputs=(
                _output("configuration-state", OutputType.JSON_REPORT, "memory/configuration.json"),
                _output(
                    "configuration-report",
                    OutputType.JSON_REPORT,
                    "reports/latest/CONFIGURATION_EFFECTIVE.json",
                ),
            ),
            commands=(
                Command(
                    command="forge config",
                    description="Inspect and validate runtime configuration.",
                    primary=True,
                ),
            ),
            scope=Scope.GLOBAL,
            docs=("docs/CONFIGURATION.md", "docs/contracts/RUNTIME_CONFIGURATION_CONTRACT.md"),
            limitations=("Configuration is local and requires restart after applicable changes.",),
        ),
        _completed(
            "runtime-health-diagnostics",
            "Runtime Health Diagnostics",
            "Diagnoses local Forge runtime and repository-understanding readiness.",
            "1.7",
            Category.DIAGNOSTICS,
            requires=("runtime-configuration", "capability-registry"),
            inputs=(
                _input("configuration", InputType.CONFIGURATION),
                _input("workspace-state", InputType.WORKSPACE_STATE, required=False),
                _input("discovery-state", InputType.DISCOVERY_STATE, required=False),
                _input("index-state", InputType.INDEX_STATE, required=False),
                _input("knowledge-graph-state", InputType.KNOWLEDGE_GRAPH_STATE, required=False),
            ),
            outputs=(
                _output(
                    "diagnostic-state", OutputType.DIAGNOSTIC_RESULT, "memory/diagnostics.json"
                ),
                _output(
                    "diagnostic-json",
                    OutputType.JSON_REPORT,
                    "reports/latest/DIAGNOSTIC_RESULTS.json",
                ),
                _output(
                    "diagnostic-summary",
                    OutputType.MARKDOWN_REPORT,
                    "reports/latest/DIAGNOSTIC_SUMMARY.md",
                ),
            ),
            commands=(
                Command(
                    command="forge health", description="Diagnose the Forge runtime.", primary=True
                ),
                Command(command="forge diagnose", description="Diagnose target readiness."),
            ),
            scope=Scope.GLOBAL,
            docs=("docs/DIAGNOSTICS.md", "docs/contracts/RUNTIME_DIAGNOSTICS_CONTRACT.md"),
            limitations=("Local, on-demand, read-only diagnosis; no automatic remediation.",),
        ),
        _completed(
            "phase-validation-release",
            "Phase Validation Release",
            "Validates and freezes the Phase 1 Engineering Runtime release contracts.",
            "1.8",
            Category.VERIFICATION,
            requires=(
                "workspace-management",
                "repository-discovery",
                "incremental-project-index",
                "engineering-knowledge-graph",
                "capability-registry",
                "runtime-configuration",
                "runtime-health-diagnostics",
            ),
            inputs=(
                _input("configuration", InputType.CONFIGURATION),
                _input("workspace-state", InputType.WORKSPACE_STATE),
                _input("discovery-state", InputType.DISCOVERY_STATE),
                _input("index-state", InputType.INDEX_STATE),
                _input("knowledge-graph-state", InputType.KNOWLEDGE_GRAPH_STATE),
            ),
            outputs=(
                _output(
                    "phase-release-manifest",
                    OutputType.JSON_REPORT,
                    "reports/latest/PHASE_1_RELEASE_MANIFEST.json",
                ),
                _output(
                    "phase-release-validation",
                    OutputType.MARKDOWN_REPORT,
                    "docs/audits/PHASE_1_RELEASE_VALIDATION.md",
                ),
            ),
            scope=Scope.GLOBAL,
            docs=(
                "docs/audits/PHASE_1_RELEASE_VALIDATION.md",
                "docs/contracts/PHASE_1_ENGINEERING_RUNTIME_CONTRACT.md",
                "docs/releases/AERION_FORGE_V0_2_RELEASE_NOTES.md",
            ),
            limitations=(
                "Produces release evidence only; it does not commit, tag, push, or publish.",
            ),
        ),
        _completed(
            "mission-planning",
            "Mission Planning",
            "Creates deterministic, evidence-grounded mission-level plans without execution.",
            "2.1",
            Category.PLANNING,
            requires=(
                "workspace-management",
                "repository-discovery",
                "incremental-project-index",
                "engineering-knowledge-graph",
                "capability-registry",
                "runtime-configuration",
                "runtime-health-diagnostics",
                "phase-validation-release",
            ),
            inputs=(
                _input("engineering-request", InputType.USER_REQUEST),
                _input("workspace-state", InputType.WORKSPACE_STATE),
                _input("discovery-state", InputType.DISCOVERY_STATE),
                _input("index-state", InputType.INDEX_STATE),
                _input("knowledge-graph-state", InputType.KNOWLEDGE_GRAPH_STATE),
                _input("configuration", InputType.CONFIGURATION),
            ),
            outputs=(
                _output(
                    "mission-plan",
                    OutputType.PLAN,
                    "memory/missions.json",
                ),
                _output(
                    "mission-plan-report",
                    OutputType.JSON_REPORT,
                    "reports/latest/MISSION_PLAN.json",
                ),
                _output(
                    "mission-summary",
                    OutputType.MARKDOWN_REPORT,
                    "reports/latest/MISSION_SUMMARY.md",
                ),
            ),
            commands=(
                Command(
                    command="forge mission plan",
                    description="Create a mission-level plan.",
                    primary=True,
                    requires_target=False,
                ),
            ),
            scope=Scope.GLOBAL,
            docs=(
                "docs/MISSION_PLANNING.md",
                "docs/contracts/MISSION_PLANNING_CONTRACT.md",
            ),
            limitations=(
                "Read-only planning; no source analysis, target execution, or target mutation.",
            ),
        ).model_copy(
            update={
                "forge_version": "0.3",
                "phase": "2",
                "access_mode": Access.READ_ONLY,
                "tags": ("phase-2",),
            }
        ),
        _completed(
            "task-management",
            "Task Management",
            ("Creates deterministic engineering task graphs from persisted mission plans."),
            "2.2",
            Category.PLANNING,
            requires=("mission-planning",),
            inputs=(
                _input(
                    "mission-plan",
                    InputType.UNKNOWN,
                    producer="mission-planning",
                ),
                _input(
                    "configuration",
                    InputType.CONFIGURATION,
                ),
            ),
            outputs=(
                _output(
                    "task-store",
                    OutputType.PLAN,
                    "memory/tasks.json",
                ),
                _output(
                    "task-plan-report",
                    OutputType.JSON_REPORT,
                    "reports/latest/TASK_PLAN.json",
                ),
                _output(
                    "task-summary-report",
                    OutputType.JSON_REPORT,
                    "reports/latest/TASK_SUMMARY.json",
                ),
                _output(
                    "task-changes-report",
                    OutputType.JSON_REPORT,
                    "reports/latest/TASK_CHANGES.json",
                ),
                _output(
                    "task-plan-markdown",
                    OutputType.MARKDOWN_REPORT,
                    "reports/latest/TASK_PLAN.md",
                ),
                _output(
                    "task-summary-markdown",
                    OutputType.MARKDOWN_REPORT,
                    "reports/latest/TASK_SUMMARY.md",
                ),
            ),
            commands=(
                Command(
                    command="forge task build",
                    description=("Build tasks from a persisted mission plan."),
                    primary=True,
                    requires_target=False,
                ),
                Command(
                    command="forge task list",
                    description="List persisted engineering tasks.",
                    requires_target=False,
                ),
                Command(
                    command="forge task show",
                    description="Show one persisted engineering task.",
                    requires_target=False,
                ),
            ),
            scope=Scope.GLOBAL,
            docs=(
                "docs/TASK_MANAGEMENT.md",
                "docs/contracts/TASK_MANAGEMENT_CONTRACT.md",
            ),
            limitations=(
                "No task execution, scheduling, automatic assignment, "
                "source editing, build execution, test execution, "
                "migration, Git mutation, deployment, or autonomous "
                "remediation.",
            ),
        ).model_copy(
            update={
                "forge_version": "0.3",
                "phase": "2",
                "access_mode": Access.FORGE_INTERNAL_WRITE,
                "tags": ("phase-2",),
            }
        ),
        _completed(
            "impact-decision-engine",
            "Impact Decision Engine",
            (
                "Produces deterministic engineering impact assessments "
                "and controlled decision recommendations from persisted "
                "Mission Plans and Task Sets."
            ),
            "2.3",
            Category.PLANNING,
            requires=(
                "mission-planning",
                "task-management",
            ),
            inputs=(
                _input(
                    "mission-plan",
                    InputType.UNKNOWN,
                    producer="mission-planning",
                ),
                _input(
                    "task-set",
                    InputType.UNKNOWN,
                    producer="task-management",
                ),
                _input(
                    "configuration",
                    InputType.CONFIGURATION,
                ),
            ),
            outputs=(
                _output(
                    "impact-decision-store",
                    OutputType.PLAN,
                    "memory/impact-decisions.json",
                ),
                _output(
                    "impact-assessment-report",
                    OutputType.JSON_REPORT,
                    "reports/latest/IMPACT_ASSESSMENT.json",
                ),
                _output(
                    "impact-decision-report",
                    OutputType.JSON_REPORT,
                    "reports/latest/IMPACT_DECISION.json",
                ),
                _output(
                    "impact-evidence-report",
                    OutputType.JSON_REPORT,
                    "reports/latest/IMPACT_EVIDENCE.json",
                ),
                _output(
                    "impact-summary-report",
                    OutputType.MARKDOWN_REPORT,
                    "reports/latest/IMPACT_SUMMARY.md",
                ),
            ),
            commands=(
                Command(
                    command="forge impact assess",
                    description=("Assess a persisted Mission Plan and Task Set."),
                    primary=True,
                    requires_target=False,
                ),
                Command(
                    command="forge impact list",
                    description=("List persisted Impact Decision assessments."),
                    requires_target=False,
                ),
                Command(
                    command="forge impact show",
                    description=("Show one persisted Impact Decision assessment."),
                    requires_target=False,
                ),
            ),
            scope=Scope.GLOBAL,
            docs=(
                "docs/IMPACT_DECISION.md",
                "docs/contracts/IMPACT_DECISION_CONTRACT.md",
            ),
            limitations=(
                "No task execution, source editing, build execution, "
                "test execution, migration, Git mutation, deployment, "
                "approval granting, or autonomous remediation.",
            ),
        ).model_copy(
            update={
                "forge_version": "0.3",
                "phase": "2",
                "access_mode": Access.FORGE_INTERNAL_WRITE,
                "tags": ("phase-2",),
            }
        ),
        _completed(
            "engineering-memory",
            "Engineering Memory",
            (
                "Preserves deterministic engineering lineage across "
                "Mission Plans, Task Sets, and Impact Assessments."
            ),
            "2.4",
            Category.KNOWLEDGE,
            requires=(
                "mission-planning",
                "task-management",
                "impact-decision-engine",
            ),
            inputs=(
                _input(
                    "mission-plan",
                    InputType.UNKNOWN,
                    producer="mission-planning",
                ),
                _input(
                    "task-set",
                    InputType.UNKNOWN,
                    producer="task-management",
                ),
                _input(
                    "impact-assessment",
                    InputType.UNKNOWN,
                    producer="impact-decision-engine",
                ),
                _input(
                    "configuration",
                    InputType.CONFIGURATION,
                ),
            ),
            outputs=(
                _output(
                    "engineering-memory-store",
                    OutputType.PLAN,
                    "memory/engineering-memory.json",
                ),
                _output(
                    "engineering-memory-report",
                    OutputType.JSON_REPORT,
                    "reports/latest/ENGINEERING_MEMORY.json",
                ),
                _output(
                    "engineering-memory-summary",
                    OutputType.JSON_REPORT,
                    "reports/latest/ENGINEERING_MEMORY_SUMMARY.json",
                ),
                _output(
                    "engineering-memory-lineage",
                    OutputType.JSON_REPORT,
                    "reports/latest/ENGINEERING_MEMORY_LINEAGE.json",
                ),
                _output(
                    "engineering-memory-markdown",
                    OutputType.MARKDOWN_REPORT,
                    "reports/latest/ENGINEERING_MEMORY.md",
                ),
            ),
            commands=(
                Command(
                    command="forge memory build",
                    description=(
                        "Build Engineering Memory from persisted "
                        "Mission, Task, and Impact artifacts."
                    ),
                    primary=True,
                    requires_target=False,
                ),
                Command(
                    command="forge memory list",
                    description=("List persisted Engineering Memory records."),
                    requires_target=False,
                ),
                Command(
                    command="forge memory show",
                    description=("Show one persisted Engineering Memory record."),
                    requires_target=False,
                ),
            ),
            scope=Scope.GLOBAL,
            docs=(
                "docs/ENGINEERING_MEMORY.md",
                "docs/contracts/ENGINEERING_MEMORY_CONTRACT.md",
            ),
            limitations=(
                "No semantic search, embeddings, task execution, "
                "source editing, build execution, test execution, "
                "migration, Git mutation, deployment, approval "
                "granting, or autonomous remediation.",
            ),
        ).model_copy(
            update={
                "forge_version": "0.3",
                "phase": "2",
                "access_mode": Access.FORGE_INTERNAL_WRITE,
                "tags": ("phase-2",),
            }
        ),
        _completed(
            "mission-reporting",
            "Mission Reporting",
            (
                "Produces deterministic engineering reports from "
                "Mission Plans, Task Sets, Impact Assessments, and "
                "Engineering Memory."
            ),
            "2.5",
            Category.DOCUMENTATION,
            requires=(
                "mission-planning",
                "task-management",
                "impact-decision-engine",
                "engineering-memory",
            ),
            inputs=(
                _input(
                    "mission-plan",
                    InputType.UNKNOWN,
                    producer="mission-planning",
                ),
                _input(
                    "task-set",
                    InputType.UNKNOWN,
                    producer="task-management",
                ),
                _input(
                    "impact-assessment",
                    InputType.UNKNOWN,
                    producer="impact-decision-engine",
                ),
                _input(
                    "engineering-memory",
                    InputType.UNKNOWN,
                    producer="engineering-memory",
                ),
                _input(
                    "configuration",
                    InputType.CONFIGURATION,
                ),
            ),
            outputs=(
                _output(
                    "mission-report",
                    OutputType.JSON_REPORT,
                    "reports/latest/MISSION_REPORT.json",
                ),
                _output(
                    "mission-report-summary",
                    OutputType.JSON_REPORT,
                    "reports/latest/MISSION_SUMMARY.json",
                ),
                _output(
                    "mission-report-traceability",
                    OutputType.JSON_REPORT,
                    "reports/latest/MISSION_TRACEABILITY.json",
                ),
                _output(
                    "mission-report-risks",
                    OutputType.JSON_REPORT,
                    "reports/latest/MISSION_RISKS.json",
                ),
                _output(
                    "mission-report-markdown",
                    OutputType.MARKDOWN_REPORT,
                    "reports/latest/MISSION_REPORT.md",
                ),
            ),
            commands=(
                Command(
                    command="forge report build",
                    description=(
                        "Build a deterministic Mission Report from persisted engineering artifacts."
                    ),
                    primary=True,
                    requires_target=False,
                ),
                Command(
                    command="forge report show",
                    description=("Show the latest persisted Mission Report."),
                    requires_target=False,
                ),
            ),
            scope=Scope.GLOBAL,
            docs=(
                "docs/MISSION_REPORTING.md",
                "docs/contracts/MISSION_REPORTING_CONTRACT.md",
            ),
            limitations=(
                "No task execution, source editing, build execution, "
                "test execution, migration, Git mutation, deployment, "
                "approval granting, or autonomous remediation.",
            ),
        ).model_copy(
            update={
                "forge_version": "0.3",
                "phase": "2",
                "access_mode": Access.FORGE_INTERNAL_WRITE,
                "tags": ("phase-2",),
            }
        ),
        _completed(
            "execution-controller",
            "Execution Controller",
            (
                "Creates deterministic execution requests and sessions, "
                "enforces explicit approval and state transitions, validates "
                "operation scope, and produces auditable execution evidence."
            ),
            "3.1",
            Category.EXECUTION,
            requires=(
                "mission-planning",
                "task-management",
                "impact-decision-engine",
                "engineering-memory",
                "mission-reporting",
            ),
            inputs=(
                _input(
                    "mission-plan",
                    InputType.UNKNOWN,
                    producer="mission-planning",
                ),
                _input(
                    "task-set",
                    InputType.UNKNOWN,
                    producer="task-management",
                ),
                _input(
                    "impact-assessment",
                    InputType.UNKNOWN,
                    producer="impact-decision-engine",
                ),
                _input(
                    "engineering-memory",
                    InputType.UNKNOWN,
                    producer="engineering-memory",
                ),
                _input(
                    "mission-report",
                    InputType.UNKNOWN,
                    producer="mission-reporting",
                ),
                _input(
                    "configuration",
                    InputType.CONFIGURATION,
                ),
            ),
            outputs=(
                _output(
                    "execution-request",
                    OutputType.PLAN,
                    "memory/execution-request.json",
                ),
                _output(
                    "execution-session",
                    OutputType.PLAN,
                    "memory/execution-session.json",
                ),
                _output(
                    "execution-controller-report",
                    OutputType.JSON_REPORT,
                    "reports/latest/EXECUTION_CONTROLLER.json",
                ),
                _output(
                    "execution-controller-summary",
                    OutputType.JSON_REPORT,
                    "reports/latest/EXECUTION_CONTROLLER_SUMMARY.json",
                ),
                _output(
                    "execution-controller-evidence",
                    OutputType.JSON_REPORT,
                    "reports/latest/EXECUTION_CONTROLLER_EVIDENCE.json",
                ),
                _output(
                    "execution-controller-transitions",
                    OutputType.JSON_REPORT,
                    "reports/latest/EXECUTION_CONTROLLER_TRANSITIONS.json",
                ),
                _output(
                    "execution-controller-markdown",
                    OutputType.MARKDOWN_REPORT,
                    "reports/latest/EXECUTION_CONTROLLER.md",
                ),
            ),
            commands=(
                Command(
                    command="forge execution request",
                    description=("Create a deterministic controlled execution request."),
                    primary=True,
                    requires_target=False,
                ),
                Command(
                    command="forge execution validate",
                    description=("Validate the latest persisted execution request."),
                    requires_target=False,
                ),
                Command(
                    command="forge execution show",
                    description=("Show a persisted execution request or session."),
                    requires_target=False,
                ),
                Command(
                    command="forge execution list",
                    description=("List persisted Execution Controller artifacts."),
                    requires_target=False,
                ),
            ),
            scope=Scope.GLOBAL,
            docs=(
                "docs/execution_controller/ARCHITECTURE.md",
                "docs/execution_controller/SPECIFICATION.md",
                "docs/execution_controller/STATE_MACHINE.md",
                "docs/execution_controller/DATA_MODEL.md",
                "docs/execution_controller/API_CONTRACT.md",
                "docs/execution_controller/ERROR_MODEL.md",
                "docs/execution_controller/TEST_PLAN.md",
                "docs/execution_controller/ACCEPTANCE_CRITERIA.md",
            ),
            limitations=(
                "Tool dispatch is disabled by default. The current milestone "
                "does not autonomously edit source files, execute builds or "
                "tests, mutate Git, deploy software, run migrations, grant "
                "approval, or perform autonomous remediation.",
            ),
        ).model_copy(
            update={
                "forge_version": "0.3",
                "phase": "3",
                "access_mode": Access.FORGE_INTERNAL_WRITE,
                "approval_policy": Approval.ALWAYS_REQUIRED,
                "tags": ("phase-3",),
            }
        ),
    )
    completed = (
        *completed,
        _completed(
            "safe-change-planning",
            "Safe Change Planning",
            (
                "Creates deterministic, read-only Safe Change Plans from "
                "validated engineering lineage; identifies change targets, "
                "orders implementation actions, assesses risk, defines "
                "verification and rollback controls, and produces auditable "
                "planning reports without modifying the target repository."
            ),
            "3.2",
            Category.PLANNING,
            requires=(
                "mission-planning",
                "task-management",
                "impact-decision-engine",
                "engineering-memory",
                "mission-reporting",
            ),
            inputs=(
                _input(
                    "mission-plan",
                    InputType.UNKNOWN,
                    producer="mission-planning",
                ),
                _input(
                    "task-set",
                    InputType.UNKNOWN,
                    producer="task-management",
                ),
                _input(
                    "impact-assessment",
                    InputType.UNKNOWN,
                    producer="impact-decision-engine",
                ),
                _input(
                    "engineering-memory",
                    InputType.UNKNOWN,
                    producer="engineering-memory",
                ),
                _input(
                    "mission-report",
                    InputType.UNKNOWN,
                    producer="mission-reporting",
                ),
                _input(
                    "configuration",
                    InputType.CONFIGURATION,
                ),
            ),
            outputs=(
                _output(
                    "safe-change-request",
                    OutputType.PLAN,
                    "memory/safe-change-request.json",
                ),
                _output(
                    "safe-change-plan",
                    OutputType.PLAN,
                    "memory/safe-change-plan.json",
                ),
                _output(
                    "safe-change-plan-report",
                    OutputType.JSON_REPORT,
                    "reports/latest/SAFE_CHANGE_PLAN.json",
                ),
                _output(
                    "safe-change-summary",
                    OutputType.JSON_REPORT,
                    "reports/latest/SAFE_CHANGE_SUMMARY.json",
                ),
                _output(
                    "safe-change-targets",
                    OutputType.JSON_REPORT,
                    "reports/latest/SAFE_CHANGE_TARGETS.json",
                ),
                _output(
                    "safe-change-risks",
                    OutputType.JSON_REPORT,
                    "reports/latest/SAFE_CHANGE_RISKS.json",
                ),
                _output(
                    "safe-change-verification",
                    OutputType.JSON_REPORT,
                    "reports/latest/SAFE_CHANGE_VERIFICATION.json",
                ),
                _output(
                    "safe-change-rollback",
                    OutputType.JSON_REPORT,
                    "reports/latest/SAFE_CHANGE_ROLLBACK.json",
                ),
                _output(
                    "safe-change-traceability",
                    OutputType.JSON_REPORT,
                    "reports/latest/SAFE_CHANGE_TRACEABILITY.json",
                ),
                _output(
                    "safe-change-markdown",
                    OutputType.MARKDOWN_REPORT,
                    "reports/latest/SAFE_CHANGE_PLAN.md",
                ),
            ),
            commands=(
                Command(
                    command="forge safe-change request",
                    description=("Create and persist a deterministic Safe Change request."),
                    primary=True,
                    requires_target=False,
                ),
                Command(
                    command="forge safe-change validate",
                    description=("Validate the persisted Safe Change request."),
                    requires_target=False,
                ),
                Command(
                    command="forge safe-change show",
                    description=("Show a persisted Safe Change request or plan."),
                    requires_target=False,
                ),
                Command(
                    command="forge safe-change list",
                    description=("List persisted Safe Change Planning artifacts."),
                    requires_target=False,
                ),
                Command(
                    command="forge safe-change render",
                    description=("Render the Safe Change Plan report suite."),
                    requires_target=False,
                ),
            ),
            scope=Scope.GLOBAL,
            docs=(
                "docs/safe_change_planning/ARCHITECTURE.md",
                "docs/safe_change_planning/SPECIFICATION.md",
                "docs/safe_change_planning/DATA_MODEL.md",
                "docs/safe_change_planning/RISK_MODEL.md",
                "docs/safe_change_planning/PLANNING_ALGORITHM.md",
                "docs/safe_change_planning/API_CONTRACT.md",
                "docs/safe_change_planning/TEST_PLAN.md",
                "docs/safe_change_planning/ACCEPTANCE_CRITERIA.md",
            ),
            limitations=(
                "Safe Change Planning is read-only. It does not edit source "
                "files, execute tools, run builds or tests, mutate Git, apply "
                "database migrations, deploy software, or approve execution.",
            ),
        ).model_copy(
            update={
                "forge_version": "0.3",
                "phase": "3",
                "access_mode": Access.READ_ONLY,
                "approval_policy": Approval.NONE,
                "tags": ("phase-3",),
            }
        ),
    )

    specs = (
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
