"""Aggregate validation for Engineering Memory."""

from forge.engineering_memory.errors import (
    EngineeringMemoryValidationError,
)
from forge.engineering_memory.identifiers import (
    build_memory_fingerprint,
    build_store_fingerprint,
    validate_evidence_id,
    validate_fingerprint,
    validate_generation_id,
    validate_memory_id,
    validate_relationship_id,
)
from forge.engineering_memory.models import (
    EngineeringMemoryConfiguration,
    EngineeringMemoryStore,
    EngineeringMemoryValidationMessage,
    EngineeringMemoryValidationResult,
    MemoryRecord,
    MemoryValidationSeverity,
)
from forge.engineering_memory.policies import (
    validate_memory_policy,
)


class EngineeringMemoryValidator:
    """Validate records and persisted Engineering Memory state."""

    def __init__(
        self,
        configuration: (EngineeringMemoryConfiguration | None) = None,
    ) -> None:
        self.configuration = configuration or EngineeringMemoryConfiguration()

    def validate_record(
        self,
        record: MemoryRecord,
    ) -> EngineeringMemoryValidationResult:
        """Validate one canonical memory record."""

        messages: list[EngineeringMemoryValidationMessage] = []

        def error(field: str, message: str) -> None:
            messages.append(
                EngineeringMemoryValidationMessage(
                    severity=MemoryValidationSeverity.ERROR,
                    field=field,
                    message=message,
                    memory_id=record.memory_id,
                )
            )

        if not validate_memory_id(record.memory_id):
            error(
                "memory_id",
                "Memory ID does not match the frozen contract.",
            )

        if not validate_fingerprint(record.memory_fingerprint):
            error(
                "memory_fingerprint",
                "Memory fingerprint is not canonical SHA-256.",
            )
        elif build_memory_fingerprint(record) != record.memory_fingerprint:
            error(
                "memory_fingerprint",
                "Memory fingerprint does not match record content.",
            )

        if len(record.evidence) > self.configuration.max_evidence_per_record:
            error(
                "evidence",
                "Evidence count exceeds the configured limit.",
            )

        if len(record.relationships) > self.configuration.max_relationships_per_record:
            error(
                "relationships",
                "Relationship count exceeds the configured limit.",
            )

        for evidence in record.evidence:
            if not validate_evidence_id(evidence.evidence_id):
                error(
                    "evidence",
                    f"Invalid evidence ID: {evidence.evidence_id}",
                )

            if not validate_fingerprint(evidence.fingerprint):
                error(
                    "evidence",
                    "Evidence fingerprint is not canonical SHA-256.",
                )

        for relationship in record.relationships:
            if not validate_relationship_id(relationship.relationship_id):
                error(
                    "relationships",
                    "Relationship ID does not match the contract.",
                )

            if relationship.source_memory_id != record.memory_id:
                error(
                    "relationships",
                    "Relationship source does not match its record.",
                )

        for name, fingerprint in record.created_from_fingerprints.items():
            if not name.strip():
                error(
                    "created_from_fingerprints",
                    "Fingerprint source names cannot be blank.",
                )

            if not validate_fingerprint(fingerprint):
                error(
                    "created_from_fingerprints",
                    "Source fingerprint is not canonical SHA-256.",
                )

        try:
            validate_memory_policy(
                memory_type=record.memory_type,
                confidence=record.confidence,
                retention_policy=record.retention_policy,
                allow_unknown_confidence=(self.configuration.allow_unknown_confidence),
                allow_temporary_records=(self.configuration.allow_temporary_records),
            )
        except EngineeringMemoryValidationError as exc:
            error("policy", str(exc))

        return EngineeringMemoryValidationResult(
            valid=not any(
                message.severity is MemoryValidationSeverity.ERROR for message in messages
            ),
            messages=tuple(messages),
        )

    def validate_store(
        self,
        store: EngineeringMemoryStore,
    ) -> EngineeringMemoryValidationResult:
        """Validate the complete persisted memory store."""

        messages: list[EngineeringMemoryValidationMessage] = []

        if len(store.records) > self.configuration.max_records:
            messages.append(
                EngineeringMemoryValidationMessage(
                    severity=MemoryValidationSeverity.ERROR,
                    field="records",
                    message=("Record count exceeds the configured limit."),
                )
            )

        for memory_id, record in sorted(store.records.items()):
            if memory_id != record.memory_id:
                messages.append(
                    EngineeringMemoryValidationMessage(
                        severity=(MemoryValidationSeverity.ERROR),
                        field="records",
                        message=("Store key does not match memory ID."),
                        memory_id=record.memory_id,
                    )
                )

            result = self.validate_record(record)
            messages.extend(result.messages)

            for relationship in record.relationships:
                if relationship.target_memory_id not in store.records:
                    messages.append(
                        EngineeringMemoryValidationMessage(
                            severity=(MemoryValidationSeverity.ERROR),
                            field="relationships",
                            message=("Relationship target does not exist in the active store."),
                            memory_id=record.memory_id,
                        )
                    )

        if store.generation is not None:
            generation = store.generation

            if not validate_generation_id(generation.generation_id):
                messages.append(
                    EngineeringMemoryValidationMessage(
                        severity=MemoryValidationSeverity.ERROR,
                        field="generation",
                        message=("Generation ID does not match the frozen contract."),
                    )
                )

            expected_fingerprint = build_store_fingerprint(store.records)

            if generation.store_fingerprint != expected_fingerprint:
                messages.append(
                    EngineeringMemoryValidationMessage(
                        severity=MemoryValidationSeverity.ERROR,
                        field="generation",
                        message=("Generation fingerprint does not match active records."),
                    )
                )

            relationship_count = sum(len(record.relationships) for record in store.records.values())
            evidence_count = sum(len(record.evidence) for record in store.records.values())

            if generation.record_count != len(store.records):
                messages.append(
                    EngineeringMemoryValidationMessage(
                        severity=MemoryValidationSeverity.ERROR,
                        field="generation",
                        message=("Generation record count is incorrect."),
                    )
                )

            if generation.relationship_count != relationship_count:
                messages.append(
                    EngineeringMemoryValidationMessage(
                        severity=MemoryValidationSeverity.ERROR,
                        field="generation",
                        message=("Generation relationship count is incorrect."),
                    )
                )

            if generation.evidence_count != evidence_count:
                messages.append(
                    EngineeringMemoryValidationMessage(
                        severity=MemoryValidationSeverity.ERROR,
                        field="generation",
                        message=("Generation evidence count is incorrect."),
                    )
                )

        return EngineeringMemoryValidationResult(
            valid=not any(
                message.severity is MemoryValidationSeverity.ERROR for message in messages
            ),
            messages=tuple(messages),
        )

    def validate_record_or_raise(
        self,
        record: MemoryRecord,
    ) -> None:
        """Raise if one memory record is invalid."""

        result = self.validate_record(record)

        if not result.valid:
            details = "; ".join(message.message for message in result.messages)
            raise EngineeringMemoryValidationError(details)

    def validate_store_or_raise(
        self,
        store: EngineeringMemoryStore,
    ) -> None:
        """Raise if persisted Engineering Memory is invalid."""

        result = self.validate_store(store)

        if not result.valid:
            details = "; ".join(message.message for message in result.messages)
            raise EngineeringMemoryValidationError(details)
