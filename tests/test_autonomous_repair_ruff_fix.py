from pathlib import Path

from forge.autonomous_repair.models import RepairInput, RepairProviderType
from forge.autonomous_repair.policies import AutonomousRepairPolicy
from forge.autonomous_repair.providers.ruff_fix import RuffFixProvider


def test_ruff_fix_uses_isolated_copy(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    original = "import os\n\nprint('ok')\n"
    target.write_text(original, encoding="utf-8")

    repair_input = RepairInput(
        input_id="input-1",
        candidate_id="candidate-1",
        repository_root=str(tmp_path),
        provider=RepairProviderType.RUFF_FIX,
        finding_ids=("f1",),
        target_paths=("sample.py",),
        repository_fingerprint="a" * 64,
        objective="remove unused import",
    )

    proposal = RuffFixProvider().propose(
        tmp_path,
        repair_input,
        AutonomousRepairPolicy(),
    )

    assert proposal.affected_paths == ("sample.py",)
    assert "import os" not in proposal.patches[0].replacement_text
    assert target.read_text(encoding="utf-8") == original