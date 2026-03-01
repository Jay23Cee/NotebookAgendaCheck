from __future__ import annotations

import csv
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

import pytest
from nicegui import ui

from notebookagendacheck.nicegui_app.na_check.models import RosterStudent
from notebookagendacheck.nicegui_app.na_check.storage import CsvStore
from notebookagendacheck.nicegui_app.pages.na_check_dashboard import (
    CARD_EFFECT_SAVE,
    CARD_EFFECT_UNDO,
    NACheckDashboard,
    SaveSnapshot,
    SaveTransaction,
    WRITE_STATE_UNSAVED_WRITE_FAILED,
)


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


@pytest.fixture
def notify_calls(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    calls: list[str] = []
    monkeypatch.setattr(ui, "notify", lambda message, **_kwargs: calls.append(str(message)))
    return calls


def _student(student_id: str) -> RosterStudent:
    return RosterStudent(
        grade="6",
        period="1",
        subject="Math",
        student_id=student_id,
        student_name=f"Student {student_id}",
    )


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _dashboard(tmp_path: Path) -> NACheckDashboard:
    dashboard = NACheckDashboard()
    dashboard.preferences_file = tmp_path / "prefs.json"
    dashboard.output_file = tmp_path / "checks.csv"
    dashboard.error_logger.log_path = tmp_path / "error_log.csv"
    dashboard.store = CsvStore(
        dashboard.output_file,
        quarantine_dir=tmp_path / "quarantine",
        session_id=dashboard.session_id,
        logger=dashboard.error_logger,
    )
    dashboard.roster = [_student("S1"), _student("S2")]
    dashboard.filtered_students = list(dashboard.roster)
    dashboard.date_input = DummyInput("02/28/2026")  # type: ignore[assignment]
    dashboard.grade_select = DummySelect(value="6", options={"6": "Grade 6"})  # type: ignore[assignment]
    dashboard.class_switch = DummySwitch(value=True)  # type: ignore[assignment]
    dashboard.student_select = DummySelect(  # type: ignore[assignment]
        value=[],
        options={student.student_id: student.student_name for student in dashboard.roster},
    )
    dashboard.sticky_choices_switch = DummyStickySwitch(value=True)  # type: ignore[assignment]
    return dashboard


def test_save_failure_sets_unsaved_state_and_preserves_drafts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    notify_calls: list[str],
) -> None:
    dashboard = _dashboard(tmp_path)
    student = dashboard.roster[0]
    key = dashboard._draft_key(student.student_id)
    dashboard._update_draft(student.student_id, lambda form: setattr(form, "agenda_legible", False))

    monkeypatch.setattr(dashboard.store, "append_rows", lambda _rows: (_ for _ in ()).throw(OSError("locked")))

    dashboard._save_students([student])

    assert dashboard.write_state == WRITE_STATE_UNSAVED_WRITE_FAILED
    assert dashboard.status_message == "Unsaved - Write Failed"
    assert key in dashboard.draft_state_by_key
    assert key not in dashboard.saved_keys
    assert dashboard._pending_card_effect_by_student_id == {}
    assert len(notify_calls) == 1


def test_duplicate_save_errors_are_suppressed_with_counter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    notify_calls: list[str],
) -> None:
    dashboard = _dashboard(tmp_path)
    student = dashboard.roster[0]

    monkeypatch.setattr(dashboard.store, "append_rows", lambda _rows: (_ for _ in ()).throw(OSError("locked")))

    dashboard._save_students([student])
    dashboard._save_students([student])

    assert dashboard.status_message == "Unsaved - Write Failed (x2)"
    assert len(notify_calls) == 1
    rows = _read_rows(dashboard.error_logger.log_path)
    assert len(rows) == 2


def test_undo_failure_restores_transaction_stack(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    notify_calls: list[str],
) -> None:
    dashboard = _dashboard(tmp_path)
    student = dashboard.roster[0]
    key = dashboard._draft_key(student.student_id)
    form = deepcopy(dashboard._ensure_draft(student.student_id))
    dashboard.save_transactions = [SaveTransaction(entries=[SaveSnapshot(key=key, student=student, form=form)])]

    monkeypatch.setattr(
        dashboard.store,
        "undo_last_saved_rows",
        lambda _count: (_ for _ in ()).throw(OSError("locked")),
    )

    dashboard._undo_last_saved()

    assert dashboard.write_state == WRITE_STATE_UNSAVED_WRITE_FAILED
    assert dashboard.status_message == "Unsaved - Write Failed"
    assert len(dashboard.save_transactions) == 1
    assert dashboard._pending_card_effect_by_student_id == {}
    assert len(notify_calls) == 1


def test_save_success_queues_save_effect(tmp_path: Path, notify_calls: list[str]) -> None:
    dashboard = _dashboard(tmp_path)
    student = dashboard.roster[0]

    dashboard._save_students([student])

    assert dashboard.status_message == "Saved 1 student(s)"
    assert dashboard._pending_card_effect_by_student_id == {student.student_id: CARD_EFFECT_SAVE}
    assert notify_calls[-1] == "Saved 1 student(s)"


def test_undo_success_queues_undo_effect(tmp_path: Path, notify_calls: list[str]) -> None:
    dashboard = _dashboard(tmp_path)
    student = dashboard.roster[0]

    dashboard._save_students([student])
    dashboard._pending_card_effect_by_student_id.clear()

    dashboard._undo_last_saved()

    assert dashboard.status_message == "Undid the last save transaction"
    assert dashboard._pending_card_effect_by_student_id == {student.student_id: CARD_EFFECT_UNDO}
    assert notify_calls[-1] == "Undid the last save transaction"

