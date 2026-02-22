from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from nicegui import ui
from nicegui.events import ValueChangeEventArguments


@dataclass
class HeaderBarHandles:
    grade_select: ui.select
    student_select: ui.select
    checker_mode_select: ui.select
    checker_student_select: ui.select
    date_input: ui.input
    progress_chip: ui.chip


def build_header_bar(
    *,
    on_grade_change: Callable[[ValueChangeEventArguments], None],
    on_student_change: Callable[[ValueChangeEventArguments], None],
    on_checker_mode_change: Callable[[ValueChangeEventArguments], None],
    on_checker_student_change: Callable[[ValueChangeEventArguments], None],
    on_date_change: Callable[[ValueChangeEventArguments], None],
    initial_date: str,
) -> HeaderBarHandles:
    with ui.row().classes("na-header-grid topbar"):
        with ui.row().classes("na-header-group na-header-left"):
            grade_select = ui.select(
                options={"6": "Grade 6", "7": "Grade 7", "8": "Grade 8"},
                label="Grade",
                value=None,
                on_change=on_grade_change,
            ).classes("na-control")

        with ui.row().classes("na-header-group na-header-center"):
            student_select = ui.select(
                options={},
                label="Student",
                value=None,
                on_change=on_student_change,
            ).classes("na-control na-student-select")
            progress_chip = ui.chip("Student 0 of 0", selectable=False).classes("na-progress-chip")

        with ui.row().classes("na-header-group na-header-right"):
            with ui.row().classes("na-user-controls"):
                checker_mode_select = ui.select(
                    options={"teacher": "Teacher", "student": "Student"},
                    label="Checked By",
                    value="teacher",
                    on_change=on_checker_mode_change,
                ).classes("na-control na-user-mode")
                checker_student_select = ui.select(
                    options={},
                    label="Student checker",
                    value=None,
                    on_change=on_checker_student_change,
                ).classes("na-control na-checker-student")
            date_input = ui.input(
                label="Date",
                value=initial_date,
                validation={"Use MM/DD/YYYY": lambda value: _is_valid_date(value)},
            ).props("readonly").classes("na-control na-date-input")
            with ui.menu().props("no-parent-event") as date_menu:
                ui.date(
                    value=initial_date,
                    on_change=on_date_change,
                ).props("mask=MM/DD/YYYY").bind_value(date_input)
            with date_input.add_slot("append"):
                ui.icon("calendar_month").classes("cursor-pointer").on("click", date_menu.open)

    return HeaderBarHandles(
        grade_select=grade_select,
        student_select=student_select,
        checker_mode_select=checker_mode_select,
        checker_student_select=checker_student_select,
        date_input=date_input,
        progress_chip=progress_chip,
    )


def _is_valid_date(value: str) -> bool:
    if not value:
        return False
    try:
        from datetime import datetime

        datetime.strptime(value, "%m/%d/%Y")
    except ValueError:
        return False
    return True
