"""Isolated Ruff-fix repair provider."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from forge.autonomous_repair.errors import RepairProposalError
from forge.autonomous_repair.identifiers import (
    patch_identifier,
    proposal_identifier,
)
from forge.autonomous_repair.models import (
    RepairInput,
    RepairPatch,
    RepairPatchOperation,
    RepairProposal,
    RepairProviderType,
)
from forge.autonomous_repair.policies import AutonomousRepairPolicy
from forge.autonomous_repair.providers.base import AutonomousRepairProvider
from forge.safe_code_editing.identifiers import source_fingerprint


class RuffFixProvider(AutonomousRepairProvider):
    """Generate a repair proposal from Ruff --fix in an isolated workspace."""

    provider_type = RepairProviderType.RUFF_FIX

    def supports(self, repair_input: RepairInput) -> bool:
        return repair_input.provider is self.provider_type

    def propose(
        self,
        repository_root: Path,
        repair_input: RepairInput,
        policy: AutonomousRepairPolicy,
    ) -> RepairProposal:
        policy.validate_provider(self.provider_type)
        paths = policy.validate_paths(repair_input.target_paths)
        if len(paths) != 1:
            raise RepairProposalError(
                "ruff_fix v1 requires exactly one target path"
            )

        root = policy.resolve_repository(repository_root)
        source = (root / paths[0]).resolve()
        if not source.is_file():
            raise RepairProposalError(f"target file does not exist: {paths[0]}")

        original = source.read_text(encoding="utf-8-sig")
        with tempfile.TemporaryDirectory(prefix="forge-ruff-fix-") as temp_directory:
            temporary_root = Path(temp_directory)
            temporary_file = temporary_root / source.name
            shutil.copy2(source, temporary_file)

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ruff",
                    "check",
                    "--fix",
                    temporary_file.name,
                ],
                cwd=temporary_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=60,
                shell=False,
                check=False,
            )
            if completed.returncode not in {0, 1}:
                raise RepairProposalError(
                    f"isolated Ruff fix failed: {completed.stderr or completed.stdout}"
                )

            updated = temporary_file.read_text(encoding="utf-8-sig")

        if updated == original:
            raise RepairProposalError(
                f"Ruff produced no bounded change for {paths[0]}"
            )

        fingerprint = source_fingerprint(original)
        patch_payload = {
            "path": paths[0],
            "operation": RepairPatchOperation.REPLACE.value,
            "start": 0,
            "end": len(original),
            "expected": original,
            "replacement": updated,
            "fingerprint": fingerprint,
        }
        patch = RepairPatch(
            patch_id=patch_identifier(patch_payload),
            relative_path=paths[0],
            operation=RepairPatchOperation.REPLACE,
            start_offset=0,
            end_offset=len(original),
            expected_text=original,
            replacement_text=updated,
            source_fingerprint=fingerprint,
        )
        return RepairProposal(
            proposal_id=proposal_identifier(
                {
                    "input_id": repair_input.input_id,
                    "provider": self.provider_type.value,
                    "patch_ids": [patch.patch_id],
                }
            ),
            input_id=repair_input.input_id,
            provider=self.provider_type,
            patches=(patch,),
            affected_paths=(paths[0],),
            risk_notes=(
                "Ruff ran only against an isolated temporary copy.",
                "The real repository remained unchanged during proposal generation.",
            ),
            validation_commands=("ruff", "mypy", "pytest"),
        )