from forge.general_engineering.edit_evidence import evidence_fingerprint_map
from forge.general_engineering.models import (
    EngineeringContext,
    RelevantFile,
    RepositoryEvidence,
)
from forge.general_engineering.states import EvidenceType


def test_evidence_fingerprint_map_uses_grounded_evidence() -> None:
    context = EngineeringContext(
        request_id="request-1",
        relevant_files=(
            RelevantFile(
                path="src/service.py",
                evidence_ids=("evidence-1",),
                rationale="grounded",
            ),
        ),
        evidence=(
            RepositoryEvidence(
                evidence_id="evidence-1",
                path="src/service.py",
                evidence_type=EvidenceType.FILE,
                rationale="grounded",
                relevance=1.0,
                fingerprint="fingerprint-1",
            ),
        ),
    )

    assert evidence_fingerprint_map(context) == {
        "src/service.py": "fingerprint-1"
    }