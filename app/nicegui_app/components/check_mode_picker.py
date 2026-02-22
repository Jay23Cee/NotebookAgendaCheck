from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from nicegui import ui
from nicegui.events import ValueChangeEventArguments


@dataclass
class CheckModePickerHandles:
    chooser_root: ui.element
    mode_radio: ui.radio


def build_check_mode_picker(
    *,
    on_mode_change: Callable[[ValueChangeEventArguments], None],
) -> CheckModePickerHandles:
    with ui.element("div").classes("na-mode-picker-wrap"):
        with ui.card().classes("na-mode-picker") as chooser_root:
            ui.label("Check Type").classes("na-card-title")
            ui.label("Choose what is being checked today.").classes("na-card-helper")
            mode_radio = ui.radio(
                options={
                    "both": "Notebook + Agenda check",
                    "notebook_only": "Notebook check only",
                    "agenda_only": "Agenda check only",
                },
                value=None,
                on_change=on_mode_change,
            ).classes("na-mode-radio")

    return CheckModePickerHandles(
        chooser_root=chooser_root,
        mode_radio=mode_radio,
    )
