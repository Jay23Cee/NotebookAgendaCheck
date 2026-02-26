from __future__ import annotations

from dataclasses import dataclass

from nicegui import ui

from app.constants import APP_DISPLAY_NAME


@dataclass
class ShellHandles:
    header_slot: ui.row
    content_slot: ui.element
    footer_slot: ui.row
    class_context_label: ui.label
    student_context_label: ui.label
    status_label: ui.label


def build_shell() -> ShellHandles:
    with ui.header(fixed=True, add_scroll_padding=False, bordered=True).classes("na-header shell_header"):
        header_slot = ui.row().classes("na-header-row shell_header_row")

    with ui.footer(fixed=True, bordered=True).classes("na-footer shell_footer"):
        footer_slot = ui.row().classes("na-footer-row shell_footer_row")

    with ui.element("div").classes("na-main shell_main"):
        with ui.element("div").classes("na-page-intro"):
            ui.label(APP_DISPLAY_NAME).classes("na-page-title")
            with ui.row().classes("na-top-status-row"):
                class_context_label = ui.label("Grade -").classes("na-top-status-chip")
                student_context_label = ui.label("Student 0 of 0").classes("na-top-status-chip")
                status_label = ui.label("Select Grade to begin.").classes(
                    "na-top-status-chip na-top-status-chip-status na-status info"
                )
        content_slot = ui.element("div").classes("na-content shell_content")

    return ShellHandles(
        header_slot=header_slot,
        content_slot=content_slot,
        footer_slot=footer_slot,
        class_context_label=class_context_label,
        student_context_label=student_context_label,
        status_label=status_label,
    )
