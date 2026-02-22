from __future__ import annotations

from app.models import CheckRecord
from app.nicegui_app.models.ui_state import SaveHistoryEntry
from app.nicegui_app.pages.check_page import CheckPage
from app.students import Student


def _student(student_id: str) -> Student:
    return Student(student_id=student_id, first_name="Ada", last_name="Lovelace", grade=7)


def _record(student_id: str, student_name: str) -> CheckRecord:
    return CheckRecord(
        student_id=student_id,
        student_name=student_name,
        grade=7,
        check_mode="both",
        date="02/22/2026",
        checker="TEACHER",
        notebook_score=10.0,
        agenda_present=True,
        entry_written=True,
        all_subjects_filled=True,
        organized=True,
        agenda_score=10,
        gradebook_score=10.0,
    )


def test_history_target_student_prefers_active_student() -> None:
    page = CheckPage()
    page.controller.state.session.roster = [_student("S1"), _student("S2")]
    page.controller.state.session.current_index = 1

    assert page._history_target_student_id() == "S2"


def test_history_target_student_uses_last_saved_when_roster_complete() -> None:
    page = CheckPage()
    page.controller.state.session.roster = [_student("S1")]
    page.controller.state.session.current_index = 1
    page.controller.state.save_history = [
        SaveHistoryEntry(
            index_before_save=0,
            record=_record("S1", "Lovelace, Ada"),
        )
    ]

    assert page._history_target_student_id() == "S1"
