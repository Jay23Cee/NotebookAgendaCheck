from __future__ import annotations

import csv
import json
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
    dashboard.preferences_file = tmp_path / "ui_preferences.json"
    dashboard.output_file = tmp_path / "checks.csv"
    dashboard.store = CsvStore(dashboard.output_file)
    dashboard.date_input = DummyInput("02/22/2026")  # type: ignore[assignment]
    dashboard.grade_select = DummySelect(value="6", options={"6": "Grade 6", "7": "Grade 7"})  # type: ignore[assignment]
    dashboard.class_switch = DummySwitch(value=True)  # type: ignore[assignment]
    dashboard.student_select = DummySelect(value=[], options={})  # type: ignore[assignment]
    dashboard.sticky_choices_switch = DummyStickySwitch(value=True)  # type: ignore[assignment]
    return dashboard


def test_refresh_student_options_filters_by_grade_and_subject(tmp_path: Path) -> None:
    dashboard = _dashboard(tmp_path)
    dashboard.roster = [
        _student("M1", grade="6", period="1", subject="Math"),
        _student("S1", grade="6", period="4", subject="Science"),
        _student("S2", grade="7", period="4", subject="Science"),
    ]
    dashboard.class_switch.value = False

    dashboard._refresh_student_options(reset_selection=True)

    assert [student.student_id for student in dashboard.filtered_students] == ["S1"]
    assert set(dashboard.student_select.options) == {"S1"}


def test_refresh_subject_options_blocks_when_subject_data_missing(tmp_path: Path) -> None:
    dashboard = _dashboard(tmp_path)
    dashboard.roster = [
        _student("M1", grade="6", period="1", subject="Math"),
        _student("X1", grade="6", period="2", subject=""),
    ]
    dashboard.student_select.options = {"M1": "Student M1"}
    dashboard.selected_student_ids = ["M1"]

    dashboard._refresh_subject_options()
    dashboard._refresh_student_options(reset_selection=True)

    assert dashboard.class_switch.enabled is False
    assert dashboard.student_select.enabled is False
    assert dashboard.student_select.options == {}
    assert dashboard.filtered_students == []
    assert dashboard.selected_student_ids == []
    assert "must include Subject values" in dashboard.status_message


def test_refresh_subject_options_single_subject_disables_switch(tmp_path: Path) -> None:
    dashboard = _dashboard(tmp_path)
    dashboard.roster = [_student("M1", grade="6", period="1", subject="Math")]
    dashboard.class_switch.value = False

    dashboard._refresh_subject_options()

    assert dashboard.class_switch.enabled is False
    assert dashboard.class_switch.value is True


def test_save_students_uses_each_student_period_value(tmp_path: Path) -> None:
    dashboard = _dashboard(tmp_path)
    dashboard.roster = [
        _student("M1", grade="6", period="1", subject="Math"),
        _student("M2", grade="6", period="4", subject="Math"),
    ]
    dashboard.filtered_students = list(dashboard.roster)
    dashboard.student_select.options = {student.student_id: student.student_name for student in dashboard.roster}
    dashboard.class_switch.value = True

    dashboard._save_students(list(dashboard.roster))

    with dashboard.output_file.open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert [row["Period"] for row in rows] == ["1", "4"]


def test_persist_preferences_writes_subject_key(tmp_path: Path) -> None:
    dashboard = _dashboard(tmp_path)
    dashboard.class_switch.value = False
    dashboard.date_input.value = "02/27/2026"

    dashboard._persist_preferences()

    payload = json.loads(dashboard.preferences_file.read_text(encoding="utf-8"))
    prefs = payload["na_check_dashboard"]
    assert prefs["subject"] == "Science"
    assert "period" not in prefs


def test_switch_subject_mapping_helpers() -> None:
    dashboard = NACheckDashboard()

    assert dashboard._switch_to_subject(False) == "Science"
    assert dashboard._switch_to_subject(True) == "Math"
    assert dashboard._subject_to_switch("Science") is False
    assert dashboard._subject_to_switch("Math") is True


@pytest.mark.parametrize(
    ("saved_subject", "expected_switch"),
    [
        ("Science", False),
        ("Math", True),
    ],
)
def test_apply_preferences_sets_switch_from_subject_key(
    tmp_path: Path,
    saved_subject: str,
    expected_switch: bool,
) -> None:
    dashboard = _dashboard(tmp_path)
    dashboard.roster = [
        _student("M1", grade="6", period="1", subject="Math"),
        _student("S1", grade="6", period="4", subject="Science"),
    ]
    dashboard.grade_select.value = None
    dashboard.class_switch.value = None
    dashboard.student_select.options = {}
    dashboard.sticky_choices_switch.value = False
    dashboard.preferences_file.write_text(
        json.dumps(
            {
                "na_check_dashboard": {
                    "sticky_enabled": True,
                    "grade": "6",
                    "subject": saved_subject,
                    "check_date": "02/16/2026",
                }
            }
        ),
        encoding="utf-8",
    )

    dashboard._apply_preferences_if_enabled()

    assert dashboard.class_switch.value is expected_switch
    assert dashboard.date_input.value == "02/16/2026"


def test_apply_preferences_migrates_legacy_period_to_subject(tmp_path: Path) -> None:
    dashboard = _dashboard(tmp_path)
    dashboard.roster = [
        _student("M1", grade="6", period="1", subject="Math"),
        _student("S1", grade="6", period="4", subject="Science"),
    ]
    dashboard.grade_select.value = None
    dashboard.class_switch.value = None
    dashboard.student_select.options = {}
    dashboard.sticky_choices_switch.value = False
    dashboard.preferences_file.write_text(
        json.dumps(
            {
                "na_check_dashboard": {
                    "sticky_enabled": True,
                    "grade": "6",
                    "period": "4",
                    "check_date": "02/15/2026",
                }
            }
        ),
        encoding="utf-8",
    )

    dashboard._apply_preferences_if_enabled()

    assert dashboard.sticky_choices_switch.value is True
    assert dashboard.grade_select.value == "6"
    assert dashboard.class_switch.value is False
    assert dashboard.date_input.value == "02/15/2026"

