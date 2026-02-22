from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from nicegui import ui
from nicegui.events import ValueChangeEventArguments


@dataclass
class HistoryPanelHandles:
    root: ui.element
    start_date_input: ui.input
    end_date_input: ui.input
    include_with_comments: ui.checkbox
    include_without_comments: ui.checkbox
    table: ui.table
    warning_label: ui.label


def build_history_panel(
    *,
    on_filter_change: Callable[[ValueChangeEventArguments | None], None],
) -> HistoryPanelHandles:
    with ui.card().classes("na-card na-history-card") as root:
        ui.label("History (Last 50)").classes("na-card-title")

        with ui.row().classes("na-history-filters"):
            start_date_input = ui.input(
                label="Start date",
                value="",
                validation={"Use YYYY-MM-DD": _is_valid_date_or_blank},
                on_change=on_filter_change,
            ).classes("na-control na-date-input")
            end_date_input = ui.input(
                label="End date",
                value="",
                validation={"Use YYYY-MM-DD": _is_valid_date_or_blank},
                on_change=on_filter_change,
            ).classes("na-control na-date-input")
            include_with_comments = ui.checkbox("With comments", value=True, on_change=on_filter_change).classes(
                "na-checkbox"
            )
            include_without_comments = ui.checkbox(
                "Without comments", value=True, on_change=on_filter_change
            ).classes("na-checkbox")

        warning_label = ui.label("").classes("na-card-helper")

        table = ui.table(
            columns=[
                {"name": "date", "label": "Date", "field": "date"},
                {"name": "student_name", "label": "Student", "field": "student_name"},
                {"name": "check_mode", "label": "Mode", "field": "check_mode"},
                {"name": "agenda_score", "label": "Agenda", "field": "agenda_score"},
                {"name": "notebook_score", "label": "Notebook", "field": "notebook_score"},
                {"name": "internal_score", "label": "Internal", "field": "internal_score"},
                {"name": "gradebook_score", "label": "Gradebook", "field": "gradebook_score"},
                {"name": "comment_deduction", "label": "Deduction", "field": "comment_deduction"},
                {"name": "has_comment", "label": "Commented", "field": "has_comment"},
                {"name": "comments", "label": "Comments", "field": "comments"},
            ],
            rows=[],
            pagination={"rowsPerPage": 10},
        ).classes("na-history-table")

    return HistoryPanelHandles(
        root=root,
        start_date_input=start_date_input,
        end_date_input=end_date_input,
        include_with_comments=include_with_comments,
        include_without_comments=include_without_comments,
        table=table,
        warning_label=warning_label,
    )


def _is_valid_date_or_blank(value: str) -> bool:
    if not value:
        return True
    try:
        from datetime import datetime

        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return False
    return True
