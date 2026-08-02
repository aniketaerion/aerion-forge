"""Atomic deterministic persistence for Impact Decision."""

import json
import os
import tempfile
from pathlib import Path

from pydantic import ValidationError

from forge.impact.errors import (
    ImpactPersistenceError,
    ImpactSchemaMismatchError,
    ImpactStoreCorruptionError,
)
from forge.impact.models import (
    SCHEMA_VERSION,
    ImpactAssessment,
    ImpactDecisionGeneration,
    ImpactDecisionStore,
)


class ImpactRepository:
    """Persist impact assessments without partial replacement."""

    def __init__(
        self,
        path: Path,
        history_limit: int = 5,
    ) -> None:
        if history_limit < 0:
            raise ValueError("history_limit cannot be negative.")

        self.path = path
        self.history_limit = history_limit

    def load(self) -> ImpactDecisionStore:
        """Load and validate the Impact Decision store."""

        if not self.path.exists():
            return ImpactDecisionStore()

        try:
            raw = self.path.read_text(encoding="utf-8")
            payload = json.loads(raw)
        except (
            OSError,
            UnicodeError,
            json.JSONDecodeError,
        ) as exc:
            raise ImpactStoreCorruptionError(
                "Persisted Impact Decision state is unreadable."
            ) from exc

        if not isinstance(payload, dict):
            raise ImpactStoreCorruptionError(
                "Persisted Impact Decision state must be a JSON object."
            )

        schema_version = payload.get("schema_version")

        if schema_version != SCHEMA_VERSION:
            raise ImpactSchemaMismatchError(
                f"Unsupported Impact Decision store schema: {schema_version!r}."
            )

        try:
            return ImpactDecisionStore.model_validate(payload)
        except ValidationError as exc:
            raise ImpactStoreCorruptionError(
                "Persisted Impact Decision state violates the store contract."
            ) from exc

    def save(
        self,
        assessment: ImpactAssessment,
        generation: ImpactDecisionGeneration,
    ) -> ImpactDecisionStore:
        """Atomically persist one impact assessment."""

        self._validate_generation(
            assessment,
            generation,
        )

        previous = self.load()

        assessments = dict(previous.assessments)
        history = {
            assessment_id: list(versions) for assessment_id, versions in previous.history.items()
        }
        generations = dict(previous.generations)

        existing = assessments.get(assessment.assessment_id)

        if (
            existing is not None
            and existing.assessment_fingerprint != assessment.assessment_fingerprint
        ):
            versions = history.setdefault(
                assessment.assessment_id,
                [],
            )
            versions.append(existing)

            if self.history_limit == 0:
                history.pop(
                    assessment.assessment_id,
                    None,
                )
            else:
                history[assessment.assessment_id] = versions[-self.history_limit :]

        assessments[assessment.assessment_id] = assessment
        generations[assessment.assessment_id] = generation

        updated = ImpactDecisionStore(
            assessments={
                assessment_id: assessments[assessment_id] for assessment_id in sorted(assessments)
            },
            history={
                assessment_id: history[assessment_id]
                for assessment_id in sorted(history)
                if history[assessment_id]
            },
            generations={
                assessment_id: generations[assessment_id] for assessment_id in sorted(generations)
            },
        )

        content = (
            updated.model_dump_json(
                indent=2,
                exclude_none=False,
            )
            + "\n"
        ).encode("utf-8")

        self._atomic_write(content)

        reloaded = self.load()

        if reloaded != updated:
            raise ImpactPersistenceError(
                "Persisted Impact Decision state failed post-write verification."
            )

        return reloaded

    def delete(
        self,
        assessment_id: str,
    ) -> ImpactDecisionStore:
        """Delete one assessment and its active generation."""

        previous = self.load()

        if assessment_id not in previous.assessments:
            return previous

        assessments = dict(previous.assessments)
        history = {key: list(values) for key, values in previous.history.items()}
        generations = dict(previous.generations)

        removed = assessments.pop(assessment_id)

        if self.history_limit > 0:
            versions = history.setdefault(
                assessment_id,
                [],
            )
            versions.append(removed)
            history[assessment_id] = versions[-self.history_limit :]
        else:
            history.pop(assessment_id, None)

        generations.pop(assessment_id, None)

        updated = ImpactDecisionStore(
            assessments={key: assessments[key] for key in sorted(assessments)},
            history={key: history[key] for key in sorted(history) if history[key]},
            generations={key: generations[key] for key in sorted(generations)},
        )

        content = (
            updated.model_dump_json(
                indent=2,
                exclude_none=False,
            )
            + "\n"
        ).encode("utf-8")

        self._atomic_write(content)
        return self.load()

    def snapshot_bytes(self) -> bytes | None:
        """Return current store bytes for rollback."""

        if not self.path.exists():
            return None

        try:
            return self.path.read_bytes()
        except OSError as exc:
            raise ImpactPersistenceError("Unable to snapshot the Impact Decision store.") from exc

    def restore_bytes(
        self,
        snapshot: bytes | None,
    ) -> None:
        """Restore a previous store snapshot."""

        if snapshot is None:
            try:
                self.path.unlink(missing_ok=True)
            except OSError as exc:
                raise ImpactPersistenceError(
                    "Unable to remove the Impact Decision store during rollback."
                ) from exc
            return

        self._atomic_write(snapshot)

    def probe_write(self) -> None:
        """Verify that atomic writes are supported."""

        probe = b'{"probe":"impact-decision-store"}\n'
        directory = self.path.parent
        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary: Path | None = None

        try:
            descriptor, name = tempfile.mkstemp(
                prefix=".impact-probe-",
                suffix=".tmp",
                dir=directory,
            )
            temporary = Path(name)

            with os.fdopen(descriptor, "wb") as stream:
                stream.write(probe)
                stream.flush()
                os.fsync(stream.fileno())
        except OSError as exc:
            raise ImpactPersistenceError("Impact Decision store write probe failed.") from exc
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def _validate_generation(
        self,
        assessment: ImpactAssessment,
        generation: ImpactDecisionGeneration,
    ) -> None:
        if generation.assessment_id != assessment.assessment_id:
            raise ImpactPersistenceError("Generation assessment ID does not match the assessment.")

        if generation.assessment_fingerprint != assessment.assessment_fingerprint:
            raise ImpactPersistenceError("Generation fingerprint does not match the assessment.")

        if generation.mission_id != assessment.mission_id:
            raise ImpactPersistenceError("Generation mission does not match the assessment.")

        if generation.task_set_fingerprint != assessment.task_set_fingerprint:
            raise ImpactPersistenceError(
                "Generation Task Set fingerprint does not match the assessment."
            )

    def _atomic_write(self, content: bytes) -> None:
        """Write bytes using same-directory atomic replacement."""

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary: Path | None = None

        try:
            descriptor, name = tempfile.mkstemp(
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                dir=self.path.parent,
            )
            temporary = Path(name)

            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())

            os.replace(
                temporary,
                self.path,
            )
            temporary = None
        except OSError as exc:
            raise ImpactPersistenceError(
                "Atomic Impact Decision store replacement failed."
            ) from exc
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
