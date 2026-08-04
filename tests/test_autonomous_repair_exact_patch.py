from pathlib import Path

import pytest

from forge.autonomous_repair.errors import RepairProposalError
from forge.autonomous_repair.models import RepairInput, RepairProviderType
from forge.autonomous_repair.policies import AutonomousRepairPolicy
from forge.autonomous_repair.providers.exact_patch import ExactPatchProvider


def repair_input(root: Path) -> RepairInput:
    return RepairInput(
        input_id="input-1",
        candidate_id="candidate-1",
        repository_root=str(root),
        provider=RepairProviderType.EXACT_PATCH,
        finding_ids=("f1",),
        target_paths=("sample.py",),
        repository_fingerprint="a" * 64,
        objective="replace TODO",
    )


def test_exact_patch_proposal_is_bounded(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_text("# TODO\n", encoding="utf-8")

    proposal = ExactPatchProvider().propose(
        tmp_path,
        repair_input(tmp_path),
        AutonomousRepairPolicy(),
    )

    assert proposal.affected_paths == ("sample.py",)
    assert proposal.patches[0].expected_text == "TODO"
    assert proposal.patches[0].replacement_text == "DONE"
    assert target.read_text(encoding="utf-8") == "# TODO\n"


def test_exact_patch_rejects_missing_marker(tmp_path: Path) -> None:
    (tmp_path / "sample.py").write_text("print('ok')\n", encoding="utf-8")

    with pytest.raises(RepairProposalError):
        ExactPatchProvider().propose(
            tmp_path,
            repair_input(tmp_path),
            AutonomousRepairPolicy(),
        )