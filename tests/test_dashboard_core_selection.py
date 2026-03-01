from __future__ import annotations

from notebookagendacheck.nicegui_app.na_check.models import RosterStudent
from notebookagendacheck.nicegui_app.pages.dashboard_core.selection import (
    find_next_remaining_candidate,
    normalize_selected_student_ids,
    remaining_student_ids,
)


def _student(student_id: str) -> RosterStudent:
    return RosterStudent(
        grade="6",
        period="1",
        subject="Math",
        student_id=student_id,
        student_name=f"Student {student_id}",
    )


def _draft_key(student_id: str) -> tuple[str, str]:
    return student_id, "02/28/2026"


def test_normalize_selected_student_ids_dedupes_and_limits() -> None:
    selected, overflowed = normalize_selected_student_ids(
        ["S1", "S2", "S1", "S3", "S4"],
        available_ids=["S1", "S2", "S3", "S4"],
        max_selected=3,
    )

    assert selected == ["S1", "S2", "S3"]
    assert overflowed is True


def test_remaining_student_ids_filters_saved_rows() -> None:
    students = [_student("S1"), _student("S2"), _student("S3")]
    saved_keys = {_draft_key("S1"), _draft_key("S3")}

    remaining = remaining_student_ids(
        students,
        saved_keys=saved_keys,
        draft_key_for_student=_draft_key,
    )

    assert remaining == ["S2"]


def test_find_next_remaining_candidate_without_wrap() -> None:
    students = [_student("S1"), _student("S2"), _student("S3"), _student("S4")]
    saved_keys = {_draft_key("S3")}

    found = find_next_remaining_candidate(
        students,
        anchor_student_id="S1",
        blocked_ids={"S2"},
        saved_keys=saved_keys,
        draft_key_for_student=_draft_key,
        wrap=False,
    )

    assert found == "S4"


def test_find_next_remaining_candidate_with_wrap() -> None:
    students = [_student("S1"), _student("S2"), _student("S3"), _student("S4")]
    saved_keys = {_draft_key("S4")}

    found = find_next_remaining_candidate(
        students,
        anchor_student_id="S3",
        blocked_ids={"S2"},
        saved_keys=saved_keys,
        draft_key_for_student=_draft_key,
        wrap=True,
    )

    assert found == "S1"


