import pytest
from pydantic import ValidationError

from forge.autonomous_repair.models import (
    RepairApproval,
    RepairExecutionRequest,
    RepairInput,
    RepairPatch,
    RepairPatchOperation,
    RepairProposal,
    RepairProviderType,
)


def patch() -> RepairPatch:
    return RepairPatch(
        patch_id="patch-1",
        relative_path="forge/app.py",
        operation=RepairPatchOperation.REPLACE,
        start_offset=0,
        end_offset=3,
        expected_text="old",
        replacement_text="new",
        source_fingerprint="a" * 64,
    )


def proposal() -> RepairProposal:
    item = patch()
    return RepairProposal(
        proposal_id="proposal-1",
        input_id="input-1",
        provider=RepairProviderType.EXACT_PATCH,
        patches=(item,),
        affected_paths=("forge/app.py",),
    )


def test_repair_input_rejects_path_traversal() -> None:
    with pytest.raises(ValidationError):
        RepairInput(
            input_id="input-1",
            candidate_id="candidate-1",
            repository_root=".",
            provider=RepairProviderType.EXACT_PATCH,
            finding_ids=("f1",),
            target_paths=("../secret.py",),
            repository_fingerprint="a" * 64,
            objective="fix",
        )


def test_apply_request_requires_approval() -> None:
    with pytest.raises(ValidationError):
        RepairExecutionRequest(
            request_id="request-1",
            proposal=proposal(),
            repository_root=".",
            repository_fingerprint="a" * 64,
            dry_run=False,
            approval=RepairApproval(),
        )


def test_approved_request_requires_approver_identity() -> None:
    with pytest.raises(ValidationError):
        RepairApproval(approved=True)


def test_models_are_immutable() -> None:
    item = patch()
    with pytest.raises(ValidationError):
        item.start_offset = 2