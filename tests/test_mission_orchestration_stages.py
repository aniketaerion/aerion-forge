from forge.mission_orchestration.models import StageType
from forge.mission_orchestration.stages import builtin_stage_definitions


def test_builtin_stages_are_complete() -> None:
    stages = builtin_stage_definitions()
    types = {stage.stage_type for stage in stages}

    assert StageType.MISSION_VALIDATION in types
    assert StageType.SAFE_EDIT_APPLY in types
    assert StageType.AUTONOMOUS_REPAIR in types
    assert StageType.MISSION_REPORTING in types


def test_apply_and_approval_gate_require_approval() -> None:
    stages = {stage.stage_id: stage for stage in builtin_stage_definitions()}

    assert stages["approval_gate"].approval_required is True
    assert stages["safe_edit_apply"].approval_required is True