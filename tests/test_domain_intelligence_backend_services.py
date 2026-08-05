from pathlib import Path

from forge.domain_intelligence.backend.services import (
    discover_service_files,
)


def test_service_file_discovery(tmp_path: Path) -> None:
    services = tmp_path / "src" / "services"
    services.mkdir(parents=True)

    (services / "order_service.py").write_text(
        "class OrderService: pass",
        encoding="utf-8",
    )

    assert discover_service_files(tmp_path) == (
        "src/services/order_service.py",
    )