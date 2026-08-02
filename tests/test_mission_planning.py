"""Core tests for the Milestone 2.1 Mission Planning Engine."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from forge.cli import app
from forge.planning.context import PlanningContext
from forge.planning.errors import MissionRequestError
from forge.planning.models import (
    MissionContextReference,
    MissionPlanningConfiguration,
    MissionPlanningStatus,
    MissionPrerequisite,
    MissionPrerequisiteStatus,
    MissionRequestCategory,
    MissionRiskLevel,
    NormalizedEngineeringRequest,
    PlanningConfidence,
)
from forge.planning.normalizer import normalize_request
from forge.planning.planner import _prerequisites, _readiness
from forge.planning.service import MissionPlanningService

runner = CliRunner()


def _prepare_empty_memory(root: Path) -> tuple[Path, Path]:
    memory = root / "memory"
    reports = root / "reports" / "latest"

    memory.mkdir(parents=True)
    reports.mkdir(parents=True)

    (memory / "workspaces.json").write_text(
        '{"workspaces": {}}\n',
        encoding="utf-8",
    )

    return memory, reports


@pytest.mark.parametrize(
    ("request_text", "category", "action", "object_name"),
    (
        (
            "Complete Procurement Module",
            MissionRequestCategory.COMPLETE,
            "complete",
            "procurement module",
        ),
        (
            "Implement supplier onboarding",
            MissionRequestCategory.IMPLEMENT,
            "implement",
            "supplier onboarding",
        ),
        (
            "Fix inventory reservation defect",
            MissionRequestCategory.FIX,
            "fix",
            "inventory reservation defect",
        ),
        (
            "Document the current architecture",
            MissionRequestCategory.DOCUMENT,
            "document",
            "the current architecture",
        ),
        (
            "Migrate the database schema",
            MissionRequestCategory.MIGRATE,
            "migrate",
            "the database schema",
        ),
    ),
)
def test_request_normalization(
    request_text: str,
    category: MissionRequestCategory,
    action: str,
    object_name: str,
) -> None:
    normalized = normalize_request(request_text)

    assert normalized.category is category
    assert normalized.primary_action == action
    assert normalized.primary_object == object_name
    assert normalized.normalized_request == request_text.casefold()
    assert normalized.terms


def test_request_normalization_is_deterministic() -> None:
    first = normalize_request(
        "  Complete   Procurement Module! "
    )
    second = normalize_request(
        "complete procurement module"
    )

    assert first.normalized_request == second.normalized_request
    assert first.primary_action == second.primary_action
    assert first.primary_object == second.primary_object
    assert first.category is second.category
    assert first.terms == second.terms


@pytest.mark.parametrize("request_text", ("", " ", "\n\t"))
def test_empty_request_is_rejected(request_text: str) -> None:
    with pytest.raises(MissionRequestError):
        normalize_request(request_text)


def test_blocked_plan_without_phase1_state(
    tmp_path: Path,
) -> None:
    memory, reports = _prepare_empty_memory(tmp_path)

    service = MissionPlanningService(
        memory_path=memory,
        reports_path=reports,
        configuration=MissionPlanningConfiguration(),
    )

    result = service.plan(
        "Document the current architecture",
        target=str(tmp_path),
        persist=False,
        cwd=tmp_path,
    )

    assert result.plan.status is MissionPlanningStatus.BLOCKED
    assert result.plan.risk_level is MissionRiskLevel.LOW
    assert (
        result.plan.planning_confidence.value
        == "insufficient"
    )
    assert result.plan.statistics.blocking_prerequisite_count == 4
    assert result.report_paths == ()
    assert not (memory / "missions.json").exists()
    assert not tuple(reports.glob("MISSION_*"))


def test_blocked_plan_contains_safe_corrective_actions(
    tmp_path: Path,
) -> None:
    memory, reports = _prepare_empty_memory(tmp_path)

    service = MissionPlanningService(
        memory_path=memory,
        reports_path=reports,
    )

    result = service.plan(
        "Document the current architecture",
        target=str(tmp_path),
        persist=False,
        cwd=tmp_path,
    )

    prerequisites = {
        item.prerequisite_id: item
        for item in result.plan.prerequisites
    }

    assert prerequisites["target_resolved"].status.value == "satisfied"
    assert prerequisites["discovery_present"].blocking
    assert prerequisites["index_present"].blocking
    assert prerequisites["knowledge_graph_current"].blocking
    assert prerequisites["required_capabilities_available"].blocking

    assert (
        prerequisites["discovery_present"].corrective_action
        is not None
    )
    assert (
        prerequisites["index_present"].corrective_action
        is not None
    )
    assert (
        prerequisites["knowledge_graph_current"].corrective_action
        is not None
    )


def test_no_persist_is_deterministic(
    tmp_path: Path,
) -> None:
    memory, reports = _prepare_empty_memory(tmp_path)

    service = MissionPlanningService(
        memory_path=memory,
        reports_path=reports,
    )

    first = service.plan(
        "Document the current architecture",
        target=str(tmp_path),
        persist=False,
        cwd=tmp_path,
    )
    second = service.plan(
        "Document the current architecture",
        target=str(tmp_path),
        persist=False,
        cwd=tmp_path,
    )
    third = service.plan(
        "Document the current architecture",
        target=str(tmp_path),
        persist=False,
        cwd=tmp_path,
    )

    assert first.plan.mission_id == second.plan.mission_id
    assert second.plan.mission_id == third.plan.mission_id

    assert (
        first.plan.mission_fingerprint
        == second.plan.mission_fingerprint
        == third.plan.mission_fingerprint
    )

    assert (
        first.generation.generation_id
        == second.generation.generation_id
        == third.generation.generation_id
    )


def test_milestone_boundaries_are_explicit(
    tmp_path: Path,
) -> None:
    memory, reports = _prepare_empty_memory(tmp_path)

    service = MissionPlanningService(
        memory_path=memory,
        reports_path=reports,
    )

    result = service.plan(
        "Complete Procurement Module",
        target=str(tmp_path),
        persist=False,
        cwd=tmp_path,
    )

    exclusions = {
        item.statement
        for item in result.plan.scope
        if item.scope_type.value == "out_of_scope"
    }

    assert "source-code modification" in exclusions
    assert "patch generation" in exclusions
    assert "target build execution" in exclusions
    assert "target test execution" in exclusions
    assert "database migration execution" in exclusions
    assert "Git mutation" in exclusions
    assert "deployment" in exclusions
    assert "automatic remediation" in exclusions


def test_high_risk_request_requires_approval(
    tmp_path: Path,
) -> None:
    memory, reports = _prepare_empty_memory(tmp_path)

    service = MissionPlanningService(
        memory_path=memory,
        reports_path=reports,
    )

    result = service.plan(
        "Migrate the database schema",
        target=str(tmp_path),
        persist=False,
        cwd=tmp_path,
    )

    approval_levels = {
        item.level.value
        for item in result.plan.approvals
    }

    assert result.plan.risk_level is MissionRiskLevel.HIGH
    assert "data_migration_approval" in approval_levels
    assert "high_risk_approval" in approval_levels
    assert "review_required" in approval_levels


def test_cli_help_exposes_planning_contract() -> None:
    result = runner.invoke(
        app,
        ["mission", "plan", "--help"],
    )

    assert result.exit_code == 0

    for option in (
        "--target",
        "--json",
        "--summary",
        "--context",
        "--risks",
        "--assumptions",
        "--questions",
        "--strict",
        "--no-persist",
    ):
        assert option in result.stdout


def test_cli_blocked_status_returns_four(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    memory, reports = _prepare_empty_memory(tmp_path)

    monkeypatch.chdir(tmp_path)

    monkeypatch.setenv(
        "FORGE_MEMORY_PATH",
        str(memory),
    )
    monkeypatch.setenv(
        "FORGE_REPORTS_PATH",
        str(reports),
    )

    result = runner.invoke(
        app,
        [
            "mission",
            "plan",
            "Document the current architecture",
            "--target",
            ".",
            "--no-persist",
            "--json",
        ],
    )

    assert result.exit_code == 4

    payload = json.loads(result.stdout)

    assert payload["plan"]["status"] == "blocked"
    assert payload["plan"]["risk_level"] == "low"
    assert payload["report_paths"] == []
    assert not (memory / "missions.json").exists()


def _request_with_confidence(
    confidence: PlanningConfidence,
) -> NormalizedEngineeringRequest:
    return NormalizedEngineeringRequest(
        raw_request="Complete Procurement Module",
        normalized_request="complete procurement module",
        primary_action="complete",
        primary_object="procurement module",
        category=MissionRequestCategory.COMPLETE,
        ambiguity=confidence,
        terms=("complete", "procurement", "module"),
    )


def _planning_context(
    *,
    diagnostic_status: str = "healthy",
    diagnostic_target_matches: bool = True,
    graph_is_current: bool = True,
    unavailable_capabilities: tuple[str, ...] = (),
) -> PlanningContext:
    evidence = object()

    return PlanningContext.model_construct(
        target_identity="target-identity",
        target_name="ERP",
        workspace_identity="workspace-identity",
        discovery=evidence,
        project_index=evidence,
        graph=evidence,
        graph_is_current=graph_is_current,
        graph_staleness_reason=(
            None
            if graph_is_current
            else "Knowledge graph was built from an older index."
        ),
        diagnostic_status=diagnostic_status,
        diagnostic_fingerprint="diagnostic-fingerprint",
        diagnostic_target_matches=diagnostic_target_matches,
        capability_fingerprint="capability-fingerprint",
        configuration_fingerprint="configuration-fingerprint",
        unavailable_capabilities=unavailable_capabilities,
    )


def _satisfied_prerequisites() -> tuple[MissionPrerequisite, ...]:
    return (
        MissionPrerequisite(
            prerequisite_id="fixture-ready",
            description="Synthetic ready prerequisite.",
            status=MissionPrerequisiteStatus.SATISFIED,
            blocking=True,
            evidence="Synthetic prerequisite is satisfied.",
        ),
    )


def _context_reference() -> tuple[MissionContextReference, ...]:
    return (
        MissionContextReference(
            entity_id="module:procurement",
            entity_type="module",
            canonical_name="Procurement",
            relationship_to_request="Matches the requested module.",
            evidence="Persisted structural evidence.",
            confidence=PlanningConfidence.HIGH,
        ),
    )


def test_readiness_returns_ready_for_complete_healthy_evidence() -> None:
    status, confidence, blocking = _readiness(
        _request_with_confidence(PlanningConfidence.HIGH),
        _planning_context(),
        _context_reference(),
        _satisfied_prerequisites(),
        MissionPlanningConfiguration(),
    )

    assert status is MissionPlanningStatus.READY
    assert confidence is PlanningConfidence.HIGH
    assert blocking == 0


def test_readiness_returns_ready_with_conditions_for_degraded_runtime() -> None:
    status, confidence, blocking = _readiness(
        _request_with_confidence(PlanningConfidence.HIGH),
        _planning_context(diagnostic_status="degraded"),
        _context_reference(),
        _satisfied_prerequisites(),
        MissionPlanningConfiguration(
            allow_degraded_runtime=True,
        ),
    )

    assert status is MissionPlanningStatus.READY_WITH_CONDITIONS
    assert confidence is PlanningConfidence.MEDIUM
    assert blocking == 0


def test_stale_graph_is_a_blocking_prerequisite() -> None:
    prerequisites = _prerequisites(
        _planning_context(graph_is_current=False),
        MissionPlanningConfiguration(
            require_current_graph=True,
        ),
    )

    graph = next(
        item
        for item in prerequisites
        if item.prerequisite_id == "knowledge_graph_current"
    )

    assert graph.status is MissionPrerequisiteStatus.UNSATISFIED
    assert graph.blocking
    assert graph.corrective_action == "Run forge graph ERP"
    assert "older index" in graph.evidence


def test_diagnostic_target_mismatch_blocks_strict_planning() -> None:
    prerequisites = _prerequisites(
        _planning_context(
            diagnostic_target_matches=False,
        ),
        MissionPlanningConfiguration(
            strict=True,
        ),
    )

    diagnostic = next(
        item
        for item in prerequisites
        if item.prerequisite_id == "diagnostic_target_matches"
    )

    assert diagnostic.status is MissionPrerequisiteStatus.UNSATISFIED
    assert diagnostic.blocking
    assert diagnostic.corrective_action == "Run forge diagnose ERP"

