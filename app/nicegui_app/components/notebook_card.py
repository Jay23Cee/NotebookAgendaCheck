from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from nicegui import ui
from nicegui.events import ValueChangeEventArguments

from app.scoring import NOTEBOOK_WORK_COMPLETE, NOTEBOOK_WORK_MISSING, NOTEBOOK_WORK_PARTIAL


@dataclass
class NotebookCardHandles:
    root: ui.card
    notebook_present: ui.checkbox
    notebook_work_today: ui.toggle
    notebook_organized: ui.checkbox
    mini_score: ui.label


def build_notebook_card(
    *,
    on_notebook_present: Callable[[ValueChangeEventArguments], None],
    on_notebook_work: Callable[[ValueChangeEventArguments], None],
    on_notebook_organized: Callable[[ValueChangeEventArguments], None],
) -> NotebookCardHandles:
    with ui.card().classes("na-card card") as root:
        ui.label("Notebook").classes("na-card-title")
        ui.label("Check notebook quality in order.").classes("na-card-helper")

        notebook_present = ui.checkbox("Notebook present", value=False, on_change=on_notebook_present).classes(
            "na-checkbox"
        )
        ui.label("Notebook work today").classes("na-card-helper")
        notebook_work_today = ui.toggle(
            options={
                NOTEBOOK_WORK_COMPLETE: "Complete",
                NOTEBOOK_WORK_PARTIAL: "Partial",
                NOTEBOOK_WORK_MISSING: "Missing",
            },
            value=NOTEBOOK_WORK_MISSING,
            on_change=on_notebook_work,
        ).classes("na-control na-toggle")
        notebook_organized = ui.checkbox("Notebook organized", value=False, on_change=on_notebook_organized).classes(
            "na-checkbox"
        )

        ui.separator().classes("na-sep")
        with ui.row().classes("na-mini-score-row score_bar"):
            ui.label("Notebook").classes("na-mini-score-label")
            mini_score = ui.label("0.0 / 10").classes("na-mini-score-value")

    return NotebookCardHandles(
        root=root,
        notebook_present=notebook_present,
        notebook_work_today=notebook_work_today,
        notebook_organized=notebook_organized,
        mini_score=mini_score,
    )
