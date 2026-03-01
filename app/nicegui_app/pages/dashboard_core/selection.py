from __future__ import annotations

from typing import Callable, Sequence

from app.nicegui_app.na_check.models import RosterStudent


def normalize_selected_student_ids(
    raw_values: object,
    *,
    available_ids: Sequence[str],
    max_selected: int,
) -> tuple[list[str], bool]:
    incoming: list[str]
    if isinstance(raw_values, list):
        incoming = [str(value) for value in raw_values]
    elif raw_values is None:
        incoming = []
    else:
        incoming = [str(raw_values)]

    deduped: list[str] = []
    for student_id in incoming:
        if student_id in available_ids and student_id not in deduped:
            deduped.append(student_id)

    overflowed = len(deduped) > max_selected
    return deduped[:max_selected], overflowed


def remaining_student_ids(
    students: Sequence[RosterStudent],
    *,
    saved_keys: set[tuple[str, str]],
    draft_key_for_student: Callable[[str], tuple[str, str]],
) -> list[str]:
    return [
        student.student_id
        for student in students
        if draft_key_for_student(student.student_id) not in saved_keys
    ]


def find_next_remaining_candidate(
    students: Sequence[RosterStudent],
    *,
    anchor_student_id: str,
    blocked_ids: set[str],
    saved_keys: set[tuple[str, str]],
    draft_key_for_student: Callable[[str], tuple[str, str]],
    wrap: bool,
) -> str | None:
    index_by_student_id = {student.student_id: index for index, student in enumerate(students)}
    anchor_index = index_by_student_id.get(anchor_student_id)
    if anchor_index is None:
        return None

    ordered_ids = [student.student_id for student in students]
    search_order = ordered_ids[anchor_index + 1 :]
    if wrap:
        search_order += ordered_ids[:anchor_index]

    for student_id in search_order:
        if student_id == anchor_student_id or student_id in blocked_ids:
            continue
        if draft_key_for_student(student_id) in saved_keys:
            continue
        return student_id
    return None

