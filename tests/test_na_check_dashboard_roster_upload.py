from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
from nicegui import ui

from notebookagendacheck.nicegui_app.na_check.models import RosterStudent
from notebookagendacheck.nicegui_app.na_check.storage import CsvStore
from notebookagendacheck.nicegui_app.pages.na_check_dashboard import NACheckDashboard


@dataclass
class DummyInput:
    value: str

    def update(self) -> None:
        return None


@dataclass
class DummySelect:
    value: object = None
    options: dict[str, str] | None = None

    def __post_init__(self) -> None:
        if self.options is None:
            self.options = {}
        self.enabled = True

    def update(self) -> None:
        return None

    def enable(self) -> None:
        self.enabled = True

    def disable(self) -> None:
        self.enabled = False


@dataclass
class DummySwitch:
    value: object = None

    def __post_init__(self) -> None:
        self.enabled = True

    def update(self) -> None:
        return None

    def enable(self) -> None:
        self.enabled = True

    def disable(self) -> None:
        self.enabled = False


@dataclass
class DummyStickySwitch:
    value: bool

    def update(self) -> None:
        return None


@pytest.fixture(autouse=True)
def _stub_notify(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ui, "notify", lambda *_args, **_kwargs: None)


def _student(student_id: str, *, grade: str, period: str, subject: str) -> RosterStudent:
    return RosterStudent(
        grade=grade,
        period=period,
        subject=subject,
        student_id=student_id,
        student_name=f"Student {student_id}",
    )


def _dashboard(tmp_path: Path) -> NACheckDashboard:
    dashboard = NACheckDashboard()
    dashboard.runtime_roster_file = tmp_path / "records" / "roster" / "current_roster.csv"
    dashboard.preferences_file = tmp_path / "ui_preferences.json"
    dashboard.output_file = tmp_path / "checks.csv"
    dashboard.store = CsvStore(dashboard.output_file)
    dashboard.date_input = DummyInput("02/22/2026")  # type: ignore[assignment]
    dashboard.grade_select = DummySelect(value="6", options={"6": "Grade 6"})  # type: ignore[assignment]
    dashboard.class_switch = DummySwitch(value=True)  # type: ignore[assignment]
    dashboard.student_select = DummySelect(value=[], options={})  # type: ignore[assignment]
    dashboard.sticky_choices_switch = DummyStickySwitch(value=False)  # type: ignore[assignment]
    return dashboard


def test_import_roster_csv_persists_runtime_file_and_refreshes_grades(tmp_path: Path) -> None:
    dashboard = _dashboard(tmp_path)
    dashboard.roster = [_student("M1", grade="6", period="1", subject="Math")]
    dashboard.filtered_students = list(dashboard.roster)

    payload = (
        "StudentID,StudentName,Grade,Subject,Period\n"
        "M1,Student M1,6,Math,1\n"
        "S1,Student S1,7,Science,4\n"
    ).encode("utf-8")

    imported = dashboard._import_roster_csv_bytes(file_name="students.csv", payload=payload)

    assert imported is True
    assert dashboard.students_file == dashboard.runtime_roster_file
    assert dashboard.runtime_roster_file.exists()
    assert len(dashboard.roster) == 2
    assert set(dashboard.grade_select.options) == {"6", "7"}


def test_import_roster_csv_blocks_when_selected_students_unsaved(tmp_path: Path) -> None:
    dashboard = _dashboard(tmp_path)
    student = _student("M1", grade="6", period="1", subject="Math")
    dashboard.roster = [student]
    dashboard.filtered_students = [student]
    dashboard.selected_student_ids = [student.student_id]

    payload = (
        "StudentID,StudentName,Grade,Subject\n"
        "M1,Student M1,6,Math\n"
    ).encode("utf-8")

    imported = dashboard._import_roster_csv_bytes(file_name="students.csv", payload=payload)

    assert imported is False
    assert dashboard.runtime_roster_file.exists() is False


def test_import_roster_csv_invalid_input_keeps_existing_roster(tmp_path: Path) -> None:
    dashboard = _dashboard(tmp_path)
    existing = [_student("M1", grade="6", period="1", subject="Math")]
    dashboard.roster = list(existing)
    dashboard.filtered_students = list(existing)
    dashboard.runtime_roster_file.parent.mkdir(parents=True, exist_ok=True)
    original_csv = (
        "StudentID,StudentName,Grade,Subject,Period\n"
        "M1,Student M1,6,Math,1\n"
    )
    dashboard.runtime_roster_file.write_text(original_csv, encoding="utf-8")

    payload = (
        "StudentID,StudentName,Grade,Subject\n"
        "S1,Student S1,5,Science\n"
    ).encode("utf-8")

    imported = dashboard._import_roster_csv_bytes(file_name="students.csv", payload=payload)

    assert imported is False
    assert [student.student_id for student in dashboard.roster] == ["M1"]
    assert dashboard.runtime_roster_file.read_text(encoding="utf-8") == original_csv


def test_import_roster_csv_does_not_modify_existing_score_history(tmp_path: Path) -> None:
    dashboard = _dashboard(tmp_path)
    dashboard.output_file.write_text(
        "StudentID,Date\nM1,02/22/2026\n",
        encoding="utf-8",
    )
    before = dashboard.output_file.read_text(encoding="utf-8")

    payload = (
        "StudentID,StudentName,Grade,Subject,Period\n"
        "M1,Student M1,6,Math,1\n"
    ).encode("utf-8")

    imported = dashboard._import_roster_csv_bytes(file_name="students.csv", payload=payload)

    assert imported is True
    assert dashboard.output_file.read_text(encoding="utf-8") == before
