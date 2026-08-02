"""Mission-to-task decomposition tests."""

from forge.planning.models import (
    MissionAcceptanceCriterion,
    MissionApprovalLevel,
    MissionApprovalRequirement,
    MissionContextReference,
    MissionObjective,
    MissionPlan,
    MissionPlanningStatus,
    MissionPlanStatistics,
    MissionRequestCategory,
    MissionRiskLevel,
    MissionScopeItem,
    MissionScopeType,
    MissionValidationCategory,
    MissionValidationStrategy,
    MissionWorkstream,
    NormalizedEngineeringRequest,
    PlanningConfidence,
)
from forge.tasks.decomposer import decompose_mission
from forge.tasks.models import (
    TaskDependencyType,
    TaskStatus,
)


def _mission(
    *,
    workstreams: tuple[MissionWorkstream, ...],
) -> MissionPlan:
    return MissionPlan(
        mission_id="mission-1234567890abcdef",
        mission_fingerprint="a" * 64,
        request=NormalizedEngineeringRequest(
            raw_request="Complete Procurement Module",
            normalized_request="complete procurement module",
            primary_action="complete",
            primary_object="procurement module",
            category=MissionRequestCategory.COMPLETE,
            ambiguity=PlanningConfidence.HIGH,
            terms=("complete", "procurement", "module"),
        ),
        target_identity="target-1",
        target_name="ERP",
        workspace_identity="workspace-1",
        source_fingerprints={
            "index": "b" * 64,
            "graph": "c" * 64,
        },
        objective=MissionObjective(
            statement="Complete the Procurement Module.",
        ),
        status=MissionPlanningStatus.READY,
        planning_confidence=PlanningConfidence.HIGH,
        risk_level=MissionRiskLevel.MEDIUM,
        scope=(
            MissionScopeItem(
                scope_id="scope-1",
                scope_type=MissionScopeType.IN_SCOPE,
                statement="Procurement module completion.",
            ),
        ),
        assumptions=(),
        constraints=(),
        prerequisites=(),
        context=(
            MissionContextReference(
                entity_id="module:procurement",
                entity_type="module",
                canonical_name="Procurement",
                relationship_to_request="Requested module.",
                evidence="Persisted graph entity.",
                confidence=PlanningConfidence.HIGH,
            ),
        ),
        affected_areas=(),
        workstreams=workstreams,
        deliverables=(),
        acceptance_criteria=(
            MissionAcceptanceCriterion(
                criterion_id="mission-criterion-1",
                statement="Mission acceptance is satisfied.",
            ),
        ),
        validation_strategy=(
            MissionValidationStrategy(
                strategy_id="mission-validation-1",
                category=MissionValidationCategory.UNIT_TESTING,
                description="Unit tests pass.",
            ),
        ),
        risks=(),
        approvals=(
            MissionApprovalRequirement(
                approval_id="mission-approval-1",
                level=MissionApprovalLevel.REVIEW_REQUIRED,
                reason="Review is required.",
            ),
        ),
        questions=(),
        statistics=MissionPlanStatistics(
            affected_area_count=0,
            workstream_count=len(workstreams),
            assumption_count=0,
            question_count=0,
            blocking_prerequisite_count=0,
        ),
    )


def test_decomposition_creates_parent_and_output_tasks() -> None:
    mission = _mission(
        workstreams=(
            MissionWorkstream(
                workstream_id="workstream-procurement",
                name="Implement Procurement",
                objective="Implement approved procurement behavior.",
                expected_outputs=(
                    "API contract",
                    "Unit tests",
                    "Documentation",
                ),
                completion_criteria=(
                    "Procurement behavior is complete.",
                ),
            ),
        )
    )

    result = decompose_mission(mission)

    assert len(result.tasks) == 4
    assert result.tasks[0].parent_task_id is None
    assert result.tasks[0].title == "Implement Procurement"

    children = result.tasks[1:]
    assert all(
        task.parent_task_id == result.tasks[0].task_id
        for task in children
    )
    assert [task.title for task in children] == [
        "Produce API contract",
        "Produce Documentation",
        "Produce Unit tests",
    ]


def test_decomposition_is_deterministic() -> None:
    workstream = MissionWorkstream(
        workstream_id="workstream-1",
        name="Build Contract",
        objective="Build the approved contract.",
        expected_outputs=("Tests", "API"),
    )
    mission = _mission(workstreams=(workstream,))

    first = decompose_mission(mission)
    second = decompose_mission(mission)

    assert first == second
    assert first.task_set_fingerprint == second.task_set_fingerprint


def test_workstream_dependencies_map_to_parent_tasks() -> None:
    first = MissionWorkstream(
        workstream_id="workstream-a",
        name="Define Contract",
        objective="Define the approved contract.",
        expected_outputs=("Contract",),
    )
    second = MissionWorkstream(
        workstream_id="workstream-b",
        name="Implement Contract",
        objective="Implement the approved contract.",
        expected_outputs=("Implementation",),
        dependencies=("workstream-a",),
    )

    result = decompose_mission(
        _mission(workstreams=(second, first))
    )

    parents = {
        task.workstream_id: task
        for task in result.tasks
        if task.parent_task_id is None
    }

    dependency = parents["workstream-b"].dependencies[0]

    assert dependency.dependency_task_id == parents["workstream-a"].task_id
    assert dependency.dependency_type is TaskDependencyType.REQUIRES
    assert dependency.blocking


def test_risk_approvals_validation_and_context_are_inherited() -> None:
    workstream = MissionWorkstream(
        workstream_id="workstream-1",
        name="Secure API",
        objective="Implement the secure API.",
        expected_outputs=("Secure API",),
        risk_level=MissionRiskLevel.HIGH,
        required_approvals=(
            MissionApprovalLevel.SECURITY_APPROVAL,
        ),
    )

    result = decompose_mission(
        _mission(workstreams=(workstream,))
    )

    assert all(task.risk_level.value == "high" for task in result.tasks)
    assert all(task.approval_requirements for task in result.tasks)
    assert all(task.validation_requirements for task in result.tasks)
    assert all(task.source_references for task in result.tasks)


def test_initial_tasks_are_draft_and_non_executing() -> None:
    result = decompose_mission(
        _mission(
            workstreams=(
                MissionWorkstream(
                    workstream_id="workstream-1",
                    name="Prepare Module",
                    objective="Prepare the module contract.",
                    expected_outputs=("Plan",),
                ),
            )
        )
    )

    assert all(
        task.status is TaskStatus.DRAFT
        for task in result.tasks
    )
