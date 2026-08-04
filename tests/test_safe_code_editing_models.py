import pytest
from pydantic import ValidationError

from forge.safe_code_editing.models import (
    EditOperation,
    EditOperationType,
    FileEditPlan,
    SafeEditRequest,
)


def operation(**overrides: object) -> EditOperation:
    values: dict[str, object] = {
        "operation_id": "editop_1",
        "operation_type": EditOperationType.REPLACE,
        "relative_path": "forge/app.py",
        "start_offset": 0,
        "end_offset": 3,
        "expected_text": "old",
        "replacement_text": "new",
        "source_fingerprint": "a" * 64,
    }
    values.update(overrides)
    return EditOperation.model_validate(values)


def test_models_are_immutable() -> None:
    item = operation()
    with pytest.raises(ValidationError):
        item.start_offset = 2 


def test_insert_requires_equal_offsets() -> None:
    with pytest.raises(ValidationError):
        operation(
            operation_type=EditOperationType.INSERT,
            start_offset=1,
            end_offset=2,
            expected_text="",
        )


def test_delete_requires_empty_replacement() -> None:
    with pytest.raises(ValidationError):
        operation(
            operation_type=EditOperationType.DELETE,
            replacement_text="not-empty",
        )


def test_relative_path_rejects_traversal() -> None:
    with pytest.raises(ValidationError):
        operation(relative_path="../secret.py")


def test_request_requires_approval_for_apply() -> None:
    item = operation()
    plan = FileEditPlan(
        relative_path="forge/app.py",
        source_fingerprint="a" * 64,
        operations=(item,),
    )
    with pytest.raises(ValidationError):
        SafeEditRequest(
            request_id="editreq_1",
            change_plan_id="plan_1",
            repository_root=".",
            file_plans=(plan,),
            dry_run=False,
            approved=False,
        )