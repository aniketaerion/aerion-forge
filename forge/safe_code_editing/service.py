"""Service orchestration for Safe Code Editing v1."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from forge.safe_code_editing.errors import SafeCodeEditingError
from forge.safe_code_editing.models import (
    EditTransactionResult,
    SafeEditReport,
    SafeEditRequest,
)
from forge.safe_code_editing.policies import SafeEditPolicy
from forge.safe_code_editing.transaction import execute_transaction


class SafeEditRequestLoadError(SafeCodeEditingError):
    """Raised when a persisted edit request cannot be loaded."""


class SafeCodeEditingService:
    """Load, validate and execute bounded safe-edit requests."""

    def __init__(self, policy: SafeEditPolicy | None = None) -> None:
        self.policy = policy or SafeEditPolicy()

    def load_request(self, path: Path) -> SafeEditRequest:
        """Load one immutable request from JSON."""
        try:
            payload: Any = json.loads(path.read_text(encoding="utf-8-sig"))
            return SafeEditRequest.model_validate(payload)
        except (OSError, json.JSONDecodeError, ValidationError, TypeError) as exc:
            raise SafeEditRequestLoadError(
                f"unable to load Safe Edit request {path}: {exc}"
            ) from exc

    def execute(self, request: SafeEditRequest) -> SafeEditReport:
        """Execute dry-run or approved apply mode and return audit evidence."""
        repository_root = Path(request.repository_root).expanduser().resolve()
        transaction: EditTransactionResult = execute_transaction(
            repository_root,
            request.file_plans,
            self.policy,
            dry_run=request.dry_run,
            approved=request.approved,
        )
        return SafeEditReport(
            request_id=request.request_id,
            transaction_id=transaction.transaction_id,
            dry_run=request.dry_run,
            approved=request.approved,
            file_results=transaction.file_results,
            validation_messages=transaction.errors,
        )

    def execute_file(
        self,
        path: Path,
        *,
        apply: bool = False,
        approved: bool = False,
    ) -> SafeEditReport:
        """Load a request file and execute with explicit CLI mode overrides."""
        request = self.load_request(path)
        effective = request.model_copy(
            update={
                "dry_run": not apply,
                "approved": approved if apply else False,
            }
        )
        return self.execute(effective)

    @staticmethod
    def write_report(report: SafeEditReport, destination: Path) -> Path:
        """Persist a structured JSON report."""
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            report.model_dump_json(indent=2) + "\n",
            encoding="utf-8",
        )
        return destination