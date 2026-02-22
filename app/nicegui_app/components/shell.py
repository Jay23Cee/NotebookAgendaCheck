from __future__ import annotations

from dataclasses import dataclass

from nicegui import ui

from app.constants import APP_DASHBOARD_SUBTITLE, APP_DISPLAY_NAME


@dataclass
class ShellHandles:
    header_slot: ui.row
    content_slot: ui.element
    footer_slot: ui.row
    class_context_label: ui.label
    student_context_label: ui.label
    status_label: ui.label


def build_shell() -> ShellHandles:
    with ui.left_drawer(fixed=True, bordered=True).classes("na-sidebar shell_sidebar"):
        ui.label(APP_DISPLAY_NAME).classes("na-sidebar-title")
        ui.label(APP_DASHBOARD_SUBTITLE).classes("na-sidebar-subtitle")
        ui.separator().classes("na-sep")

        ui.label("CLASS CONTEXT").classes("na-sidebar-section-title")
        class_context_label = ui.label("Grade -").classes("na-sidebar-context")
        student_context_label = ui.label("No roster loaded").classes("na-sidebar-context")

        ui.separator().classes("na-sep")
        ui.label("LOCAL-ONLY SAFETY").classes("na-sidebar-section-title")
        ui.label("Roster: data/mock_students.xlsx").classes("na-sidebar-context")
        ui.label("Output: records/notebook_agenda_checks.csv").classes("na-sidebar-context")
        ui.label("No Google sync").classes("na-sidebar-context")
        ui.label("No Excel writes").classes("na-sidebar-context")

        ui.separator().classes("na-sep")
        ui.label("STATUS").classes("na-sidebar-section-title")
        status_label = ui.label("Select Grade to begin.").classes("na-status info")

    with ui.header(fixed=True, add_scroll_padding=False, bordered=True).classes("na-header shell_header"):
        header_slot = ui.row().classes("na-header-row shell_header_row")

    with ui.footer(fixed=True, bordered=True).classes("na-footer shell_footer"):
        footer_slot = ui.row().classes("na-footer-row shell_footer_row")

    with ui.element("div").classes("na-main shell_main"):
        content_slot = ui.element("div").classes("na-content shell_content")

    return ShellHandles(
        header_slot=header_slot,
        content_slot=content_slot,
        footer_slot=footer_slot,
        class_context_label=class_context_label,
        student_context_label=student_context_label,
        status_label=status_label,
    )
