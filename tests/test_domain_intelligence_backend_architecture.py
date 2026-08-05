from pathlib import Path

from forge.domain_intelligence.backend.architecture import (
    classify_backend_architecture,
)


def test_architecture_classifies_layered_backend(
    tmp_path: Path,
) -> None:
    source = tmp_path / "services"
    source.mkdir()

    (source / "orders_service.py").write_text(
        "class OrdersService: pass",
        encoding="utf-8",
    )

    assert (
        classify_backend_architecture(tmp_path)
        == "layered-backend"
    )


def test_architecture_reports_undetermined(
    tmp_path: Path,
) -> None:
    assert (
        classify_backend_architecture(tmp_path)
        == "undetermined"
    )