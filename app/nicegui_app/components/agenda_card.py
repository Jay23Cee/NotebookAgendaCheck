from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from nicegui import ui
from nicegui.events import ValueChangeEventArguments

from app.scoring import AGENDA_FILLED_BLANK, AGENDA_FILLED_COMPLETE, AGENDA_FILLED_PARTIAL


@dataclass
class AgendaCardHandles:
    root: ui.card
    agenda_present: ui.checkbox
    agenda_filled_today: ui.toggle
    agenda_readable: ui.checkbox
    mini_score: ui.label


def build_agenda_card(
    *,
    on_agenda_present: Callable[[ValueChangeEventArguments], None],
    on_agenda_filled: Callable[[ValueChangeEventArguments], None],
    on_agenda_readable: Callable[[ValueChangeEventArguments], None],
) -> AgendaCardHandles:
    with ui.card().classes("na-card card") as root:
        ui.label("Agenda").classes("na-card-title")
        ui.label("Check agenda quality in order.").classes("na-card-helper")

        agenda_present = ui.checkbox("Agenda present", value=False, on_change=on_agenda_present).classes(
            "na-checkbox"
        )
        ui.label("Agenda filled today").classes("na-card-helper")
        agenda_filled_today = ui.toggle(
            options={
                AGENDA_FILLED_COMPLETE: "Complete",
                AGENDA_FILLED_PARTIAL: "Partial",
                AGENDA_FILLED_BLANK: "Blank",
            },
            value=AGENDA_FILLED_BLANK,
            on_change=on_agenda_filled,
        ).classes("na-control na-toggle")
        agenda_readable = ui.checkbox("Agenda readable", value=False, on_change=on_agenda_readable).classes(
            "na-checkbox"
        )

        ui.separator().classes("na-sep")
        with ui.row().classes("na-mini-score-row score_bar"):
            ui.label("Agenda").classes("na-mini-score-label")
            mini_score = ui.label("0.0 / 10").classes("na-mini-score-value")

    return AgendaCardHandles(
        root=root,
        agenda_present=agenda_present,
        agenda_filled_today=agenda_filled_today,
        agenda_readable=agenda_readable,
        mini_score=mini_score,
    )
