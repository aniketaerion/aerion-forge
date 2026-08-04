[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Content
    )

    $FullPath = Join-Path $RepositoryRoot $Path
    $Directory = Split-Path $FullPath -Parent
    New-Item -ItemType Directory -Path $Directory -Force | Out-Null

    [System.IO.File]::WriteAllText(
        $FullPath,
        $Content,
        [System.Text.UTF8Encoding]::new($false)
    )

    Write-Host "WROTE $Path" -ForegroundColor Green
}

Write-Utf8NoBom "forge\autonomous_repair\providers\base.py" @'
"""Provider contract for M3.5 Autonomous Repair."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from forge.autonomous_repair.models import (
    RepairInput,
    RepairProposal,
    RepairProviderType,
)
from forge.autonomous_repair.policies import AutonomousRepairPolicy


class AutonomousRepairProvider(ABC):
    """Base contract for bounded repair proposal providers."""

    provider_type: RepairProviderType

    @abstractmethod
    def supports(self, repair_input: RepairInput) -> bool:
        """Return whether this provider supports the input."""

    @abstractmethod
    def propose(
        self,
        repository_root: Path,
        repair_input: RepairInput,
        policy: AutonomousRepairPolicy,
    ) -> RepairProposal:
        """Produce a deterministic bounded repair proposal without mutation."""
'@

Write-Utf8NoBom "forge\autonomous_repair\providers\exact_patch.py" @'
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
'@

Write-Utf8NoBom "forge\autonomous_repair\providers\ruff_fix.py" @'
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
'@

Write-Utf8NoBom "forge\autonomous_repair\providers\__init__.py" @'
"""Built-in autonomous-repair providers."""

from forge.autonomous_repair.providers.base import AutonomousRepairProvider
from forge.autonomous_repair.providers.exact_patch import ExactPatchProvider
from forge.autonomous_repair.providers.ruff_fix import RuffFixProvider

__all__ = [
    "AutonomousRepairProvider",
    "ExactPatchProvider",
    "RuffFixProvider",
]
'@

Write-Utf8NoBom "forge\autonomous_repair\registry.py" @'
"""Deterministic autonomous-repair provider registry."""

from __future__ import annotations

from forge.autonomous_repair.errors import (
    RepairProviderConflictError,
    RepairProviderNotFoundError,
)
from forge.autonomous_repair.models import RepairProviderType
from forge.autonomous_repair.providers import (
    AutonomousRepairProvider,
    ExactPatchProvider,
    RuffFixProvider,
)


class RepairProviderRegistry:
    """Register and resolve bounded repair providers."""

    def __init__(self) -> None:
        self._providers: dict[RepairProviderType, AutonomousRepairProvider] = {}

    def register(self, provider: AutonomousRepairProvider) -> None:
        if provider.provider_type in self._providers:
            raise RepairProviderConflictError(
                f"provider already registered: {provider.provider_type}"
            )
        self._providers[provider.provider_type] = provider

    def get(self, provider_type: RepairProviderType) -> AutonomousRepairProvider:
        try:
            return self._providers[provider_type]
        except KeyError as exc:
            raise RepairProviderNotFoundError(
                f"provider not registered: {provider_type}"
            ) from exc

    def list_provider_types(self) -> tuple[RepairProviderType, ...]:
        return tuple(sorted(self._providers, key=lambda item: item.value))

    @classmethod
    def with_builtins(cls) -> RepairProviderRegistry:
        registry = cls()
        registry.register(ExactPatchProvider())
        registry.register(RuffFixProvider())
        return registry
'@

Write-Utf8NoBom "tests\test_autonomous_repair_registry.py" @'
import pytest

from forge.autonomous_repair.errors import (
    RepairProviderConflictError,
    RepairProviderNotFoundError,
)
from forge.autonomous_repair.models import RepairProviderType
from forge.autonomous_repair.providers import ExactPatchProvider
from forge.autonomous_repair.registry import RepairProviderRegistry


def test_builtin_registry_is_deterministic() -> None:
    registry = RepairProviderRegistry.with_builtins()

    assert registry.list_provider_types() == (
        RepairProviderType.EXACT_PATCH,
        RepairProviderType.RUFF_FIX,
    )


def test_duplicate_provider_is_rejected() -> None:
    registry = RepairProviderRegistry()
    registry.register(ExactPatchProvider())

    with pytest.raises(RepairProviderConflictError):
        registry.register(ExactPatchProvider())


def test_missing_provider_is_rejected() -> None:
    with pytest.raises(RepairProviderNotFoundError):
        RepairProviderRegistry().get(RepairProviderType.RUFF_FIX)
'@

Write-Utf8NoBom "tests\test_autonomous_repair_exact_patch.py" @'
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
'@

Write-Utf8NoBom "tests\test_autonomous_repair_ruff_fix.py" @'
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
'@

Write-Host ""
Write-Host "M3.5 Package 1 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m mypy .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m pytest `
    .\tests\test_autonomous_repair_registry.py `
    .\tests\test_autonomous_repair_exact_patch.py `
    .\tests\test_autonomous_repair_ruff_fix.py `
    -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m pytest -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "M3.5 PACKAGE 1 COMPLETE" -ForegroundColor Green
git status --short
