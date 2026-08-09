from pathlib import Path

from forge.general_engineering.request_builder import (
    build_engineering_request,
)


def test_request_builder_normalizes_and_preserves_scope(
    tmp_path: Path,
) -> None:
    request = build_engineering_request(
        objective="  Add   validation and tests. ",
        repository_root=tmp_path,
        constraints=(
            " Do not modify README. ",
            "do not modify README.",
        ),
        acceptance_criteria=("Tests pass",),
        explicit_target_paths=(r".\src\service.py",),
        forbidden_paths=(r".\docs",),
        allow_code_changes=True,
    )

    assert request.objective == "Add validation and tests."
    assert request.constraints == ("Do not modify README.",)
    assert request.acceptance_criteria == ("Tests pass",)
    assert request.explicit_target_paths == ("src/service.py",)
    assert request.forbidden_paths == ("docs",)
    assert request.allow_code_changes is True


def test_request_builder_identifier_is_deterministic(
    tmp_path: Path,
) -> None:
    first = build_engineering_request(
        objective="Add validation",
        repository_root=tmp_path,
    )
    second = build_engineering_request(
        objective="Add validation",
        repository_root=tmp_path,
    )

    assert first.request_id == second.request_id