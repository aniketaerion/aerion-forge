"""Provider-backed, non-mutating edit synthesis for M5.9 Package 4."""

from __future__ import annotations

from dataclasses import dataclass

from forge.general_engineering.change_set_factory import (
    build_generated_change_set,
)
from forge.general_engineering.edit_proposal_validator import (
    validate_generated_change_set,
)
from forge.general_engineering.models import (
    ChangePlan,
    EngineeringContext,
    EngineeringRequest,
    GeneratedChangeSet,
)
from forge.general_engineering.protocols import EngineeringProvider


@dataclass(frozen=True)
class EditSynthesisResult:
    change_set: GeneratedChangeSet
    operation_count: int
    affected_paths: tuple[str, ...]


class EngineeringEditSynthesisService:
    """Ask a reasoning provider for edit proposals, then validate them.

    The service exposes no file-writing or shell-execution capability.
    """

    def synthesize(
        self,
        *,
        provider: EngineeringProvider,
        request: EngineeringRequest,
        context: EngineeringContext,
        plan: ChangePlan,
    ) -> EditSynthesisResult:
        proposed = provider.synthesize_edits(
            request=request,
            context=context,
            plan=plan,
        )

        canonical = build_generated_change_set(
            plan=plan,
            operations=proposed.operations,
        )

        validate_generated_change_set(
            request=request,
            context=context,
            plan=plan,
            change_set=canonical,
        )

        return EditSynthesisResult(
            change_set=canonical,
            operation_count=len(canonical.operations),
            affected_paths=tuple(
                dict.fromkeys(
                    operation.target_path
                    for operation in canonical.operations
                )
            ),
        )


engineering_edit_synthesis_service = EngineeringEditSynthesisService()