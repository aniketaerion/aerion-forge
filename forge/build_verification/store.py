"""Persistence for M3.7 Build Verification."""

from __future__ import annotations

import json
from pathlib import Path

from forge.build_verification.errors import (
    BuildVerificationNotFoundError,
    BuildVerificationPersistenceError,
)
from forge.build_verification.models import (
    BuildVerificationEvidence,
    ReleaseGateDecision,
)


class BuildVerificationStore:
    """Persist verification evidence and release decisions atomically."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def _evidence_path(self, evidence_id: str) -> Path:
        return self.root / "evidence" / f"{evidence_id}.json"

    def _decision_path(self, decision_id: str) -> Path:
        return self.root / "decisions" / f"{decision_id}.json"

    @staticmethod
    def _write_json(path: Path, payload: dict[str, object]) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(path.suffix + ".tmp")
            temporary.write_text(
                json.dumps(payload, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            temporary.replace(path)
        except OSError as exc:
            raise BuildVerificationPersistenceError(
                f"unable to persist build verification artifact: {path}"
            ) from exc

    def save_evidence(
        self,
        evidence: BuildVerificationEvidence,
    ) -> Path:
        """Persist one verification evidence document."""
        path = self._evidence_path(evidence.evidence_id)
        self._write_json(path, evidence.model_dump(mode="json"))
        return path

    def save_decision(
        self,
        decision: ReleaseGateDecision,
    ) -> Path:
        """Persist one release-gate decision document."""
        path = self._decision_path(decision.decision_id)
        self._write_json(path, decision.model_dump(mode="json"))
        return path

    def load_evidence(
        self,
        evidence_id: str,
    ) -> BuildVerificationEvidence:
        """Load one persisted verification evidence document."""
        path = self._evidence_path(evidence_id)

        if not path.is_file():
            raise BuildVerificationNotFoundError(
                f"verification evidence not found: {evidence_id}"
            )

        try:
            return BuildVerificationEvidence.model_validate_json(
                path.read_text(encoding="utf-8-sig")
            )
        except OSError as exc:
            raise BuildVerificationPersistenceError(
                f"unable to load verification evidence: {evidence_id}"
            ) from exc

    def load_decision(
        self,
        decision_id: str,
    ) -> ReleaseGateDecision:
        """Load one persisted release-gate decision."""
        path = self._decision_path(decision_id)

        if not path.is_file():
            raise BuildVerificationNotFoundError(
                f"release decision not found: {decision_id}"
            )

        try:
            return ReleaseGateDecision.model_validate_json(
                path.read_text(encoding="utf-8-sig")
            )
        except OSError as exc:
            raise BuildVerificationPersistenceError(
                f"unable to load release decision: {decision_id}"
            ) from exc

    def list_evidence_ids(self) -> tuple[str, ...]:
        """Return persisted evidence identifiers deterministically."""
        directory = self.root / "evidence"

        if not directory.is_dir():
            return ()

        return tuple(
            sorted(path.stem for path in directory.glob("*.json"))
        )