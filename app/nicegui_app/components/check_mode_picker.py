from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from nicegui import ui
from nicegui.events import ValueChangeEventArguments


@dataclass
class CheckModePickerHandles:
    chooser_root: ui.element
    mode_radio: ui.radio
    selected_root: ui.element
    selected_chip: ui.chip
    change_button: ui.button


def build_check_mode_picker(
    *,
    on_mode_change: Callable[[ValueChangeEventArguments], None],
    on_change_click: Callable[[], None],
) -> CheckModePickerHandles:
    with ui.element("div").classes("na-mode-picker-wrap"):
        with ui.card().classes("na-mode-picker") as chooser_root:
            ui.label("Check Type").classes("na-card-title")
            ui.label("Choose what is being checked today.").classes("na-card-helper")
            mode_radio = ui.radio(
                options={
                    "notebook_only": "Notebook check only",
                    "both": "Notebook + Agenda check",
                    "agenda_only": "Agenda check only",
                },
                value=None,
                on_change=on_mode_change,
            ).classes("na-mode-radio")

        with ui.row().classes("na-mode-selected"):
            with ui.row().classes("na-mode-selected-row") as selected_root:
                selected_chip = ui.chip("Mode: -", selectable=False).classes("na-progress-chip")
                change_button = ui.button("Change mode", on_click=on_change_click).classes(
                    "na-btn na-btn-secondary"
                )
            selected_root.visible = False

    return CheckModePickerHandles(
        chooser_root=chooser_root,
        mode_radio=mode_radio,
        selected_root=selected_root,
        selected_chip=selected_chip,
        change_button=change_button,
    )
