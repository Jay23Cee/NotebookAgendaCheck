from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from nicegui import ui
from nicegui.events import ValueChangeEventArguments

from app.nicegui_app.services.scoring_service import COMMENT_TAGS_BY_GROUP, TagDefinition


@dataclass
class StatusTagsCardHandles:
    auto_flag_chip: ui.chip
    chip_by_tag: dict[str, ui.chip]
    comment_toggle: ui.switch
    comment_input: ui.textarea
    deduction_value_label: ui.label


def build_status_tags_card(
    *,
    on_tag_toggle: Callable[[str, bool], None],
    on_comment_toggle: Callable[[ValueChangeEventArguments], None],
    on_comment_change: Callable[[ValueChangeEventArguments], None],
) -> StatusTagsCardHandles:
    chip_by_tag: dict[str, ui.chip] = {}

    with ui.card().classes("na-card na-status-card card"):
        ui.label("Status + Tags").classes("na-card-title")
        ui.label("Track flags, deductions, and performance tags.").classes("na-card-helper")

        with ui.column().classes("na-status-block"):
            ui.label("Auto Flags").classes("na-section-title")
            auto_flag_chip = ui.chip("None", selectable=False, icon="flag").classes(
                "na-auto-flag-chip chip chip_warn"
            )

        with ui.column().classes("na-status-block"):
            ui.label("Completion Status (Deductions)").classes("na-section-title")
            _build_tag_row(
                tags=COMMENT_TAGS_BY_GROUP["completion"],
                css_class="na-chip chip chip_warn",
                chip_by_tag=chip_by_tag,
                on_tag_toggle=on_tag_toggle,
            )

        with ui.column().classes("na-status-block"):
            ui.label("Legibility / Organization").classes("na-section-title")
            _build_tag_row(
                tags=COMMENT_TAGS_BY_GROUP["legibility"],
                css_class="na-chip na-chip-deduction chip chip_neg",
                chip_by_tag=chip_by_tag,
                on_tag_toggle=on_tag_toggle,
            )

        with ui.column().classes("na-status-block"):
            ui.label("Positive Performance").classes("na-section-title")
            _build_tag_row(
                tags=COMMENT_TAGS_BY_GROUP["positive"],
                css_class="na-chip na-chip-positive chip chip_pos",
                chip_by_tag=chip_by_tag,
                on_tag_toggle=on_tag_toggle,
            )

        with ui.row().classes("na-comment-row"):
            comment_toggle = ui.switch("Add comment", value=False, on_change=on_comment_toggle)
            deduction_value_label = ui.label("Deduction: 0.0").classes("na-deduction-text")

        comment_input = ui.textarea(
            label="Additional notes",
            value="",
            placeholder="Optional notes...",
            on_change=on_comment_change,
        ).classes("na-comment-input")
        comment_input.visible = False

    return StatusTagsCardHandles(
        auto_flag_chip=auto_flag_chip,
        chip_by_tag=chip_by_tag,
        comment_toggle=comment_toggle,
        comment_input=comment_input,
        deduction_value_label=deduction_value_label,
    )


def _build_tag_row(
    *,
    tags: tuple[TagDefinition, ...],
    css_class: str,
    chip_by_tag: dict[str, ui.chip],
    on_tag_toggle: Callable[[str, bool], None],
) -> None:
    with ui.row().classes("na-chip-row"):
        for definition in tags:
            chip_label = definition.label
            if definition.deduction > 0:
                chip_label = f"{chip_label} (-{definition.deduction})"
            chip = ui.chip(
                text=chip_label,
                selectable=True,
                selected=False,
                on_selection_change=lambda event, tag=definition.tag: on_tag_toggle(tag, bool(event.value)),
            ).classes(css_class)
            chip_by_tag[definition.tag] = chip
