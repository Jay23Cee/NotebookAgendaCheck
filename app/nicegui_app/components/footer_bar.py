from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from nicegui import ui


@dataclass
class FooterBarHandles:
    agenda_value: ui.label
    notebook_value: ui.label
    internal_value: ui.label
    gradebook_value: ui.label
    save_button: ui.button
    undo_button: ui.button


def build_footer_bar(
    *,
    on_save: Callable[[], None],
    on_undo: Callable[[], None],
) -> FooterBarHandles:
    with ui.row().classes("na-footer-grid footer_bar"):
        with ui.row().classes("na-score-strip"):
            with ui.column().classes("na-score-block"):
                ui.label("Agenda").classes("na-score-label")
                agenda_value = ui.label("0.0").classes("na-score-value")

            with ui.column().classes("na-score-block"):
                ui.label("Notebook").classes("na-score-label")
                notebook_value = ui.label("0.0").classes("na-score-value")

            with ui.column().classes("na-score-block"):
                ui.label("Internal /20").classes("na-score-label")
                internal_value = ui.label("0.0").classes("na-score-value")

            with ui.column().classes("na-score-block na-score-block-primary"):
                ui.label("Gradebook /10").classes("na-score-label")
                gradebook_value = ui.label("0.0").classes("na-score-value na-score-value-primary")

        with ui.row().classes("na-footer-actions"):
            save_button = ui.button("Save + Next", on_click=on_save).classes("na-btn na-btn-primary primary_btn")
            undo_button = ui.button("Undo Last", on_click=on_undo).classes("na-btn na-btn-secondary")
            ui.label("Enter = Save+Next, U = Undo").classes("na-shortcut-hint")

    return FooterBarHandles(
        agenda_value=agenda_value,
        notebook_value=notebook_value,
        internal_value=internal_value,
        gradebook_value=gradebook_value,
        save_button=save_button,
        undo_button=undo_button,
    )
