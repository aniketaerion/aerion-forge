"""Mission Reporting renderer tests."""

import json
from pathlib import Path

import pytest

from forge.mission_reporting.errors import (
    MissionReportingReportError,
)
from forge.mission_reporting.renderer import (
    REPORT_NAMES,
    MissionReportRenderer,
)
from tests.test_mission_reporting_builder import _build


def test_render_returns_complete_suite(
    tmp_path: Path,
) -> None:
    rendered = MissionReportRenderer().render(_build(tmp_path))

    assert tuple(rendered) == REPORT_NAMES


def test_render_is_deterministic(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    renderer = MissionReportRenderer()

    assert renderer.render(report) == renderer.render(report)


def test_report_json_is_valid(
    tmp_path: Path,
) -> None:
    rendered = MissionReportRenderer().render(_build(tmp_path))

    payload = json.loads(rendered["MISSION_REPORT.json"])

    assert payload["report_id"]


def test_summary_json_is_valid(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    rendered = MissionReportRenderer().render(report)

    payload = json.loads(rendered["MISSION_SUMMARY.json"])

    assert payload["mission_id"] == report.mission_id
    assert payload["status"] == report.status.value


def test_traceability_json_is_valid(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    rendered = MissionReportRenderer().render(report)

    payload = json.loads(rendered["MISSION_TRACEABILITY.json"])

    assert payload["traceability_count"] == len(report.traceability)


def test_risks_json_is_valid(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    rendered = MissionReportRenderer().render(report)

    payload = json.loads(rendered["MISSION_RISKS.json"])

    assert payload["risk_count"] == len(report.risks)


def test_markdown_contains_report_identity(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    rendered = MissionReportRenderer().render(report)

    markdown = rendered["MISSION_REPORT.md"].decode("utf-8")

    assert report.report_id in markdown
    assert report.mission_id in markdown


def test_markdown_contains_sections(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    rendered = MissionReportRenderer().render(report)

    markdown = rendered["MISSION_REPORT.md"].decode("utf-8")

    for section in report.sections:
        assert f"## {section.title}" in markdown


def test_markdown_contains_safety_boundary(
    tmp_path: Path,
) -> None:
    rendered = MissionReportRenderer().render(_build(tmp_path))

    markdown = rendered["MISSION_REPORT.md"].decode("utf-8")

    assert "## Safety Boundary" in markdown
    assert "does not execute tasks" in markdown


def test_write_creates_all_reports(
    tmp_path: Path,
) -> None:
    renderer = MissionReportRenderer()
    rendered = renderer.render(_build(tmp_path))
    directory = tmp_path / "reports"

    paths = renderer.write(
        directory,
        rendered,
    )

    assert tuple(path.name for path in paths) == REPORT_NAMES

    for name in REPORT_NAMES:
        assert (directory / name).is_file()


def test_written_content_matches_rendered_content(
    tmp_path: Path,
) -> None:
    renderer = MissionReportRenderer()
    rendered = renderer.render(_build(tmp_path))
    directory = tmp_path / "reports"

    renderer.write(
        directory,
        rendered,
    )

    for name in REPORT_NAMES:
        assert (directory / name).read_bytes() == rendered[name]


def test_write_rejects_missing_report(
    tmp_path: Path,
) -> None:
    renderer = MissionReportRenderer()
    rendered = dict(renderer.render(_build(tmp_path)))
    rendered.pop("MISSION_REPORT.md")

    with pytest.raises(MissionReportingReportError):
        renderer.write(
            tmp_path / "reports",
            rendered,
        )


def test_write_rejects_extra_report(
    tmp_path: Path,
) -> None:
    renderer = MissionReportRenderer()
    rendered = dict(renderer.render(_build(tmp_path)))
    rendered["EXTRA.txt"] = b"unexpected"

    with pytest.raises(MissionReportingReportError):
        renderer.write(
            tmp_path / "reports",
            rendered,
        )


def test_write_overwrites_existing_reports(
    tmp_path: Path,
) -> None:
    renderer = MissionReportRenderer()
    rendered = renderer.render(_build(tmp_path))
    directory = tmp_path / "reports"
    directory.mkdir()

    for name in REPORT_NAMES:
        (directory / name).write_bytes(b"old")

    renderer.write(
        directory,
        rendered,
    )

    for name in REPORT_NAMES:
        assert (directory / name).read_bytes() == rendered[name]


def test_atomic_failure_raises_report_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    renderer = MissionReportRenderer()
    rendered = renderer.render(_build(tmp_path))

    def fail_replace(
        source: object,
        target: object,
    ) -> None:
        raise OSError("replacement failed")

    monkeypatch.setattr(
        "forge.mission_reporting.renderer.os.replace",
        fail_replace,
    )

    with pytest.raises(MissionReportingReportError):
        renderer.write(
            tmp_path / "reports",
            rendered,
        )


def test_failed_write_restores_existing_reports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    renderer = MissionReportRenderer()
    rendered = renderer.render(_build(tmp_path))
    directory = tmp_path / "reports"
    directory.mkdir()

    originals = {name: f"old-{name}".encode() for name in REPORT_NAMES}

    for name, content in originals.items():
        (directory / name).write_bytes(content)

    original_atomic_write = renderer._atomic_write
    calls = 0

    def fail_once(
        path: Path,
        content: bytes,
    ) -> None:
        nonlocal calls
        calls += 1

        if calls == 2:
            raise MissionReportingReportError("simulated write failure")

        original_atomic_write(
            path,
            content,
        )

    monkeypatch.setattr(
        renderer,
        "_atomic_write",
        fail_once,
    )

    with pytest.raises(MissionReportingReportError):
        renderer.write(
            directory,
            rendered,
        )

    for name, content in originals.items():
        assert (directory / name).read_bytes() == content
