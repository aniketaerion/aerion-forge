"""Canonical static diagnostic definitions."""

from forge.diagnostics.models import (
    DiagnosticCategory as C,
)
from forge.diagnostics.models import (
    DiagnosticCriticality as K,
)
from forge.diagnostics.models import (
    DiagnosticDefinition,
)
from forge.diagnostics.models import (
    DiagnosticScope as S,
)


def _d(
    check_id: str,
    category: C,
    scope: S,
    criticality: K = K.REQUIRED,
    *,
    prerequisites: tuple[str, ...] = (),
    target: bool = False,
    capabilities: tuple[str, ...] = (),
    configuration: tuple[str, ...] = (),
) -> DiagnosticDefinition:
    name = check_id.replace("-", " ").title()
    return DiagnosticDefinition(
        check_id=check_id,
        display_name=name,
        description=f"Verify {name.lower()}.",
        category=category,
        scope=scope,
        criticality=criticality,
        prerequisite_checks=prerequisites,
        target_required=target,
        required_capabilities=capabilities,
        required_configuration_keys=configuration,
        tags=(category.value, scope.value),
    )


def diagnostic_definitions() -> tuple[DiagnosticDefinition, ...]:
    values = (
        _d("runtime-python-version", C.CORE, S.RUNTIME),
        _d("runtime-forge-root", C.CORE, S.RUNTIME),
        _d("runtime-core-imports", C.CORE, S.RUNTIME),
        _d(
            "configuration-valid", C.CONFIGURATION, S.CONFIGURATION, configuration=("core.profile",)
        ),
        _d("configuration-store-readable", C.CONFIGURATION, S.PERSISTENCE),
        _d(
            "configuration-store-schema",
            C.CONFIGURATION,
            S.PERSISTENCE,
            prerequisites=("configuration-store-readable",),
        ),
        _d(
            "persistence-memory-directory",
            C.PERSISTENCE,
            S.PERSISTENCE,
            configuration=("persistence.memory_directory",),
        ),
        _d(
            "reporting-output-directory",
            C.REPORTING,
            S.REPORTING,
            configuration=("reporting.output_directory",),
        ),
        _d("capability-registry-readable", C.CAPABILITIES, S.CAPABILITY),
        _d(
            "capability-registry-valid",
            C.CAPABILITIES,
            S.CAPABILITY,
            prerequisites=("capability-registry-readable",),
        ),
        _d(
            "capability-dependencies-satisfied",
            C.CAPABILITIES,
            S.CAPABILITY,
            prerequisites=("capability-registry-valid",),
        ),
        _d("workspace-store-readable", C.WORKSPACE, S.PERSISTENCE),
        _d("repository-artifacts-excluded", C.COMPATIBILITY, S.INTEGRATION),
        _d("security-sensitive-redaction", C.SECURITY, S.SECURITY),
        _d("target-resolvable", C.WORKSPACE, S.REPOSITORY, target=True),
        _d(
            "workspace-target-valid",
            C.WORKSPACE,
            S.WORKSPACE,
            prerequisites=("target-resolvable",),
            target=True,
        ),
        _d(
            "workspace-project-type-supported",
            C.WORKSPACE,
            S.WORKSPACE,
            prerequisites=("workspace-target-valid",),
            target=True,
        ),
        _d(
            "discovery-state-present",
            C.DISCOVERY,
            S.REPOSITORY,
            K.RECOMMENDED,
            prerequisites=("target-resolvable",),
            target=True,
        ),
        _d(
            "discovery-state-readable",
            C.DISCOVERY,
            S.PERSISTENCE,
            prerequisites=("discovery-state-present",),
            target=True,
        ),
        _d(
            "discovery-state-current",
            C.DISCOVERY,
            S.REPOSITORY,
            K.RECOMMENDED,
            prerequisites=("discovery-state-readable",),
            target=True,
        ),
        _d(
            "index-state-present",
            C.INDEXING,
            S.REPOSITORY,
            K.RECOMMENDED,
            prerequisites=("target-resolvable",),
            target=True,
        ),
        _d(
            "index-state-readable",
            C.INDEXING,
            S.PERSISTENCE,
            prerequisites=("index-state-present",),
            target=True,
        ),
        _d(
            "index-state-consistent",
            C.INDEXING,
            S.REPOSITORY,
            prerequisites=("index-state-readable",),
            target=True,
        ),
        _d(
            "knowledge-graph-state-present",
            C.KNOWLEDGE_GRAPH,
            S.REPOSITORY,
            K.RECOMMENDED,
            prerequisites=("target-resolvable",),
            target=True,
        ),
        _d(
            "knowledge-graph-state-readable",
            C.KNOWLEDGE_GRAPH,
            S.PERSISTENCE,
            prerequisites=("knowledge-graph-state-present",),
            target=True,
        ),
        _d(
            "knowledge-graph-state-valid",
            C.KNOWLEDGE_GRAPH,
            S.REPOSITORY,
            prerequisites=("knowledge-graph-state-readable",),
            target=True,
        ),
        _d(
            "knowledge-graph-state-current",
            C.KNOWLEDGE_GRAPH,
            S.REPOSITORY,
            K.RECOMMENDED,
            prerequisites=("knowledge-graph-state-readable", "index-state-readable"),
            target=True,
        ),
        _d(
            "discovery-index-consistent",
            C.CONSISTENCY,
            S.INTEGRATION,
            prerequisites=("discovery-state-readable", "index-state-readable"),
            target=True,
        ),
        _d(
            "index-graph-consistent",
            C.CONSISTENCY,
            S.INTEGRATION,
            prerequisites=("index-state-readable", "knowledge-graph-state-readable"),
            target=True,
        ),
        _d(
            "target-required-capabilities",
            C.CAPABILITIES,
            S.CAPABILITY,
            prerequisites=("target-resolvable",),
            target=True,
            capabilities=(
                "workspace-management",
                "repository-discovery",
                "incremental-project-index",
                "engineering-knowledge-graph",
                "capability-registry",
                "runtime-configuration",
                "runtime-health-diagnostics",
            ),
        ),
    )
    return tuple(sorted(values, key=lambda item: item.check_id))
