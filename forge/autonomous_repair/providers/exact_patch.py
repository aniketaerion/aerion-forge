"""Exact-patch repair provider."""

from __future__ import annotations

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


class ExactPatchProvider(AutonomousRepairProvider):
    """Build one exact replacement patch from deterministic input metadata."""

    provider_type = RepairProviderType.EXACT_PATCH

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
                "exact patch v1 requires exactly one target path"
            )

        root = policy.resolve_repository(repository_root)
        target = (root / paths[0]).resolve()
        if not target.is_file():
            raise RepairProposalError(f"target file does not exist: {paths[0]}")

        content = target.read_text(encoding="utf-8-sig")
        marker = "TODO"
        replacement = "DONE"
        start = content.find(marker)
        if start < 0:
            raise RepairProposalError(
                f"exact patch marker not found in {paths[0]}: {marker}"
            )
        end = start + len(marker)
        fingerprint = source_fingerprint(content)
        patch_payload = {
            "path": paths[0],
            "operation": RepairPatchOperation.REPLACE.value,
            "start": start,
            "end": end,
            "expected": marker,
            "replacement": replacement,
            "fingerprint": fingerprint,
        }
        patch = RepairPatch(
            patch_id=patch_identifier(patch_payload),
            relative_path=paths[0],
            operation=RepairPatchOperation.REPLACE,
            start_offset=start,
            end_offset=end,
            expected_text=marker,
            replacement_text=replacement,
            source_fingerprint=fingerprint,
        )
        proposal_payload = {
            "input_id": repair_input.input_id,
            "provider": self.provider_type.value,
            "patch_ids": [patch.patch_id],
        }
        return RepairProposal(
            proposal_id=proposal_identifier(proposal_payload),
            input_id=repair_input.input_id,
            provider=self.provider_type,
            patches=(patch,),
            affected_paths=(paths[0],),
            risk_notes=(
                "Exact replacement of the first TODO marker only.",
                "No repository files were modified during proposal generation.",
            ),
            validation_commands=("ruff", "mypy", "pytest"),
        )