from __future__ import annotations

from dataclasses import dataclass

import pytest
from nicegui import ui

from app.nicegui_app.na_check.models import RosterStudent
from app.nicegui_app.pages.na_check_dashboard import NACheckDashboard


@dataclass
class DummyLabel:
    text: str = ""

    def set_text(self, value: str) -> None:
        self.text = value


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
class DummyButton:
    text: str = ""
    classes_value: str = ""
    enabled: bool = True

    def set_text(self, value: str) -> None:
        self.text = value

    def classes(self, *, replace: str | None = None, add: str | None = None, remove: str | None = None) -> None:
        if replace is not None:
            self.classes_value = replace
        if add:
            self.classes_value = f"{self.classes_value} {add}".strip()
        if remove:
            self.classes_value = self.classes_value.replace(remove, "").strip()

    def enable(self) -> None:
        self.enabled = True

    def disable(self) -> None:
        self.enabled = False


@pytest.fixture(autouse=True)
def _stub_notify(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ui, "notify", lambda *_args, **_kwargs: None)


def _student(student_id: str) -> RosterStudent:
    return RosterStudent(
        grade="6",
        period="1",
        subject="Math",
        student_id=student_id,
        student_name=f"Student {student_id}",
    )


def _dashboard() -> NACheckDashboard:
    dashboard = NACheckDashboard()
    dashboard.roster = [_student("S1"), _student("S2"), _student("S3")]
    dashboard.filtered_students = list(dashboard.roster)
    dashboard.date_input = DummyInput("02/22/2026")  # type: ignore[assignment]
    dashboard.grade_select = DummySelect(value="6")  # type: ignore[assignment]
    dashboard.class_switch = DummySwitch(value=True)  # type: ignore[assignment]
    dashboard.student_select = DummySelect(  # type: ignore[assignment]
        value=[],
        options={student.student_id: student.student_name for student in dashboard.roster},
    )
    return dashboard


def _saved_key(dashboard: NACheckDashboard, student_id: str) -> tuple[str, str]:
    return dashboard._draft_key(student_id)


def test_select_next_not_checked_replaces_only_clicked_slot() -> None:
    dashboard = _dashboard()
    dashboard.roster = [_student("S1"), _student("S2"), _student("S3"), _student("S4")]
    dashboard.filtered_students = list(dashboard.roster)
    dashboard.student_select.options = {student.student_id: student.student_name for student in dashboard.roster}
    dashboard.selected_student_ids = ["S1", "S2", "S3"]

    dashboard._select_next_not_checked("S2")

    assert dashboard.selected_student_ids == ["S1", "S4", "S3"]
    assert dashboard.status_message == "Moved to next student"


def test_select_next_not_checked_stops_at_end_without_wrap() -> None:
    dashboard = _dashboard()
    dashboard.selected_student_ids = ["S3"]

    dashboard._select_next_not_checked("S3")

    assert dashboard.selected_student_ids == ["S3"]
    assert dashboard.status_message == "No later remaining student available"


def test_select_next_not_checked_when_all_checked_keeps_selection() -> None:
    dashboard = _dashboard()
    dashboard.selected_student_ids = ["S2", "S3"]
    dashboard.saved_keys = {_saved_key(dashboard, "S1"), _saved_key(dashboard, "S2"), _saved_key(dashboard, "S3")}

    dashboard._select_next_not_checked("S2")

    assert dashboard.selected_student_ids == ["S2", "S3"]
    assert dashboard.status_message == "No remaining students for this date"


def test_select_next_not_checked_skips_already_selected_students() -> None:
    dashboard = _dashboard()
    dashboard.roster = [_student("S1"), _student("S2"), _student("S3"), _student("S4")]
    dashboard.filtered_students = list(dashboard.roster)
    dashboard.student_select.options = {student.student_id: student.student_name for student in dashboard.roster}
    dashboard.selected_student_ids = ["S1", "S2", "S4"]

    dashboard._select_next_not_checked("S1")

    assert dashboard.selected_student_ids == ["S3", "S2", "S4"]
    assert dashboard.status_message == "Moved to next student"


def test_toggle_not_checked_filter_prunes_picker_options_and_selection() -> None:
    dashboard = _dashboard()
    dashboard.selected_student_ids = ["S1", "S2"]
    dashboard.saved_keys = {_saved_key(dashboard, "S2")}

    dashboard._toggle_not_checked_filter()

    assert dashboard.show_not_checked_only is True
    assert dashboard.status_message == "Showing remaining students"
    assert set(dashboard.student_select.options) == {"S1", "S3"}
    assert dashboard.selected_student_ids == ["S1"]

    dashboard._toggle_not_checked_filter()

    assert dashboard.show_not_checked_only is False
    assert dashboard.status_message == "Showing all students"
    assert set(dashboard.student_select.options) == {"S1", "S2", "S3"}


def test_available_students_for_picker_respects_filter_state() -> None:
    dashboard = _dashboard()
    dashboard.saved_keys = {_saved_key(dashboard, "S2")}

    dashboard.show_not_checked_only = False
    assert [student.student_id for student in dashboard._available_students_for_picker()] == ["S1", "S2", "S3"]

    dashboard.show_not_checked_only = True
    assert [student.student_id for student in dashboard._available_students_for_picker()] == ["S1", "S3"]


def test_refresh_summary_strip_enables_global_filter_button_and_updates_label() -> None:
    dashboard = _dashboard()
    dashboard.selected_metric_label = DummyLabel()  # type: ignore[assignment]
    dashboard.remaining_metric_label = DummyLabel()  # type: ignore[assignment]
    dashboard.unsaved_metric_label = DummyLabel()  # type: ignore[assignment]
    dashboard.filter_toggle_button = DummyButton()
    dashboard.selected_student_ids = ["S1", "S2", "S3"]
    dashboard.saved_keys = {_saved_key(dashboard, "S1")}
    dashboard._update_draft("S2", lambda form: setattr(form, "agenda_legible", False))

    dashboard._refresh_summary_strip()

    assert dashboard.filter_toggle_button.enabled is True
    # assert dashboard.filter_toggle_button.text == "Remaining only"
    assert dashboard.selected_metric_label.text == "3"
    assert dashboard.remaining_metric_label.text == "2 of 3 visible"
    assert dashboard.unsaved_metric_label.text == "2"

    dashboard.filtered_students = []
    dashboard.show_not_checked_only = True
    dashboard._refresh_summary_strip()

    assert dashboard.filter_toggle_button.enabled is False
    assert dashboard.filter_toggle_button.text == "All"


def test_notify_status_ignores_deleted_slot_runtime_error(monkeypatch: pytest.MonkeyPatch) -> None:
    dashboard = _dashboard()

    def raise_deleted_slot(*_args, **_kwargs) -> None:
        raise RuntimeError("The parent element this slot belongs to has been deleted.")

    monkeypatch.setattr(ui, "notify", raise_deleted_slot)
    monkeypatch.setattr(dashboard.error_logger, "log_exception", lambda **_kwargs: None)

    dashboard._notify_status("Message after re-render")
