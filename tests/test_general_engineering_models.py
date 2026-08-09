from pathlib import Path

import pytest

from forge.general_engineering.errors import EngineeringContractError
from forge.general_engineering.models import (
    EditOperation,
    EngineeringRequest,
    RepositoryEvidence,
)
from forge.general_engineering.states import (
    EditOperationType,
    EvidenceType,
)


def test_engineering_request_requires_absolute_repository_root(
    tmp_path: Path,
) -> None:
    request = EngineeringRequest(
        request_id="engineering-request-test",
        objective="Add service validation",
        repository_root=str(tmp_path),
        allow_code_changes=True,
    )

    assert request.repository_root == str(tmp_path)


def test_engineering_request_rejects_repository_escape_path(
    tmp_path: Path,
) -> None:
    with pytest.raises(EngineeringContractError):
        EngineeringRequest(
            request_id="engineering-request-test",
            objective="Add validation",
            repository_root=str(tmp_path),
            explicit_target_paths=("../outside.py",),
        )


def test_repository_evidence_requires_rationale() -> None:
    with pytest.raises(EngineeringContractError):
        RepositoryEvidence(
            evidence_id="repository-evidence-test",
            path="src/service.py",
            evidence_type=EvidenceType.FILE,
            relevance=1.0,
            rationale="",
        )


def test_replace_operation_requires_source_fingerprint() -> None:
    with pytest.raises(EngineeringContractError):
        EditOperation(
            operation_id="edit-operation-test",
            operation_type=EditOperationType.REPLACE,
            target_path="src/service.py",
            proposed_content="value = 2\n",
            rationale="Update implementation",
            originating_requirement_id="requirement-1",
        )


def test_create_file_operation_requires_content() -> None:
    with pytest.raises(EngineeringContractError):
        EditOperation(
            operation_id="edit-operation-test",
            operation_type=EditOperationType.CREATE_FILE,
            target_path="src/new_service.py",
            rationale="Create requested service",
            originating_requirement_id="requirement-1",
        )