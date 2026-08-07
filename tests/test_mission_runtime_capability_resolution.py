from forge.capabilities.models import (
    CapabilityAccessMode,
    CapabilityApprovalPolicy,
    CapabilityAvailabilityScope,
    CapabilityCategory,
    CapabilityDefinition,
    CapabilityEvaluation,
    CapabilityImplementationStatus,
    CapabilityLifecycle,
    CapabilityMaturity,
    CapabilityRegistry,
    CapabilityRegistryGeneration,
    CapabilityRegistryStatistics,
)
from forge.capabilities.query import CapabilityRegistryQuery
from forge.mission_runtime.capability_resolution import (
    MissionCapabilityResolver,
)
from forge.mission_runtime.context import MissionTechnologyContext
from forge.workspace.models import ProjectType


def statistics(
    *,
    total: int,
    available: int,
    implemented: int,
) -> CapabilityRegistryStatistics:
    return CapabilityRegistryStatistics(
        total_capabilities=total,
        available_capabilities=available,
        planned_capabilities=0,
        implemented_capabilities=implemented,
        partially_available_capabilities=0,
        disabled_capabilities=0,
        deprecated_capabilities=0,
        removed_capabilities=0,
        read_only_capabilities=total,
        forge_internal_write_capabilities=0,
        target_mutating_capabilities=0,
        external_side_effect_capabilities=0,
        capabilities_by_category={},
        capabilities_by_maturity={},
        capabilities_by_phase={},
        capabilities_by_milestone={},
    )


def definition(
    capability_id: str,
    *,
    project_types: tuple[str, ...],
) -> CapabilityDefinition:
    return CapabilityDefinition(
        capability_id=capability_id,
        display_name=capability_id,
        description="Test capability.",
        capability_version="1.0",
        forge_version="1.0",
        phase="5",
        milestone="5.8",
        category=CapabilityCategory.INTEGRATION,
        lifecycle=CapabilityLifecycle.AVAILABLE,
        maturity=CapabilityMaturity.STABLE,
        implementation_status=(
            CapabilityImplementationStatus.IMPLEMENTED
        ),
        supported_project_types=project_types,
        access_mode=CapabilityAccessMode.READ_ONLY,
        approval_policy=CapabilityApprovalPolicy.NONE,
        availability_scope=(
            CapabilityAvailabilityScope.PROJECT_TYPE
        ),
    )


def query() -> CapabilityRegistryQuery:
    definitions = (
        definition(
            "erp-capability",
            project_types=("ERP",),
        ),
        definition(
            "flutter-capability",
            project_types=("Flutter",),
        ),
    )

    evaluations = tuple(
        CapabilityEvaluation(
            capability_id=item.capability_id,
            lifecycle=item.lifecycle,
            implementation_status=item.implementation_status,
            available=True,
        )
        for item in definitions
    )

    registry = CapabilityRegistry(
        registry_id="test-registry",
        schema_version="1.0",
        definitions=definitions,
        evaluations=evaluations,
        statistics=statistics(
            total=2,
            available=2,
            implemented=2,
        ),
        generation=CapabilityRegistryGeneration(
            generation_id="test-generation",
            registry_fingerprint="test-fingerprint",
        ),
    )

    return CapabilityRegistryQuery(registry)


def test_resolver_selects_project_capability() -> None:
    selection = MissionCapabilityResolver(
        query()
    ).resolve(
        MissionTechnologyContext(
            project_type=ProjectType.ERP,
            technologies=("React", "Node"),
        )
    )

    assert selection.capability_ids == (
        "erp-capability",
    )