from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path

from nicegui import ui
from nicegui.events import KeyEventArguments, ValueChangeEventArguments

from app.constants import DEFAULT_OUTPUT_FILE, DEFAULT_STUDENTS_FILE, DEFAULT_UI_PREFERENCES_FILE
from app.nicegui_app.na_check.models import CheckFormState, RosterStudent
from app.nicegui_app.na_check.roster import load_roster
from app.nicegui_app.na_check.scoring import (
    COMMENT_PRESETS,
    TAG_DEFINITIONS,
    TAG_LABEL_BY_KEY,
    apply_auto_rules,
    default_form_state,
    score_form,
)
from app.nicegui_app.na_check.storage import CsvStore
from app.scoring import SCORE_MODEL_INTERNAL20_GRADEBOOK10_V1

PREFERENCES_KEY = "na_check_dashboard"
MAX_SELECTED_STUDENTS = 3
SAVED_OPTION_PREFIX = "__SAVED__|"
TODO_OPTION_PREFIX = "__TODO__|"
TEACHER_LABEL = "TEACHER"


@dataclass
class SaveSnapshot:
    key: tuple[str, str]
    student: RosterStudent
    form: CheckFormState


@dataclass
class SaveTransaction:
    entries: list[SaveSnapshot]


@dataclass
class StudentCardHandles:
    student: RosterStudent
    root: ui.card
    status_chip: ui.chip
    next_ungraded_button: ui.button
    lock_hint: ui.label
    agenda_present: ui.toggle
    agenda_entry: ui.toggle
    agenda_legible: ui.toggle
    notebook_present: ui.toggle
    notebook_date: ui.toggle
    notebook_title: ui.toggle
    notebook_notes: ui.toggle
    notebook_organized: ui.toggle
    notebook_legible: ui.toggle
    agenda_score: ui.label
    notebook_score: ui.label
    status_score: ui.label
    total_score: ui.label
    gradebook_score: ui.label
    deduction_label: ui.label
    auto_flag_chip: ui.chip
    tags_select: ui.select
    comment_checks: dict[str, ui.checkbox]
    comment_textarea: ui.textarea
    tags_summary: ui.label
    comment_summary: ui.label
    comments_panel: ui.element
    chevron_icon: ui.icon
    save_button: ui.button


class NACheckDashboard:
    def __init__(self) -> None:
        self.students_file = DEFAULT_STUDENTS_FILE
        self.output_file = DEFAULT_OUTPUT_FILE
        self.preferences_file = DEFAULT_UI_PREFERENCES_FILE

        self.store = CsvStore(self.output_file)
        self.roster: list[RosterStudent] = load_roster(self.students_file)
        self.filtered_students: list[RosterStudent] = []

        self.card_handles_by_student_id: dict[str, StudentCardHandles] = {}
        self.draft_state_by_key: dict[tuple[str, str], CheckFormState] = {}
        self.expanded_keys: set[tuple[str, str]] = set()
        self.saved_keys: set[tuple[str, str]] = set()
        self.save_transactions: list[SaveTransaction] = []

        self._syncing = False
        self.status_message = "Select grade, period, and students to start grading."

        self.grade_select: ui.select | None = None
        self.period_select: ui.select | None = None
        self.student_select: ui.select | None = None
        self.date_input: ui.input | None = None
        self.sticky_choices_switch: ui.switch | None = None

        self.show_not_checked_only = False
        self.selected_student_ids: list[str] = []

        self.save_all_button: ui.button | None = None
        self.undo_button: ui.button | None = None
        self.filter_toggle_button: ui.button | None = None

        self.group_summary_label: ui.label | None = None
        self.progress_summary_label: ui.label | None = None
        self.card_summary_label: ui.label | None = None
        self.status_label: ui.label | None = None

        self.batch_grid: ui.element | None = None

    def build(self) -> None:
        ui.add_css(Path(__file__).resolve().parents[1] / "styles" / "na_check_dashboard.css", shared=True)

        with ui.element("div").classes("na2-page"):
            with ui.element("div").classes("na2-sticky-wrap"):
                self._build_top_bar()
                self._build_global_actions()
                self._build_summary_strip()
            self.batch_grid = ui.element("div").classes("na2-batch-grid na2-cols-3")

        ui.keyboard(on_key=self._on_keyboard, repeating=False, ignore=["textarea"])

        self._initialize_selectors()
        self._reload_saved_keys_for_date()
        self._render_batch_cards()
        self._refresh_summary_strip()

    def _build_top_bar(self) -> None:
        with ui.row().classes("na2-topbar"):
            self.grade_select = ui.select(
                options={},
                value=None,
                label="Grade",
                on_change=self._on_grade_change,
            ).classes("na2-control")

            self.period_select = ui.select(
                options={},
                value=None,
                label="Period",
                on_change=self._on_period_change,
            ).classes("na2-control")

            self.student_select = ui.select(
                options={},
                value=[],
                label="Students",
                on_change=self._on_student_selection_change,
                with_input=True,
                multiple=True,
                clearable=True,
            ).classes("na2-control")
            self.student_select.props("use-chips input-debounce=0")
            self.student_select.add_slot(
                "option",
                """
                <q-item
                  v-bind="props.itemProps"
                  :class="[
                    props.opt.label.startsWith('__SAVED__|') ? 'na2-student-option-row-saved' : 'na2-student-option-row-not-checked',
                    props.selected ? 'na2-student-option-row-selected' : ''
                  ]"
                >
                  <q-item-section avatar>
                    <q-icon
                      :name="props.opt.label.startsWith('__SAVED__|') ? 'check_box' : 'check_box_outline_blank'"
                      :color="props.opt.label.startsWith('__SAVED__|') ? 'positive' : (props.selected ? 'warning' : 'negative')"
                    />
                  </q-item-section>
                  <q-item-section>
                    <q-item-label>
                      {{ props.opt.label.split('|').slice(1).join('|') }}
                    </q-item-label>
                  </q-item-section>
                </q-item>
                """,
            )
            self.student_select.add_slot(
                "selected-item",
                """
                <q-chip
                  dense
                  class="na2-student-chip"
                  :class="[
                    props.opt.label.startsWith('__SAVED__|') ? 'na2-student-chip-saved' : 'na2-student-chip-not-checked',
                    'na2-student-chip-selected'
                  ]"
                >
                  <q-icon
                    size="16px"
                    class="q-mr-xs"
                    :name="props.opt.label.startsWith('__SAVED__|') ? 'check_box' : 'check_box_outline_blank'"
                    :color="props.opt.label.startsWith('__SAVED__|') ? 'positive' : 'warning'"
                  />
                  {{ props.opt.label.split('|').slice(1).join('|') }}
                </q-chip>
                """,
            )

            today = datetime.now().strftime("%m/%d/%Y")
            self.date_input = ui.input(label="Date", value=today).props("readonly").classes("na2-control")
            with ui.menu().props("no-parent-event") as date_menu:
                ui.date(value=today).props("mask=MM/DD/YYYY").bind_value(self.date_input)
            with self.date_input.add_slot("append"):
                ui.icon("calendar_month").classes("cursor-pointer").on("click", date_menu.open)
            self.date_input.on("change", self._on_date_change)

            self.sticky_choices_switch = ui.switch(
                "Sticky last choices",
                value=False,
                on_change=self._on_sticky_toggle,
            ).classes("na2-sticky-toggle")

    def _build_global_actions(self) -> None:
        with ui.row().classes("na2-actions-row"):
            self.save_all_button = ui.button(
                "Save Selected",
                on_click=self._save_selected_students,
            ).classes("na2-btn na2-btn-primary")
            self.undo_button = ui.button(
                "Undo Last Save",
                on_click=self._undo_last_saved,
            ).classes("na2-btn na2-btn-secondary")
            self.filter_toggle_button = ui.button(
                "Not Checked Only",
                on_click=self._toggle_not_checked_filter,
            ).classes("na2-btn na2-btn-secondary na2-filter-toggle-btn")

    def _build_summary_strip(self) -> None:
        with ui.row().classes("na2-summary-strip"):
            with ui.column().classes("na2-summary-chip"):
                ui.label("Selected").classes("na2-summary-title")
                self.group_summary_label = ui.label(f"Selected 0 of {MAX_SELECTED_STUDENTS}").classes("na2-summary-value")
            with ui.column().classes("na2-summary-chip"):
                ui.label("Unchecked").classes("na2-summary-title")
                self.progress_summary_label = ui.label("Unchecked 0 of 0").classes("na2-summary-value")
            with ui.column().classes("na2-summary-chip"):
                ui.label("Cards").classes("na2-summary-title")
                self.card_summary_label = ui.label("Saved: 0 | Draft: 0 | Not saved: 0").classes("na2-summary-value")
            with ui.column().classes("na2-summary-chip na2-summary-status"):
                ui.label("Status").classes("na2-summary-title")
                self.status_label = ui.label(self.status_message).classes("na2-status-text")

    def _initialize_selectors(self) -> None:
        assert self.grade_select is not None
        assert self.student_select is not None
        assert self.date_input is not None

        self._syncing = True
        try:
            self.grade_select.options = self._grade_options()
            self.grade_select.value = next(iter(self.grade_select.options), None)
            self.grade_select.update()

            self.student_select.value = []
            self.student_select.update()

            self.date_input.value = datetime.now().strftime("%m/%d/%Y")
            self.date_input.update()

            self._refresh_period_options()
            self._reload_saved_keys_for_date()
            self._refresh_student_options(reset_selection=True)
            self._apply_preferences_if_enabled()
        finally:
            self._syncing = False

    def _apply_preferences_if_enabled(self) -> None:
        assert self.sticky_choices_switch is not None
        assert self.grade_select is not None
        assert self.period_select is not None
        assert self.student_select is not None
        assert self.date_input is not None

        prefs = self._load_preferences()
        sticky_enabled = bool(prefs.get("sticky_enabled", False))
        self.sticky_choices_switch.value = sticky_enabled
        self.sticky_choices_switch.update()

        if not sticky_enabled:
            return

        saved_grade = str(prefs.get("grade", "")).strip()
        if saved_grade and saved_grade in self.grade_select.options:
            self.grade_select.value = saved_grade
            self.grade_select.update()

        self._refresh_period_options()

        saved_period = str(prefs.get("period", "")).strip()
        if saved_period and saved_period in self.period_select.options:
            self.period_select.value = saved_period
            self.period_select.update()

        self._reload_saved_keys_for_date()
        self._refresh_student_options(reset_selection=True)

        saved_date = self._normalized_check_date(str(prefs.get("check_date", "")))
        if saved_date:
            self.date_input.value = saved_date
            self.date_input.update()
            self._reload_saved_keys_for_date()
            self._refresh_student_options(reset_selection=True)

    def _on_grade_change(self, _event: ValueChangeEventArguments) -> None:
        if self._syncing:
            return
        self._refresh_period_options()
        self._reload_saved_keys_for_date()
        self._refresh_student_options(reset_selection=True)
        self._render_batch_cards()
        self._refresh_summary_strip()
        self._persist_preferences()

    def _on_period_change(self, _event: ValueChangeEventArguments) -> None:
        if self._syncing:
            return
        self._reload_saved_keys_for_date()
        self._refresh_student_options(reset_selection=True)
        self._render_batch_cards()
        self._refresh_summary_strip()
        self._persist_preferences()

    def _on_student_selection_change(self, _event: ValueChangeEventArguments) -> None:
        if self._syncing:
            return
        self._apply_selected_student_values(self.student_select.value if self.student_select else [])
        self._render_batch_cards()
        self._refresh_summary_strip()
        self._persist_preferences()

    def _on_date_change(self, _event: ValueChangeEventArguments) -> None:
        if self._syncing:
            return
        normalized = self._normalized_check_date(self.date_input.value if self.date_input else None)
        if normalized is None:
            self.status_message = "Date must use MM/DD/YYYY."
            if self.status_label is not None:
                self.status_label.set_text(self.status_message)
            ui.notify(self.status_message, type="warning")
            return
        assert self.date_input is not None
        self.date_input.value = normalized
        self.date_input.update()
        self._reload_saved_keys_for_date()
        self._refresh_student_options(reset_selection=True)
        self._render_batch_cards()
        self._refresh_summary_strip()
        self._persist_preferences()

    def _on_sticky_toggle(self, _event: ValueChangeEventArguments) -> None:
        if self._syncing:
            return
        self._persist_preferences()

    def _grade_options(self) -> dict[str, str]:
        grades = sorted({student.grade for student in self.roster}, key=self._sort_key)
        return {grade: f"Grade {grade}" if grade.isdigit() else grade for grade in grades}

    def _period_options(self, grade: str | None) -> dict[str, str]:
        if not grade:
            return {}
        periods = sorted({student.period for student in self.roster if student.grade == grade}, key=self._sort_key)
        return {period: period for period in periods}

    def _refresh_period_options(self) -> None:
        assert self.grade_select is not None
        assert self.period_select is not None

        selected_grade = str(self.grade_select.value) if self.grade_select.value is not None else None
        options = self._period_options(selected_grade)
        self.period_select.options = options
        if self.period_select.value not in options:
            self.period_select.value = next(iter(options), None)
        self.period_select.update()

    def _refresh_student_options(self, *, reset_selection: bool, notify_pruned: bool = False) -> None:
        assert self.grade_select is not None
        assert self.period_select is not None
        assert self.student_select is not None

        grade = str(self.grade_select.value) if self.grade_select.value is not None else ""
        period = str(self.period_select.value) if self.period_select.value is not None else ""
        self.filtered_students = [
            student for student in self.roster if student.grade == grade and student.period == period
        ]

        available_students = self._available_students_for_picker()
        options = {student.student_id: self._student_option_label(student) for student in available_students}

        previous_selection = list(self.selected_student_ids)
        new_selection: list[str]
        if reset_selection:
            new_selection = []
        else:
            new_selection = [student_id for student_id in previous_selection if student_id in options]

        self.student_select.options = options
        self.student_select.update()
        self._apply_selected_student_values(new_selection)

        if notify_pruned and len(new_selection) < len(previous_selection):
            removed = len(previous_selection) - len(new_selection)
            ui.notify(f"Hidden {removed} saved student(s) while Not Checked filter is on.", type="warning")

    def _render_batch_cards(self) -> None:
        if self.batch_grid is None:
            return

        students = self._current_selected_students()

        self.batch_grid.clear()
        cols = max(1, min(len(students), MAX_SELECTED_STUDENTS))
        self.batch_grid.classes(replace=f"na2-batch-grid na2-cols-{cols}")
        self.card_handles_by_student_id = {}

        with self.batch_grid:
            if not students:
                self._build_empty_selection_card()
            else:
                for student in students:
                    self._build_student_card(student)

        for student in students:
            self._refresh_card(student.student_id)

    def _build_empty_selection_card(self) -> None:
        with ui.card().classes("na2-student-card na2-empty-card"):
            ui.label("No students selected").classes("na2-empty-title")
            ui.label(f"Select up to {MAX_SELECTED_STUDENTS} students to start grading.").classes("na2-empty-subtitle")

    def _build_student_card(self, student: RosterStudent) -> None:
        default_form = self._ensure_draft(student.student_id)
        scores = score_form(default_form)

        with ui.card().classes("na2-student-card") as root:
            with ui.row().classes("na2-card-header"):
                with ui.column().classes("na2-card-title-wrap"):
                    ui.label(student.student_name).classes("na2-card-name")
                    ui.label(student.student_id).classes("na2-card-id")
                with ui.row().classes("na2-card-header-actions"):
                    status_chip = ui.chip("Not saved", selectable=False).classes("na2-card-status na2-status-not-saved")
                    next_ungraded_button = ui.button(
                        "Next Ungraded",
                        on_click=lambda sid=student.student_id: self._select_next_not_checked(sid),
                    ).props("dense no-caps").classes("na2-btn na2-btn-secondary na2-filter-toggle-btn")

            lock_hint = ui.label("").classes("na2-lock-hint")

            with ui.element("div").classes("na2-sections-stack"):
                with ui.element("div").classes("na2-section"):
                    ui.label("Agenda").classes("na2-section-title")
                    with ui.row().classes("na2-control-row"):
                        ui.label("Present").classes("na2-control-label")
                        agenda_present = ui.toggle(
                            options={"yes": "Present", "no": "Not present"},
                            value="yes" if default_form.agenda_present else "no",
                            on_change=lambda e, sid=student.student_id: self._update_draft(
                                sid,
                                lambda f, v=(str(e.value) == "yes"): setattr(f, "agenda_present", v),
                            ),
                        ).classes("na2-toggle na2-toggle-compact")
                    with ui.row().classes("na2-control-row"):
                        ui.label("Filled today").classes("na2-control-label")
                        agenda_entry = ui.toggle(
                            options={"complete": "Complete", "partial": "Partial", "blank": "Blank"},
                            value=default_form.agenda_entry_status,
                            on_change=lambda e, sid=student.student_id: self._update_draft(
                                sid,
                                lambda f, v=str(e.value): setattr(f, "agenda_entry_status", v),
                            ),
                        ).classes("na2-toggle na2-toggle-compact")
                    with ui.row().classes("na2-control-row"):
                        ui.label("Legible").classes("na2-control-label")
                        agenda_legible = ui.toggle(
                            options={"yes": "Legible", "no": "Not legible"},
                            value="yes" if default_form.agenda_legible else "no",
                            on_change=lambda e, sid=student.student_id: self._update_draft(
                                sid,
                                lambda f, v=(str(e.value) == "yes"): setattr(f, "agenda_legible", v),
                            ),
                        ).classes("na2-toggle na2-toggle-compact")
                    with ui.row().classes("na2-section-score-row"):
                        ui.label("Section score").classes("na2-section-score-label")
                        agenda_score = ui.label(f"{scores.agenda_score:.1f} / 10").classes("na2-section-score-value")

                with ui.element("div").classes("na2-section"):
                    ui.label("Notebook").classes("na2-section-title")
                    with ui.row().classes("na2-control-row"):
                        ui.label("Present").classes("na2-control-label")
                        notebook_present = ui.toggle(
                            options={"yes": "Present", "no": "Not present"},
                            value="yes" if default_form.nb_present else "no",
                            on_change=lambda e, sid=student.student_id: self._update_draft(
                                sid,
                                lambda f, v=(str(e.value) == "yes"): setattr(f, "nb_present", v),
                            ),
                        ).classes("na2-toggle na2-toggle-compact")
                    with ui.row().classes("na2-control-row"):
                        ui.label("Date").classes("na2-control-label")
                        notebook_date = ui.toggle(
                            options={"full": "Correct", "partial": "Unclear", "none": "Missing"},
                            value=default_form.nb_date_status,
                            on_change=lambda e, sid=student.student_id: self._update_draft(
                                sid,
                                lambda f, v=str(e.value): setattr(f, "nb_date_status", v),
                            ),
                        ).classes("na2-toggle na2-toggle-compact")
                    with ui.row().classes("na2-control-row"):
                        ui.label("Title").classes("na2-control-label")
                        notebook_title = ui.toggle(
                            options={"full": "Accurate", "partial": "Vague", "none": "Missing"},
                            value=default_form.nb_title_status,
                            on_change=lambda e, sid=student.student_id: self._update_draft(
                                sid,
                                lambda f, v=str(e.value): setattr(f, "nb_title_status", v),
                            ),
                        ).classes("na2-toggle na2-toggle-compact")
                    with ui.row().classes("na2-control-row"):
                        ui.label("Academic notes").classes("na2-control-label")
                        notebook_notes = ui.toggle(
                            options={"complete": "Detailed", "partial": "Basic", "missing": "Minimal"},
                            value=default_form.nb_notes_status,
                            on_change=lambda e, sid=student.student_id: self._update_draft(
                                sid,
                                lambda f, v=str(e.value): setattr(f, "nb_notes_status", v),
                            ),
                        ).classes("na2-toggle na2-toggle-compact")
                    with ui.row().classes("na2-control-row"):
                        ui.label("Organization").classes("na2-control-label")
                        notebook_organized = ui.toggle(
                            options={"full": "Structured", "partial": "Inconsistent", "none": "Disorganized"},
                            value=default_form.nb_organization_status,
                            on_change=lambda e, sid=student.student_id: self._update_draft(
                                sid,
                                lambda f, v=str(e.value): setattr(f, "nb_organization_status", v),
                            ),
                        ).classes("na2-toggle na2-toggle-compact")
                    with ui.row().classes("na2-control-row"):
                        ui.label("Legibility & effort").classes("na2-control-label")
                        notebook_legible = ui.toggle(
                            options={"full": "Neat", "partial": "Readable", "none": "Difficult"},
                            value=default_form.nb_legibility_status,
                            on_change=lambda e, sid=student.student_id: self._update_draft(
                                sid,
                                lambda f, v=str(e.value): setattr(f, "nb_legibility_status", v),
                            ),
                        ).classes("na2-toggle na2-toggle-compact")
                    with ui.row().classes("na2-section-score-row"):
                        ui.label("Section score").classes("na2-section-score-label")
                        notebook_score = ui.label(f"{scores.notebook_score:.1f} / 10").classes("na2-section-score-value")

                with ui.element("div").classes("na2-section"):
                    ui.label("Status").classes("na2-section-title")
                    with ui.row().classes("na2-control-row"):
                        ui.label("Auto flag").classes("na2-control-label")
                        auto_flag_chip = ui.chip(scores.auto_flag, selectable=False).classes("na2-flag-chip")
                    with ui.row().classes("na2-control-row"):
                        ui.label("Deduction").classes("na2-control-label")
                        deduction_label = ui.label(f"-{scores.comment_deduction:.2f}").classes("na2-deduction")
                    with ui.row().classes("na2-section-score-row"):
                        ui.label("Section score").classes("na2-section-score-label")
                        status_score = ui.label(f"{scores.status_score:.2f}").classes("na2-section-score-value")

            with ui.row().classes("na2-total-row"):
                with ui.column().classes("na2-total-chip"):
                    ui.label("Total /20").classes("na2-total-label")
                    total_score = ui.label(f"{scores.total_score:.2f}").classes("na2-total-value")
                with ui.column().classes("na2-total-chip na2-total-chip-primary"):
                    ui.label("Gradebook /10").classes("na2-total-label")
                    gradebook_score = ui.label(f"{scores.gradebook_score:.2f}").classes("na2-total-value")
                save_button = ui.button(
                    "Save Student",
                    on_click=lambda sid=student.student_id: self._save_student(sid),
                ).classes("na2-btn na2-btn-secondary na2-card-save-btn")

            with ui.row().classes("na2-comment-footer"):
                tags_summary = ui.label("Tags: none").classes("na2-comment-summary")
                comment_summary = ui.label("Comment: None").classes("na2-comment-summary")
                chevron_icon = ui.icon("expand_more").classes("na2-chevron cursor-pointer").on(
                    "click",
                    lambda _event, sid=student.student_id: self._toggle_comments(sid),
                )

            with ui.element("div").classes("na2-comment-panel") as comments_panel:
                tags_select = ui.select(
                    options={tag.tag: tag.label for tag in TAG_DEFINITIONS},
                    value=list(default_form.tags),
                    multiple=True,
                    label="Tags",
                    on_change=lambda e, sid=student.student_id: self._update_draft(
                        sid,
                        lambda f, v=(list(e.value) if isinstance(e.value, list) else []): setattr(
                            f,
                            "tags",
                            [str(item) for item in v],
                        ),
                    ),
                ).classes("na2-control")
                tags_select.props("use-chips use-input input-debounce=0")

                ui.label("Comment presets").classes("na2-preset-label")
                comment_checks: dict[str, ui.checkbox] = {}
                for preset in COMMENT_PRESETS:
                    checkbox = ui.checkbox(
                        preset,
                        value=preset in default_form.comment_checks,
                        on_change=lambda _e, sid=student.student_id: self._sync_comment_checks_from_controls(sid),
                    ).classes("na2-checkbox")
                    comment_checks[preset] = checkbox

                comment_textarea = ui.textarea(
                    label="Comment text",
                    value=default_form.comment_text,
                    placeholder="Optional note...",
                    on_change=lambda e, sid=student.student_id: self._update_draft(
                        sid,
                        lambda f, v=str(e.value or ""): setattr(f, "comment_text", v),
                    ),
                ).classes("na2-comment-input")

        self.card_handles_by_student_id[student.student_id] = StudentCardHandles(
            student=student,
            root=root,
            status_chip=status_chip,
            next_ungraded_button=next_ungraded_button,
            lock_hint=lock_hint,
            agenda_present=agenda_present,
            agenda_entry=agenda_entry,
            agenda_legible=agenda_legible,
            notebook_present=notebook_present,
            notebook_date=notebook_date,
            notebook_title=notebook_title,
            notebook_notes=notebook_notes,
            notebook_organized=notebook_organized,
            notebook_legible=notebook_legible,
            agenda_score=agenda_score,
            notebook_score=notebook_score,
            status_score=status_score,
            total_score=total_score,
            gradebook_score=gradebook_score,
            deduction_label=deduction_label,
            auto_flag_chip=auto_flag_chip,
            tags_select=tags_select,
            comment_checks=comment_checks,
            comment_textarea=comment_textarea,
            tags_summary=tags_summary,
            comment_summary=comment_summary,
            comments_panel=comments_panel,
            chevron_icon=chevron_icon,
            save_button=save_button,
        )

    def _update_draft(self, student_id: str, mutator) -> None:
        if self._syncing:
            return
        key = self._draft_key(student_id)
        draft = deepcopy(self._ensure_draft(student_id))
        mutator(draft)
        self.draft_state_by_key[key] = draft
        self._refresh_card(student_id)
        self._refresh_summary_strip()

    def _sync_comment_checks_from_controls(self, student_id: str) -> None:
        if self._syncing:
            return
        card = self.card_handles_by_student_id.get(student_id)
        if card is None:
            return
        selected = [preset for preset, checkbox in card.comment_checks.items() if bool(checkbox.value)]
        self._update_draft(student_id, lambda f, values=selected: setattr(f, "comment_checks", values))

    def _toggle_comments(self, student_id: str) -> None:
        key = self._draft_key(student_id)
        if key in self.expanded_keys:
            self.expanded_keys.remove(key)
        else:
            self.expanded_keys.add(key)
        self._refresh_card(student_id)

    def _refresh_card(self, student_id: str) -> None:
        card = self.card_handles_by_student_id.get(student_id)
        if card is None:
            return

        key = self._draft_key(student_id)
        draft = apply_auto_rules(self._ensure_draft(student_id))
        self.draft_state_by_key[key] = deepcopy(draft)

        scores = score_form(draft)
        is_saved = key in self.saved_keys
        is_draft = draft != default_form_state()

        status_text = "Saved" if is_saved else ("Draft" if is_draft else "Not saved")
        status_class = "na2-status-saved" if is_saved else ("na2-status-draft" if is_draft else "na2-status-not-saved")
        if is_saved:
            card_class = "na2-student-card na2-card-saved"
        elif is_draft:
            card_class = "na2-student-card"
        else:
            card_class = "na2-student-card na2-card-pending"

        expanded = key in self.expanded_keys

        self._syncing = True
        try:
            card.root.classes(replace=card_class)
            card.status_chip.set_text(status_text)
            card.status_chip.classes(replace=f"na2-card-status {status_class}")
            card.next_ungraded_button.set_text("Next Ungraded")
            card.next_ungraded_button.classes(replace="na2-btn na2-btn-secondary na2-filter-toggle-btn")

            card.agenda_present.value = "yes" if draft.agenda_present else "no"
            card.agenda_present.update()
            card.agenda_entry.value = draft.agenda_entry_status
            card.agenda_entry.update()
            card.agenda_legible.value = "yes" if draft.agenda_legible else "no"
            card.agenda_legible.update()

            card.notebook_present.value = "yes" if draft.nb_present else "no"
            card.notebook_present.update()
            card.notebook_date.value = draft.nb_date_status
            card.notebook_date.update()
            card.notebook_title.value = draft.nb_title_status
            card.notebook_title.update()
            card.notebook_notes.value = draft.nb_notes_status
            card.notebook_notes.update()
            card.notebook_organized.value = draft.nb_organization_status
            card.notebook_organized.update()
            card.notebook_legible.value = draft.nb_legibility_status
            card.notebook_legible.update()

            card.tags_select.value = list(draft.tags)
            card.tags_select.update()
            for preset, checkbox in card.comment_checks.items():
                checkbox.value = preset in draft.comment_checks
                checkbox.update()
            card.comment_textarea.value = draft.comment_text
            card.comment_textarea.update()

            card.agenda_score.set_text(f"{scores.agenda_score:.1f} / 10")
            card.notebook_score.set_text(f"{scores.notebook_score:.1f} / 10")
            card.status_score.set_text(f"{scores.status_score:.2f}")
            card.total_score.set_text(f"{scores.total_score:.2f}")
            card.gradebook_score.set_text(f"{scores.gradebook_score:.2f}")
            card.deduction_label.set_text(f"-{scores.comment_deduction:.2f}")
            card.auto_flag_chip.set_text(scores.auto_flag)
            card.auto_flag_chip.classes(replace=f"na2-flag-chip {self._flag_class(scores.auto_flag)}")

            card.tags_summary.set_text(self._tags_summary_text(draft.tags))
            card.comment_summary.set_text(self._comment_summary_text(draft.comment_checks, draft.comment_text))

            if expanded:
                card.comments_panel.classes(add="na2-comment-panel-open")
                card.chevron_icon.classes(replace="na2-chevron na2-chevron-open cursor-pointer")
            else:
                card.comments_panel.classes(remove="na2-comment-panel-open")
                card.chevron_icon.classes(replace="na2-chevron cursor-pointer")

            agenda_details_enabled = (not is_saved) and draft.agenda_present
            notebook_controls_enabled = (not is_saved) and draft.nb_present

            self._set_enabled(card.agenda_present, not is_saved)
            self._set_enabled(card.agenda_entry, agenda_details_enabled)
            self._set_enabled(card.agenda_legible, agenda_details_enabled)
            self._set_enabled(card.notebook_present, not is_saved)
            self._set_enabled(card.notebook_date, notebook_controls_enabled)
            self._set_enabled(card.notebook_title, notebook_controls_enabled)
            self._set_enabled(card.notebook_notes, notebook_controls_enabled)
            self._set_enabled(card.notebook_organized, notebook_controls_enabled)
            self._set_enabled(card.notebook_legible, notebook_controls_enabled)
            self._set_enabled(card.tags_select, not is_saved)
            for checkbox in card.comment_checks.values():
                self._set_enabled(checkbox, not is_saved)
            self._set_enabled(card.comment_textarea, not is_saved)
            self._set_enabled(card.save_button, not is_saved)

            if is_saved:
                card.lock_hint.set_text("Already saved for this date. Card is locked.")
            else:
                card.lock_hint.set_text("")
        finally:
            self._syncing = False

    def _save_student(self, student_id: str) -> None:
        student = self._find_student(student_id)
        if student is None:
            return
        self._save_students([student])

    def _save_selected_students(self) -> None:
        students = self._current_selected_students()
        self._save_students(students)

    def _save_students(self, students: list[RosterStudent]) -> None:
        if not students:
            message = "No selected students."
            self.status_message = message
            self._refresh_summary_strip()
            ui.notify(message, type="warning")
            return

        check_date = self._normalized_check_date(self.date_input.value if self.date_input else None)
        if check_date is None:
            message = "Date must use MM/DD/YYYY before saving."
            self.status_message = message
            self._refresh_summary_strip()
            ui.notify(message, type="negative")
            return

        grade = str(self.grade_select.value) if self.grade_select and self.grade_select.value is not None else ""
        period = str(self.period_select.value) if self.period_select and self.period_select.value is not None else ""

        rows_to_save: list[dict[str, object]] = []
        snapshots: list[SaveSnapshot] = []
        skipped: list[str] = []

        for student in students:
            key = self._draft_key(student.student_id, check_date)
            if key in self.saved_keys:
                skipped.append(f"{student.student_name}: already saved for {check_date}")
                continue

            draft = apply_auto_rules(deepcopy(self._ensure_draft(student.student_id)))
            scores = score_form(draft)

            entry_written = draft.agenda_present and draft.agenda_entry_status != "blank"
            all_subjects_filled = draft.agenda_present and draft.agenda_entry_status == "complete"
            organized = (
                draft.agenda_legible
                and draft.nb_organization_status != "none"
                and draft.nb_legibility_status != "none"
            )
            comment_tags = "|".join(tag for tag in draft.tags if tag in TAG_LABEL_BY_KEY)

            comments = draft.comment_text.strip()
            if draft.comment_checks:
                presets_text = "; ".join(draft.comment_checks)
                comments = f"{presets_text} | {comments}" if comments else presets_text

            rows_to_save.append(
                {
                    "StudentID": student.student_id,
                    "StudentName": student.student_name,
                    "Grade": grade,
                    "Period": period,
                    "Date": check_date,
                    "Checker": TEACHER_LABEL,
                    "NotebookScore": scores.notebook_score,
                    "AgendaPresent": draft.agenda_present,
                    "EntryWritten": entry_written,
                    "AllSubjectsFilled": all_subjects_filled,
                    "Organized": organized,
                    "AgendaScore": scores.agenda_score,
                    "GradebookScore": scores.gradebook_score,
                    "Flag": scores.auto_flag,
                    "AgendaFilledToday": draft.agenda_entry_status,
                    "AgendaReadable": draft.agenda_legible,
                    "NotebookPresentDetail": draft.nb_present,
                    "NotebookWorkToday": draft.nb_notes_status,
                    "NotebookOrganized": draft.nb_organization_status != "none",
                    "CommentTags": comment_tags,
                    "CommentDeduction": scores.comment_deduction,
                    "InternalScore": scores.total_score,
                    "ScoreModel": SCORE_MODEL_INTERNAL20_GRADEBOOK10_V1,
                    "Comments": comments,
                    "CheckMode": "both",
                }
            )
            snapshots.append(SaveSnapshot(key=key, student=student, form=deepcopy(draft)))

        if rows_to_save:
            self.store.append_rows(rows_to_save)
            for snapshot in snapshots:
                self.saved_keys.add(snapshot.key)
                self.draft_state_by_key.pop(snapshot.key, None)
                self.expanded_keys.discard(snapshot.key)
            self.save_transactions.append(SaveTransaction(entries=snapshots))

        if rows_to_save and not skipped:
            message = f"Saved {len(rows_to_save)} student(s)."
            self.status_message = message
            ui.notify(message, type="positive")
        elif rows_to_save and skipped:
            skipped_text = " | ".join(skipped)
            message = f"Saved {len(rows_to_save)} student(s). Skipped: {skipped_text}"
            self.status_message = message
            ui.notify(message, type="warning")
        else:
            skipped_text = " | ".join(skipped) if skipped else "No eligible students to save."
            message = f"No students saved. {skipped_text}"
            self.status_message = message
            ui.notify(message, type="warning")

        self._refresh_student_options(reset_selection=False, notify_pruned=self.show_not_checked_only)
        self._render_batch_cards()
        self._refresh_summary_strip()
        self._persist_preferences()

    def _undo_last_saved(self) -> None:
        if not self.save_transactions:
            message = "No save transaction to undo."
            self.status_message = message
            self._refresh_summary_strip()
            ui.notify(message, type="warning")
            return

        transaction = self.save_transactions.pop()
        requested = len(transaction.entries)
        removed = self.store.undo_last_saved_rows(requested)

        if removed <= 0:
            self.save_transactions.append(transaction)
            message = "Unable to undo the last save transaction."
            self.status_message = message
            self._refresh_summary_strip()
            ui.notify(message, type="negative")
            return

        removed_entries = transaction.entries[-removed:]
        for snapshot in removed_entries:
            self.saved_keys.discard(snapshot.key)
            self.draft_state_by_key[snapshot.key] = deepcopy(snapshot.form)

        if removed < requested:
            remaining_entries = transaction.entries[: requested - removed]
            if remaining_entries:
                self.save_transactions.append(SaveTransaction(entries=remaining_entries))
            message = "Partially undid the last save transaction."
            ui.notify(message, type="warning")
        else:
            message = "Undid the last save transaction."
            ui.notify(message, type="positive")

        self.status_message = message
        self._refresh_student_options(reset_selection=False, notify_pruned=self.show_not_checked_only)
        self._render_batch_cards()
        self._refresh_summary_strip()
        self._persist_preferences()

    def _toggle_not_checked_filter(self) -> None:
        self.show_not_checked_only = not self.show_not_checked_only
        if self.show_not_checked_only:
            self.status_message = "Showing only not-checked students."
        else:
            self.status_message = "Showing all students."
        self._refresh_student_options(reset_selection=False, notify_pruned=True)
        self._render_batch_cards()
        self._refresh_summary_strip()
        self._persist_preferences()

    def _select_next_not_checked(self, clicked_student_id: str) -> None:
        index_by_student_id = {student.student_id: index for index, student in enumerate(self.filtered_students)}
        unchecked_ids = [
            student.student_id
            for student in self.filtered_students
            if self._draft_key(student.student_id) not in self.saved_keys
        ]
        if not unchecked_ids:
            self.status_message = "All students checked for this date."
            self._refresh_summary_strip()
            ui.notify(self.status_message, type="positive")
            self._persist_preferences()
            return

        if clicked_student_id not in self.selected_student_ids or clicked_student_id not in index_by_student_id:
            self.status_message = "Selected card is no longer available."
            self._refresh_summary_strip()
            ui.notify(self.status_message, type="warning")
            self._persist_preferences()
            return

        anchor = index_by_student_id[clicked_student_id]
        blocked_ids = set(self.selected_student_ids)
        blocked_ids.discard(clicked_student_id)

        replacement_id = next(
            (
                student_id
                for student_id in unchecked_ids
                if index_by_student_id[student_id] > anchor and student_id not in blocked_ids
            ),
            None,
        )

        if replacement_id is None:
            self.status_message = "No later unchecked student available."
            self._refresh_summary_strip()
            ui.notify(self.status_message, type="warning")
            self._persist_preferences()
            return

        updated_ids = list(self.selected_student_ids)
        clicked_index = updated_ids.index(clicked_student_id)
        updated_ids[clicked_index] = replacement_id
        self._apply_selected_student_values(updated_ids)
        self.status_message = "Moved to next unchecked student."
        self._render_batch_cards()
        self._refresh_summary_strip()
        self._persist_preferences()

    def _refresh_filter_toggle_button(self) -> None:
        if self.filter_toggle_button is None:
            return
        self.filter_toggle_button.set_text("Show All" if self.show_not_checked_only else "Not Checked Only")
        self.filter_toggle_button.classes(
            replace=(
                "na2-btn na2-btn-secondary na2-filter-toggle-btn na2-filter-toggle-active"
                if self.show_not_checked_only
                else "na2-btn na2-btn-secondary na2-filter-toggle-btn"
            )
        )

    def _refresh_summary_strip(self) -> None:
        if not all(
            [
                self.group_summary_label,
                self.progress_summary_label,
                self.card_summary_label,
                self.status_label,
            ]
        ):
            return

        total_students = len(self.filtered_students)
        unchecked_students = [
            student for student in self.filtered_students if self._draft_key(student.student_id) not in self.saved_keys
        ]
        students = self._current_selected_students()
        saved_count = 0
        draft_count = 0
        not_saved_count = 0

        for student in students:
            key = self._draft_key(student.student_id)
            form = apply_auto_rules(self._ensure_draft(student.student_id))
            if key in self.saved_keys:
                saved_count += 1
            elif form != default_form_state():
                draft_count += 1
            else:
                not_saved_count += 1

        self.group_summary_label.set_text(f"Selected {len(students)} of {MAX_SELECTED_STUDENTS}")
        self.progress_summary_label.set_text(f"Unchecked {len(unchecked_students)} of {total_students}")
        self.card_summary_label.set_text(
            f"Saved: {saved_count} | Draft: {draft_count} | Not saved: {not_saved_count}"
        )
        self.status_label.set_text(self.status_message)
        self._refresh_filter_toggle_button()

        if self.save_all_button is not None:
            self._set_enabled(self.save_all_button, bool(students))
        if self.filter_toggle_button is not None:
            self._set_enabled(self.filter_toggle_button, bool(self.filtered_students))
        if self.undo_button is not None:
            self._set_enabled(self.undo_button, bool(self.save_transactions))

    def _current_selected_students(self) -> list[RosterStudent]:
        by_id = {student.student_id: student for student in self.filtered_students}
        return [by_id[student_id] for student_id in self.selected_student_ids if student_id in by_id]

    def _ensure_draft(self, student_id: str) -> CheckFormState:
        key = self._draft_key(student_id)
        if key not in self.draft_state_by_key:
            self.draft_state_by_key[key] = default_form_state()
        return self.draft_state_by_key[key]

    def _draft_key(self, student_id: str, check_date: str | None = None) -> tuple[str, str]:
        date_value = check_date if check_date is not None else self._normalized_check_date(
            self.date_input.value if self.date_input else None
        )
        if not date_value:
            date_value = datetime.now().strftime("%m/%d/%Y")
        return student_id, date_value

    def _find_student(self, student_id: str) -> RosterStudent | None:
        for student in self.filtered_students:
            if student.student_id == student_id:
                return student
        return None

    def _reload_saved_keys_for_date(self) -> None:
        check_date = self._normalized_check_date(self.date_input.value if self.date_input else None)
        self.saved_keys = set()
        if check_date is None:
            return
        for record in self.store.list_saved_refs():
            if record.check_date == check_date:
                self.saved_keys.add((record.student_id, record.check_date))

    def _available_students_for_picker(self) -> list[RosterStudent]:
        if not self.show_not_checked_only:
            return list(self.filtered_students)
        return [student for student in self.filtered_students if self._draft_key(student.student_id) not in self.saved_keys]

    def _student_option_label(self, student: RosterStudent) -> str:
        prefix = SAVED_OPTION_PREFIX if self._draft_key(student.student_id) in self.saved_keys else TODO_OPTION_PREFIX
        return f"{prefix}{student.student_name} ({student.student_id})"

    def _apply_selected_student_values(self, raw_values: object) -> None:
        assert self.student_select is not None

        available_ids = list(self.student_select.options.keys())
        incoming: list[str]
        if isinstance(raw_values, list):
            incoming = [str(value) for value in raw_values]
        elif raw_values is None:
            incoming = []
        else:
            incoming = [str(raw_values)]

        deduped: list[str] = []
        for student_id in incoming:
            if student_id in available_ids and student_id not in deduped:
                deduped.append(student_id)

        trimmed = deduped[:MAX_SELECTED_STUDENTS]
        if len(deduped) > MAX_SELECTED_STUDENTS:
            ui.notify(f"You can select up to {MAX_SELECTED_STUDENTS} students.", type="warning")

        self.selected_student_ids = trimmed
        self._syncing = True
        try:
            self.student_select.value = list(trimmed)
            self.student_select.update()
        finally:
            self._syncing = False

    def _tags_summary_text(self, selected_tags: list[str]) -> str:
        if not selected_tags:
            return "Tags: none"
        labels = [TAG_LABEL_BY_KEY.get(tag, tag) for tag in selected_tags]
        return f"Tags: {', '.join(labels[:3])}" + ("..." if len(labels) > 3 else "")

    def _comment_summary_text(self, comment_checks: list[str], comment_text: str) -> str:
        text = comment_text.strip()
        if not text and comment_checks:
            text = "; ".join(comment_checks)
        if not text:
            return "Comment: None"
        snippet = text[:40]
        if len(text) > 40:
            snippet += "..."
        return f"Comment: {snippet}"

    def _flag_class(self, flag: str) -> str:
        lowered = flag.lower()
        if "missing" in lowered:
            return "na2-flag-critical"
        if "blank" in lowered or "incomplete" in lowered or "messy" in lowered:
            return "na2-flag-warning"
        return "na2-flag-neutral"

    def _normalized_check_date(self, raw_value: str | None) -> str | None:
        value = str(raw_value or "").strip()
        if not value:
            return None
        for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
            try:
                parsed = datetime.strptime(value, fmt)
                return parsed.strftime("%m/%d/%Y")
            except ValueError:
                continue
        return None

    def _set_enabled(self, control: ui.element, enabled: bool) -> None:
        if enabled:
            control.enable()
        else:
            control.disable()

    def _sort_key(self, value: str) -> tuple[int, str]:
        if value.isdigit():
            return (0, f"{int(value):06d}")
        return (1, value.lower())

    def _load_preferences(self) -> dict[str, object]:
        if not self.preferences_file.exists():
            return {}
        try:
            payload = json.loads(self.preferences_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        if not isinstance(payload, dict):
            return {}
        prefs = payload.get(PREFERENCES_KEY)
        if not isinstance(prefs, dict):
            return {}
        return prefs

    def _persist_preferences(self) -> None:
        if not all(
            [
                self.sticky_choices_switch,
                self.grade_select,
                self.period_select,
                self.student_select,
                self.date_input,
            ]
        ):
            return

        payload: dict[str, object] = {}
        if self.preferences_file.exists():
            try:
                raw = json.loads(self.preferences_file.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    payload = raw
            except (OSError, ValueError):
                payload = {}

        payload[PREFERENCES_KEY] = {
            "sticky_enabled": bool(self.sticky_choices_switch.value),
            "grade": str(self.grade_select.value or ""),
            "period": str(self.period_select.value or ""),
            "check_date": str(self.date_input.value or ""),
        }

        self.preferences_file.parent.mkdir(parents=True, exist_ok=True)
        temp_file = self.preferences_file.with_name(f"{self.preferences_file.name}.tmp")
        with temp_file.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        temp_file.replace(self.preferences_file)

    def _on_keyboard(self, event: KeyEventArguments) -> None:
        if not event.action.keydown or event.action.repeat:
            return
        key = event.key.name.lower()
        if key == "z" and event.modifiers.ctrl:
            self._undo_last_saved()


def build_na_check_dashboard() -> None:
    dashboard = NACheckDashboard()
    dashboard.build()
