from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
import time

import flet as ft

from app.constants import APP_DISPLAY_NAME, DEFAULT_OUTPUT_FILE, DEFAULT_STUDENTS_FILE, DEFAULT_UI_PREFERENCES_FILE
from app.flags import NO_ISSUE_FLAG, compute_issue_flag
from app.models import CheckRecord, SessionConfig
from app.scoring import (
    AGENDA_FILLED_BLANK,
    AGENDA_FILLED_COMPLETE,
    AGENDA_FILLED_OPTIONS,
    AGENDA_FILLED_PARTIAL,
    COMMENT_TAG_DIFFICULT_TO_READ,
    COMMENT_TAG_DISORGANIZED,
    COMMENT_TAG_EXCEEDS_EXPECTATIONS,
    COMMENT_TAG_IMPROVEMENT_SHOWN,
    COMMENT_TAG_INCOMPLETE_WORK,
    COMMENT_TAG_MEETS_EXPECTATIONS,
    COMMENT_TAG_MISSING_COMPONENTS,
    COMMENT_TAG_MISSING_DATE,
    COMMENT_TAG_STRONG_EFFORT,
    COMMENT_TAG_UNREADABLE,
    NEGATIVE_COMMENT_DEDUCTION_BY_TAG,
    NOTEBOOK_WORK_COMPLETE,
    NOTEBOOK_WORK_MISSING,
    NOTEBOOK_WORK_OPTIONS,
    NOTEBOOK_WORK_PARTIAL,
    SCORE_MODEL_INTERNAL20_GRADEBOOK10_V1,
    compute_agenda_score_v2,
    compute_comment_deduction,
    compute_internal_total,
    compute_notebook_score_v2,
)
from app.storage import (
    append_record,
    load_insights_visibility,
    load_records_with_warnings,
    remove_last_record,
    save_insights_visibility,
)
from app.students import Student, filter_students, load_students


NOTEBOOK_PRESENT_COMPONENT_POINTS = 4.0

POSITIVE_COMMENT_TAG_OPTIONS = [
    ("Exceeds expectations", COMMENT_TAG_EXCEEDS_EXPECTATIONS),
    ("Meets expectations", COMMENT_TAG_MEETS_EXPECTATIONS),
    ("Strong effort", COMMENT_TAG_STRONG_EFFORT),
    ("Improvement shown", COMMENT_TAG_IMPROVEMENT_SHOWN),
]

LEGIBILITY_COMMENT_TAG_OPTIONS = [
    ("Unreadable (-1.0)", COMMENT_TAG_UNREADABLE),
    ("Difficult to read (-0.5)", COMMENT_TAG_DIFFICULT_TO_READ),
    ("Disorganized (-0.5)", COMMENT_TAG_DISORGANIZED),
    ("Missing date (-0.25)", COMMENT_TAG_MISSING_DATE),
]

COMPLETION_COMMENT_TAG_OPTIONS = [
    ("Incomplete work (-5.0)", COMMENT_TAG_INCOMPLETE_WORK),
    ("Missing components (-5.0)", COMMENT_TAG_MISSING_COMPONENTS),
]

# Theme tokens
COLOR_BG = "#F4F6F8"
COLOR_SURFACE = "#FFFFFF"
COLOR_SURFACE_ALT = "#EEF2F6"
COLOR_TEXT = "#1F2937"
COLOR_MUTED = "#5B6470"
COLOR_PRIMARY = "#0F766E"
COLOR_PRIMARY_SOFT = "#DFF3F0"
COLOR_WARN = "#B45309"
COLOR_DANGER = "#B91C1C"

RADIUS_SM = 8
RADIUS_MD = 12
RADIUS_LG = 16

SPACE_XS = 4
SPACE_SM = 8
SPACE_MD = 12
SPACE_LG = 16
SPACE_XL = 20
SPACE_2XL = 24

WINDOW_MIN_WIDTH = 1366
WINDOW_MIN_HEIGHT = 768
COMPACT_PADDING_BREAKPOINT = 820
INSIGHTS_SIDE_BY_SIDE_BREAKPOINT = 1180
SCORING_LOCKED_OPACITY = 0.55
ACTIONS_LOCKED_OPACITY = 0.65
APP_PAGE_PADDING = SPACE_SM
APP_CONTENT_SPACING = SPACE_SM
COMPACT_CARD_PADDING = SPACE_MD
COMPACT_SECTION_SPACING = SPACE_SM
COMPACT_GROUP_SPACING = SPACE_XS
HISTORY_TABLE_HEIGHT = 190


@dataclass(frozen=True)
class RubricState:
    agenda_present: bool
    agenda_filled_today: str
    agenda_readable: bool
    notebook_present: bool
    notebook_work_today: str
    notebook_organized: bool
    agenda_score: float
    notebook_score: float
    comment_tags: list[str]
    comments: str
    comment_deduction: float
    internal_score: float
    gradebook_score: float
    entry_written: bool
    all_subjects_filled: bool
    organized: bool
    auto_flag: str


class NAFletApp:
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.page.title = APP_DISPLAY_NAME
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.bgcolor = COLOR_BG
        self.page.theme = ft.Theme(color_scheme_seed=COLOR_PRIMARY)
        self.page.padding = SPACE_LG
        self.page.window_min_width = WINDOW_MIN_WIDTH
        self.page.window_min_height = WINDOW_MIN_HEIGHT

        self.session: SessionConfig | None = None
        self.roster: list[Student] = []
        self.current_index = 0
        self.last_save_at = 0.0
        self.save_history: list[tuple[int, CheckRecord]] = []
        self.students_cache: list[Student] | None = None
        self.checker_name_by_id: dict[str, str] = {}
        self.insights_visibility_by_class: dict[str, bool] = load_insights_visibility(DEFAULT_UI_PREFERENCES_FILE)
        self.insights_visible = False
        self._pending_insights_hide = False
        self._insights_hide_generation = 0
        self._insights_hide_fallback_ms = 220
        self.student_col_container: ft.Container | None = None
        self.insights_col_container: ft.Container | None = None
        self.bottom_actions_container: ft.Container | None = None
        self.insights_panel: ft.Control | None = None
        self.insights_placeholder: ft.Control = ft.Container(height=1)
        self.insights_switcher: ft.AnimatedSwitcher | None = None
        self.scoring_lock_hint: ft.Container | None = None

        self.setup_date = ft.TextField(
            label="Date (YYYY-MM-DD)",
            value=datetime.now().strftime("%Y-%m-%d"),
            expand=True,
            dense=False,
            text_size=16,
            border_radius=RADIUS_SM,
            content_padding=ft.padding.symmetric(horizontal=12, vertical=12),
        )
        self.setup_grade = ft.Dropdown(
            label="Grade",
            expand=True,
            value=None,
            hint_text="Select grade",
            options=[ft.dropdown.Option("6"), ft.dropdown.Option("7"), ft.dropdown.Option("8")],
            on_change=self._grade_changed,
            text_size=16,
            border_radius=RADIUS_SM,
            content_padding=ft.padding.symmetric(horizontal=12, vertical=12),
        )
        self.setup_checker = ft.Dropdown(
            label="Checker (student from this class roster)",
            expand=True,
            value=None,
            options=[],
            disabled=True,
            on_change=self._checker_changed,
            text_size=16,
            border_radius=RADIUS_SM,
            content_padding=ft.padding.symmetric(horizontal=12, vertical=12),
        )
        self.setup_student_picker = ft.Dropdown(
            label="Student",
            expand=True,
            value=None,
            options=[],
            on_change=self._student_picker_changed,
            disabled=True,
            text_size=16,
            border_radius=RADIUS_SM,
            content_padding=ft.padding.symmetric(horizontal=12, vertical=12),
        )
        self.setup_paths_text = ft.Text(
            f"Roster source: {DEFAULT_STUDENTS_FILE}  |  Output CSV: {DEFAULT_OUTPUT_FILE}",
            size=12,
            color=COLOR_MUTED,
        )

        self.student_heading = ft.Text("No roster loaded", size=24, weight=ft.FontWeight.BOLD, color=COLOR_TEXT)
        self.student_progress = ft.Text(
            "0 / 0",
            color=COLOR_PRIMARY,
            weight=ft.FontWeight.W_600,
            size=13,
            text_align=ft.TextAlign.CENTER,
        )
        self.student_progress_chip = ft.Container(
            content=self.student_progress,
            bgcolor=COLOR_PRIMARY_SOFT,
            border_radius=999,
            padding=ft.padding.symmetric(horizontal=12, vertical=6),
        )
        self.status_text = ft.Text("Select grade to begin.", color=COLOR_MUTED, max_lines=2)

        self.agenda_present = ft.Checkbox(
            label="Agenda present (4 pts)",
            value=False,
            on_change=self._on_agenda_present_changed,
        )
        self.agenda_filled_today = ft.RadioGroup(
            value=AGENDA_FILLED_BLANK,
            on_change=self._refresh_scores,
            content=ft.Row(
                controls=[
                    ft.Radio(value=AGENDA_FILLED_COMPLETE, label="Complete (4 pts)"),
                    ft.Radio(value=AGENDA_FILLED_PARTIAL, label="Partial (2 pts)"),
                    ft.Radio(value=AGENDA_FILLED_BLANK, label="Blank (0 pts)"),
                ],
                wrap=True,
                spacing=SPACE_MD,
                run_spacing=SPACE_XS,
            ),
        )
        self.agenda_readable = ft.Checkbox(
            label="Agenda readable (2 pts)",
            value=False,
            on_change=self._refresh_scores,
        )
        self.notebook_present = ft.Checkbox(
            label=f"Notebook present ({int(NOTEBOOK_PRESENT_COMPONENT_POINTS)} pts)",
            value=False,
            on_change=self._on_notebook_present_changed,
        )
        self.notebook_work_today = ft.RadioGroup(
            value=NOTEBOOK_WORK_MISSING,
            on_change=self._refresh_scores,
            content=ft.Row(
                controls=[
                    ft.Radio(value=NOTEBOOK_WORK_COMPLETE, label="Complete (4 pts)"),
                    ft.Radio(value=NOTEBOOK_WORK_PARTIAL, label="Partial (2 pts)"),
                    ft.Radio(value=NOTEBOOK_WORK_MISSING, label="Missing (0 pts)"),
                ],
                wrap=True,
                spacing=SPACE_MD,
                run_spacing=SPACE_XS,
            ),
        )
        self.notebook_organized = ft.Checkbox(
            label="Notebook organized (2 pts)",
            value=False,
            on_change=self._refresh_scores,
        )

        self.comment_present = ft.Checkbox(
            label="Add comment",
            value=False,
            on_change=self._on_comment_toggle,
        )
        self.comment_tag_checkboxes: dict[str, ft.Checkbox] = {}
        for label, tag in [
            *POSITIVE_COMMENT_TAG_OPTIONS,
            *LEGIBILITY_COMMENT_TAG_OPTIONS,
            *COMPLETION_COMMENT_TAG_OPTIONS,
        ]:
            self.comment_tag_checkboxes[tag] = ft.Checkbox(
                label=label,
                value=False,
                on_change=self._refresh_scores,
            )
        self.comment_text = ft.TextField(
            label="Additional notes (optional)",
            value="",
            expand=True,
            multiline=True,
            min_lines=2,
            max_lines=3,
            disabled=True,
            visible=False,
            text_size=16,
            border_radius=RADIUS_SM,
            content_padding=ft.padding.symmetric(horizontal=12, vertical=12),
        )
        self.flag_auto_text = ft.Text(
            f"Auto flag now: {NO_ISSUE_FLAG}",
            size=12,
            color=COLOR_MUTED,
        )
        self.full_rubric_controls = ft.Row(
            controls=[
                ft.Container(
                    expand=1,
                    content=ft.Column(
                        controls=[
                            ft.Text("Agenda", weight=ft.FontWeight.W_600, size=13, color=COLOR_TEXT),
                            self.agenda_present,
                            ft.Column(
                                controls=[
                                    ft.Text("Agenda filled today", size=12, color=COLOR_MUTED),
                                    self.agenda_filled_today,
                                ],
                                spacing=SPACE_XS,
                            ),
                            self.agenda_readable,
                        ],
                        spacing=COMPACT_GROUP_SPACING,
                    ),
                ),
                ft.Container(
                    expand=1,
                    content=ft.Column(
                        controls=[
                            ft.Text("Notebook", weight=ft.FontWeight.W_600, size=13, color=COLOR_TEXT),
                            self.notebook_present,
                            ft.Column(
                                controls=[
                                    ft.Text("Notebook work today", size=12, color=COLOR_MUTED),
                                    self.notebook_work_today,
                                ],
                                spacing=SPACE_XS,
                            ),
                            self.notebook_organized,
                        ],
                        spacing=COMPACT_GROUP_SPACING,
                    ),
                ),
                ft.Container(
                    expand=1,
                    content=ft.Column(
                        controls=[
                            ft.Text("Status", weight=ft.FontWeight.W_600, size=13, color=COLOR_TEXT),
                            self.flag_auto_text,
                        ],
                        spacing=COMPACT_GROUP_SPACING,
                    ),
                ),
            ],
            spacing=SPACE_SM,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )
        self.comment_section = ft.Row(
            controls=[
                ft.Container(
                    expand=1,
                    content=ft.Column(
                        controls=[
                            ft.Text("Positive Performance", weight=ft.FontWeight.W_600, size=13, color=COLOR_TEXT),
                            *[self.comment_tag_checkboxes[tag] for _label, tag in POSITIVE_COMMENT_TAG_OPTIONS],
                        ],
                        spacing=COMPACT_GROUP_SPACING,
                    ),
                ),
                ft.Container(
                    expand=1,
                    content=ft.Column(
                        controls=[
                            ft.Text("Legibility / Organization", weight=ft.FontWeight.W_600, size=13, color=COLOR_TEXT),
                            *[self.comment_tag_checkboxes[tag] for _label, tag in LEGIBILITY_COMMENT_TAG_OPTIONS],
                        ],
                        spacing=COMPACT_GROUP_SPACING,
                    ),
                ),
                ft.Container(
                    expand=1,
                    content=ft.Column(
                        controls=[
                            ft.Text("Completion Status", weight=ft.FontWeight.W_600, size=13, color=COLOR_TEXT),
                            *[self.comment_tag_checkboxes[tag] for _label, tag in COMPLETION_COMMENT_TAG_OPTIONS],
                            self.comment_present,
                            self.comment_text,
                        ],
                        spacing=COMPACT_GROUP_SPACING,
                    ),
                ),
            ],
            spacing=SPACE_SM,
            vertical_alignment=ft.CrossAxisAlignment.START,
            visible=True,
        )

        self.agenda_score_text = ft.Text("0.0", size=28, weight=ft.FontWeight.BOLD, color=COLOR_TEXT)
        self.notebook_score_text = ft.Text("0.0", size=28, weight=ft.FontWeight.BOLD, color=COLOR_TEXT)
        self.internal_score_text = ft.Text("0.0", size=28, weight=ft.FontWeight.BOLD, color=COLOR_TEXT)
        self.gradebook_score_text = ft.Text("0.0", size=28, weight=ft.FontWeight.BOLD, color=COLOR_TEXT)

        self.save_next_btn = ft.ElevatedButton(
            "Save + Next",
            icon=ft.icons.CHECK_CIRCLE_OUTLINE,
            on_click=self._save_next,
            style=ft.ButtonStyle(
                bgcolor=COLOR_PRIMARY,
                color=ft.colors.WHITE,
                shape=ft.RoundedRectangleBorder(radius=RADIUS_MD),
                padding=ft.padding.symmetric(horizontal=20, vertical=16),
            ),
            height=52,
        )
        self.undo_btn = ft.OutlinedButton(
            "Undo Last",
            icon=ft.icons.UNDO,
            on_click=self._undo_last,
            style=ft.ButtonStyle(
                color=COLOR_PRIMARY,
                side=ft.BorderSide(1.4, COLOR_PRIMARY),
                shape=ft.RoundedRectangleBorder(radius=RADIUS_MD),
                padding=ft.padding.symmetric(horizontal=16, vertical=14),
            ),
            height=52,
        )
        self.insights_toggle_btn = ft.OutlinedButton(
            "Show Insights",
            icon=ft.icons.VISIBILITY,
            on_click=self._toggle_insights,
            disabled=True,
            style=ft.ButtonStyle(
                color=COLOR_PRIMARY,
                side=ft.BorderSide(1.2, COLOR_PRIMARY),
                shape=ft.RoundedRectangleBorder(radius=RADIUS_MD),
                padding=ft.padding.symmetric(horizontal=14, vertical=12),
            ),
        )
        self.tap_flow_hint = ft.Text(
            "Tap flow: check boxes -> Save + Next",
            size=12,
            color=COLOR_MUTED,
        )

        self.history_with_comments = ft.Checkbox(
            label="With comments",
            value=True,
            on_change=self._refresh_history_and_reliability,
        )
        self.history_without_comments = ft.Checkbox(
            label="Without comments",
            value=True,
            on_change=self._refresh_history_and_reliability,
        )
        self.history_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Date")),
                ft.DataColumn(ft.Text("Student")),
                ft.DataColumn(ft.Text("Agenda")),
                ft.DataColumn(ft.Text("Notebook")),
                ft.DataColumn(ft.Text("Internal")),
                ft.DataColumn(ft.Text("Gradebook")),
                ft.DataColumn(ft.Text("Deduction")),
                ft.DataColumn(ft.Text("Commented")),
                ft.DataColumn(ft.Text("Comments")),
            ],
            rows=[],
            column_spacing=16,
            divider_thickness=0.4,
        )

        self.page.on_keyboard_event = self._on_keyboard
        self.page.on_resized = self._on_page_resized

    def build(self) -> None:
        setup_controls_row = ft.ResponsiveRow(
            controls=[
                ft.Container(self.setup_grade, col={"xs": 12, "sm": 6, "md": 3, "lg": 2}),
                ft.Container(self.setup_checker, col={"xs": 12, "sm": 12, "md": 5, "lg": 4}),
                ft.Container(self.setup_date, col={"xs": 12, "sm": 6, "md": 2, "lg": 3}),
            ],
            spacing=SPACE_SM,
            run_spacing=SPACE_SM,
        )
        top_setup = ft.Container(
            bgcolor=COLOR_SURFACE,
            border_radius=RADIUS_LG,
            padding=COMPACT_CARD_PADDING,
            shadow=ft.BoxShadow(blur_radius=12, color="#14000000", offset=ft.Offset(0, 2)),
            content=ft.Column(
                spacing=COMPACT_SECTION_SPACING,
                controls=[
                    ft.Text("Session Setup", size=20, weight=ft.FontWeight.BOLD, color=COLOR_TEXT),
                    setup_controls_row,
                    self.setup_paths_text,
                    self.setup_student_picker,
                ],
            ),
        )

        score_strip = ft.Container(
            bgcolor=COLOR_SURFACE_ALT,
            border_radius=RADIUS_MD,
            padding=SPACE_MD,
            content=ft.ResponsiveRow(
                controls=[
                    ft.Container(
                        ft.Column(
                            [ft.Text("Agenda Score", size=12, color=COLOR_MUTED), self.agenda_score_text],
                            spacing=SPACE_XS,
                        ),
                        col={"xs": 12, "sm": 6, "md": 3},
                    ),
                    ft.Container(
                        ft.Column(
                            [ft.Text("Notebook Score", size=12, color=COLOR_MUTED), self.notebook_score_text],
                            spacing=SPACE_XS,
                        ),
                        col={"xs": 12, "sm": 6, "md": 3},
                    ),
                    ft.Container(
                        ft.Column(
                            [ft.Text("Internal /20", size=12, color=COLOR_MUTED), self.internal_score_text],
                            spacing=SPACE_XS,
                        ),
                        col={"xs": 12, "sm": 6, "md": 3},
                    ),
                    ft.Container(
                        ft.Column(
                            [ft.Text("Gradebook /10", size=12, color=COLOR_MUTED), self.gradebook_score_text],
                            spacing=SPACE_XS,
                        ),
                        col={"xs": 12, "sm": 6, "md": 3},
                    ),
                ],
                spacing=SPACE_SM,
                run_spacing=SPACE_SM,
            ),
        )

        student_header = ft.ResponsiveRow(
            controls=[
                ft.Container(
                    ft.Column([self.student_heading, self.student_progress_chip], spacing=SPACE_SM),
                    col={"xs": 12, "md": 8},
                ),
                ft.Container(
                    self.insights_toggle_btn,
                    alignment=ft.alignment.center_right,
                    col={"xs": 12, "md": 4},
                ),
            ],
            spacing=SPACE_SM,
            run_spacing=SPACE_SM,
        )
        self.scoring_lock_hint = ft.Container(
            visible=False,
            padding=ft.padding.symmetric(horizontal=10, vertical=8),
            border_radius=RADIUS_SM,
            bgcolor=COLOR_PRIMARY_SOFT,
            border=ft.border.all(1, "#220F766E"),
            content=ft.Row(
                controls=[
                    ft.Icon(ft.icons.LOCK_OUTLINE, size=16, color=COLOR_PRIMARY),
                    ft.Text(
                        "Scoring locked until Grade is selected and class is loaded.",
                        size=12,
                        color=COLOR_PRIMARY,
                    ),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

        student_card = ft.Container(
            bgcolor=COLOR_SURFACE,
            border_radius=RADIUS_LG,
            padding=COMPACT_CARD_PADDING,
            shadow=ft.BoxShadow(blur_radius=12, color="#14000000", offset=ft.Offset(0, 2)),
            content=ft.Column(
                spacing=COMPACT_SECTION_SPACING,
                controls=[
                    student_header,
                    ft.Divider(height=1, color="#1F000000"),
                    self.scoring_lock_hint,
                    self.full_rubric_controls,
                    self.comment_section,
                    score_strip,
                    ft.Text(
                        "Shortcuts: Enter = Save + Next, U = Undo Last",
                        size=12,
                        color=COLOR_MUTED,
                    ),
                ],
            ),
        )

        history_header = ft.ResponsiveRow(
            controls=[
                ft.Container(
                    ft.Text("History (Last 50)", size=18, weight=ft.FontWeight.BOLD, color=COLOR_TEXT),
                    col={"xs": 12, "md": 6},
                ),
                ft.Container(
                    ft.Row(
                        [self.history_with_comments, self.history_without_comments],
                        wrap=True,
                        spacing=SPACE_MD,
                    ),
                    col={"xs": 12, "md": 6},
                ),
            ],
            spacing=SPACE_SM,
            run_spacing=SPACE_SM,
        )

        history_card = ft.Container(
            bgcolor=COLOR_SURFACE,
            border_radius=RADIUS_LG,
            padding=COMPACT_CARD_PADDING,
            shadow=ft.BoxShadow(blur_radius=12, color="#14000000", offset=ft.Offset(0, 2)),
            content=ft.Column(
                spacing=COMPACT_GROUP_SPACING,
                controls=[
                    history_header,
                    ft.Container(
                        content=ft.Column(
                            [ft.Row([self.history_table], scroll=ft.ScrollMode.AUTO)],
                            scroll=ft.ScrollMode.AUTO,
                        ),
                        height=HISTORY_TABLE_HEIGHT,
                    ),
                ],
            ),
        )

        self.insights_panel = ft.Column([history_card], spacing=12)
        self.insights_switcher = ft.AnimatedSwitcher(
            content=self.insights_placeholder,
            transition=ft.AnimatedSwitcherTransition.FADE,
            duration=180,
            reverse_duration=140,
            switch_in_curve=ft.AnimationCurve.EASE_OUT,
            switch_out_curve=ft.AnimationCurve.EASE_IN,
            on_animation_end=self._on_insights_animation_end,
        )
        self.student_col_container = ft.Container(col=self._student_col_layout(insights_visible=False), content=student_card)
        self.insights_col_container = ft.Container(
            col=self._insights_col_layout(),
            visible=False,
            content=self.insights_switcher,
        )

        actions_row = ft.ResponsiveRow(
            controls=[
                ft.Container(self.save_next_btn, col={"xs": 12, "sm": 6, "md": 3, "lg": 2}),
                ft.Container(self.undo_btn, col={"xs": 12, "sm": 6, "md": 3, "lg": 2}),
                ft.Container(self.tap_flow_hint, col={"xs": 12, "sm": 6, "md": 3, "lg": 3}),
                ft.Container(self.status_text, col={"xs": 12, "md": 6, "lg": 5}, alignment=ft.alignment.center_right),
            ],
            spacing=SPACE_SM,
            run_spacing=SPACE_SM,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        self.bottom_actions_container = ft.Container(
            bgcolor=COLOR_SURFACE,
            border_radius=RADIUS_LG,
            padding=COMPACT_CARD_PADDING,
            shadow=ft.BoxShadow(blur_radius=16, color="#1A000000", offset=ft.Offset(0, 2)),
            content=actions_row,
        )

        self.page.add(
            ft.Column(
                expand=True,
                scroll=ft.ScrollMode.AUTO,
                controls=[
                    top_setup,
                    ft.ResponsiveRow(
                        controls=[
                            self.student_col_container,
                            self.insights_col_container,
                        ]
                    ),
                    self.bottom_actions_container,
                ],
                spacing=APP_CONTENT_SPACING,
            )
        )
        self._apply_window_responsive_layout(update_ui=False)
        self._set_scoring_enabled(False)
        self._refresh_scores()
        self._refresh_history_and_reliability()
        self.page.update()

    def _set_scoring_enabled(self, enabled: bool) -> None:
        controls = [
            self.agenda_present,
            self.agenda_filled_today,
            self.agenda_readable,
            self.notebook_present,
            self.notebook_work_today,
            self.notebook_organized,
            self.comment_present,
            self.comment_text,
            self.save_next_btn,
        ]
        controls.extend(self.comment_tag_checkboxes.values())
        for control in controls:
            control.disabled = not enabled
        self.setup_student_picker.disabled = not enabled
        self.undo_btn.disabled = not self.save_history
        self._apply_scoring_lock_visuals(enabled=enabled)
        if enabled:
            self._on_agenda_present_changed(None)
            self._on_notebook_present_changed(None)
            self._on_comment_toggle(None)
        else:
            self._apply_insights_visibility(visible=False, animate=False, persist=False)
        self._update_insights_toggle_button()
        self.page.update()

    def _apply_scoring_lock_visuals(self, *, enabled: bool) -> None:
        if self.student_col_container is not None:
            self.student_col_container.opacity = 1.0 if enabled else SCORING_LOCKED_OPACITY
        if self.bottom_actions_container is not None:
            self.bottom_actions_container.opacity = 1.0 if enabled else ACTIONS_LOCKED_OPACITY
        if self.scoring_lock_hint is not None:
            self.scoring_lock_hint.visible = not enabled

    def _class_key(self, grade: int) -> str:
        return str(grade)

    def _window_width(self) -> int:
        raw_width = getattr(self.page, "window_width", None)
        if isinstance(raw_width, (int, float)) and raw_width > 0:
            return int(raw_width)
        return 1280

    def _is_compact_window(self) -> bool:
        return self._window_width() < COMPACT_PADDING_BREAKPOINT

    def _is_insights_side_by_side_window(self) -> bool:
        return self._window_width() >= INSIGHTS_SIDE_BY_SIDE_BREAKPOINT

    def _student_col_layout(self, insights_visible: bool) -> dict[str, int]:
        if insights_visible and self._is_insights_side_by_side_window():
            return {"sm": 12, "md": 8}
        return {"sm": 12, "md": 12}

    def _insights_col_layout(self) -> dict[str, int]:
        if self._is_insights_side_by_side_window():
            return {"sm": 12, "md": 4}
        return {"sm": 12, "md": 12}

    def _apply_window_responsive_layout(self, update_ui: bool) -> None:
        self.page.padding = APP_PAGE_PADDING
        insights_active = self.insights_visible or self._pending_insights_hide
        if self.student_col_container is not None:
            self.student_col_container.col = self._student_col_layout(insights_active)
        if self.insights_col_container is not None:
            self.insights_col_container.col = self._insights_col_layout()
        if update_ui:
            self.page.update()

    def _on_page_resized(self, _: ft.ControlEvent | None) -> None:
        self._apply_window_responsive_layout(update_ui=True)

    def _current_class_key(self) -> str | None:
        if not self.session:
            return None
        return self._class_key(self.session.grade)

    def _update_insights_toggle_button(self) -> None:
        has_class_context = self.session is not None and bool(self.roster)
        self.insights_toggle_btn.disabled = not has_class_context
        if self.insights_visible:
            self.insights_toggle_btn.text = "Hide Insights"
            self.insights_toggle_btn.icon = ft.icons.VISIBILITY_OFF
        else:
            self.insights_toggle_btn.text = "Show Insights"
            self.insights_toggle_btn.icon = ft.icons.VISIBILITY

    def _toggle_insights(self, _: ft.ControlEvent | None) -> None:
        if self.insights_toggle_btn.disabled:
            return
        self._apply_insights_visibility(visible=not self.insights_visible, animate=True, persist=True)

    def _restore_insights_visibility_for_session(self) -> None:
        class_key = self._current_class_key()
        visible = self.insights_visibility_by_class.get(class_key, False) if class_key else False
        self._apply_insights_visibility(visible=visible, animate=False, persist=False)

    def _finalize_insights_hidden_layout(self) -> None:
        if self.insights_col_container is None or self.student_col_container is None or self.insights_switcher is None:
            return
        self._pending_insights_hide = False
        self.insights_switcher.content = self.insights_placeholder
        self.insights_col_container.visible = False
        self.student_col_container.col = self._student_col_layout(insights_visible=False)
        self.insights_col_container.col = self._insights_col_layout()
        self.page.update()

    async def _finalize_insights_hide_after_delay(self, generation: int) -> None:
        await asyncio.sleep(self._insights_hide_fallback_ms / 1000)
        if generation != self._insights_hide_generation:
            return
        if not self._pending_insights_hide or self.insights_visible:
            return
        self._finalize_insights_hidden_layout()

    def _schedule_insights_hide_fallback(self, generation: int) -> None:
        self.page.run_task(self._finalize_insights_hide_after_delay, generation)

    def _on_insights_animation_end(self, _: ft.ControlEvent) -> None:
        if not self._pending_insights_hide or self.insights_visible:
            return
        self._finalize_insights_hidden_layout()

    def _apply_insights_visibility(self, visible: bool, animate: bool, persist: bool) -> None:
        self.insights_visible = visible
        self._update_insights_toggle_button()

        class_key = self._current_class_key()
        if persist and class_key:
            self.insights_visibility_by_class[class_key] = visible
            try:
                save_insights_visibility(DEFAULT_UI_PREFERENCES_FILE, self.insights_visibility_by_class)
            except Exception as exc:  # noqa: BLE001
                self._show_message(f"Could not save UI preferences: {exc}", warn=True)

        self._insights_hide_generation += 1
        generation = self._insights_hide_generation

        if (
            self.insights_col_container is None
            or self.student_col_container is None
            or self.insights_switcher is None
            or self.insights_panel is None
        ):
            return

        if visible:
            self._pending_insights_hide = False
            self.insights_col_container.visible = True
            self.student_col_container.col = self._student_col_layout(insights_visible=True)
            self.insights_col_container.col = self._insights_col_layout()
            self.insights_switcher.content = self.insights_panel
            self.page.update()
        elif animate:
            self._pending_insights_hide = True
            self.insights_col_container.visible = True
            self.student_col_container.col = self._student_col_layout(insights_visible=True)
            self.insights_col_container.col = self._insights_col_layout()
            self.insights_switcher.content = self.insights_placeholder
            self._schedule_insights_hide_fallback(generation)
            self.page.update()
        else:
            self._finalize_insights_hidden_layout()

    def _show_message(self, message: str, error: bool = False, warn: bool = False) -> None:
        message_color = COLOR_MUTED
        bar_color = COLOR_PRIMARY
        if warn:
            message_color = COLOR_WARN
            bar_color = COLOR_WARN
        if error:
            message_color = COLOR_DANGER
            bar_color = COLOR_DANGER

        self.status_text.value = message
        self.status_text.color = message_color
        self.page.snack_bar = ft.SnackBar(ft.Text(message), bgcolor=bar_color)
        self.page.snack_bar.open = True
        self.page.update()

    def _focus_if_supported(self, control: ft.Control) -> None:
        focus_method = getattr(control, "focus", None)
        if callable(focus_method):
            focus_method()

    def _load_students_source(self) -> list[Student]:
        students_file = DEFAULT_STUDENTS_FILE
        if not students_file.exists():
            raise FileNotFoundError(f"Students file not found: {students_file}")
        if self.students_cache is None:
            self.students_cache = load_students(students_file)
        return self.students_cache

    def _grade_changed(self, _: ft.ControlEvent | None) -> None:
        try:
            self._refresh_checker_options(update_ui=False)
            self._auto_load_roster()
        except Exception as exc:  # noqa: BLE001
            self._show_message(str(exc), error=True)

    def _checker_changed(self, _: ft.ControlEvent | None) -> None:
        if not self.session:
            return
        checker = self._selected_checker_name(strict=False)
        if checker is None:
            return
        self.session = SessionConfig(
            checker=checker,
            check_date=self.session.check_date,
            grade=self.session.grade,
            students_file=self.session.students_file,
            output_file=self.session.output_file,
        )

    def _refresh_checker_options(self, update_ui: bool) -> None:
        previous_checker_id = (self.setup_checker.value or "").strip()
        self.setup_checker.options = []
        self.setup_checker.value = None
        self.setup_checker.disabled = True
        self.checker_name_by_id = {}

        grade_raw = (self.setup_grade.value or "").strip()
        if not grade_raw:
            if update_ui:
                self.page.update()
            return

        grade = int(grade_raw)
        class_students = filter_students(self._load_students_source(), grade=grade)

        seen_student_ids: set[str] = set()
        options: list[ft.dropdown.Option] = []
        for student in class_students:
            if student.student_id in seen_student_ids:
                continue
            seen_student_ids.add(student.student_id)
            self.checker_name_by_id[student.student_id] = student.full_name
            options.append(ft.dropdown.Option(key=student.student_id, text=f"{student.full_name} ({student.student_id})"))

        self.setup_checker.options = options
        self.setup_checker.disabled = not options
        if options:
            valid_checker_ids = {option.key for option in options}
            if previous_checker_id in valid_checker_ids:
                self.setup_checker.value = previous_checker_id
            else:
                self.setup_checker.value = options[0].key

        if update_ui:
            self.page.update()

    def _selected_checker_name(self, strict: bool) -> str | None:
        checker_id = (self.setup_checker.value or "").strip()
        if not checker_id:
            if strict:
                raise ValueError("Select checker from the selected class roster (grade).")
            return None

        checker = self.checker_name_by_id.get(checker_id)
        if checker is None:
            self._refresh_checker_options(update_ui=False)
            checker = self.checker_name_by_id.get(checker_id)

        if checker is None and strict:
            raise ValueError("Select a valid checker from the selected class roster (grade).")
        return checker

    def _validate_session(self) -> SessionConfig:
        if not self.setup_grade.value:
            raise ValueError("Select grade first.")

        check_date = (self.setup_date.value or "").strip()
        try:
            datetime.strptime(check_date, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("Date must be YYYY-MM-DD.") from exc

        try:
            grade = int(self.setup_grade.value or "")
        except ValueError as exc:
            raise ValueError("Grade must be a valid number.") from exc

        checker = self._selected_checker_name(strict=True)
        assert checker is not None

        students_file = DEFAULT_STUDENTS_FILE
        if not students_file.exists():
            raise FileNotFoundError(f"Students file not found: {students_file}")

        output_file = DEFAULT_OUTPUT_FILE

        return SessionConfig(
            checker=checker,
            check_date=check_date,
            grade=grade,
            students_file=students_file,
            output_file=output_file,
        )

    def _auto_load_roster(self) -> None:
        try:
            config = self._validate_session()
            students = self._load_students_source()
            roster = filter_students(students, config.grade)
            if not roster:
                raise ValueError(f"No students found for grade {config.grade}.")
        except Exception as exc:  # noqa: BLE001
            self.session = None
            self.roster = []
            self.current_index = 0
            self.save_history = []
            self._refresh_student_picker()
            self._set_scoring_enabled(False)
            self._render_current_student()
            self._show_message(str(exc), error=True)
            return

        self._finish_roster_load(config, roster)

    def _refresh_student_picker(self) -> None:
        options = []
        for index, student in enumerate(self.roster):
            options.append(ft.dropdown.Option(key=str(index), text=f"{student.last_name}, {student.first_name}"))
        self.setup_student_picker.options = options
        if options and self.current_index < len(options):
            self.setup_student_picker.value = str(self.current_index)
        else:
            self.setup_student_picker.value = None

    def _student_picker_changed(self, _: ft.ControlEvent) -> None:
        if not self.roster:
            return
        selected = self.setup_student_picker.value
        if selected is None:
            return
        try:
            new_index = int(selected)
        except ValueError:
            return
        if new_index < 0 or new_index >= len(self.roster):
            return
        self.current_index = new_index
        self._reset_inputs()
        self._render_current_student()
        self._show_message(f"Ready for {self.roster[self.current_index].full_name}.")
        self._focus_if_supported(self.notebook_present)

    def _finish_roster_load(self, config: SessionConfig, roster: list[Student]) -> None:
        self.session = config
        self.roster = roster
        self.current_index = 0
        self.save_history = []
        self._refresh_student_picker()
        self._reset_inputs()
        self._set_scoring_enabled(True)
        self._restore_insights_visibility_for_session()
        self._render_current_student()
        self._refresh_history_and_reliability()
        self._show_message(f"Loaded {len(roster)} students for Grade {config.grade}.")

    def _render_current_student(self) -> None:
        if not self.roster:
            self.student_heading.value = "No roster loaded"
            self.student_progress.value = "0 / 0"
            self.setup_student_picker.value = None
            self.page.update()
            return

        if self.current_index >= len(self.roster):
            self.student_heading.value = "Roster complete"
            self.student_progress.value = f"{len(self.roster)} / {len(self.roster)}"
            self.setup_student_picker.value = None
            self._set_scoring_enabled(False)
            self.save_next_btn.disabled = True
            self.page.update()
            return

        student = self.roster[self.current_index]
        self.student_heading.value = f"{student.last_name}, {student.first_name} ({student.student_id})"
        self.student_progress.value = f"{self.current_index + 1} / {len(self.roster)}"
        self.setup_student_picker.value = str(self.current_index)
        self.page.update()

    def _on_agenda_present_changed(self, _: ft.ControlEvent | None) -> None:
        details_enabled = (not self.agenda_present.disabled) and bool(self.agenda_present.value)
        if not details_enabled:
            self.agenda_filled_today.value = AGENDA_FILLED_BLANK
            self.agenda_readable.value = False
        self.agenda_filled_today.disabled = not details_enabled
        self.agenda_readable.disabled = not details_enabled
        self._refresh_scores(None)

    def _on_notebook_present_changed(self, _: ft.ControlEvent | None) -> None:
        details_enabled = (not self.notebook_present.disabled) and bool(self.notebook_present.value)
        if not details_enabled:
            self.notebook_work_today.value = NOTEBOOK_WORK_MISSING
            self.notebook_organized.value = False
        self.notebook_work_today.disabled = not details_enabled
        self.notebook_organized.disabled = not details_enabled
        self._refresh_scores(None)

    def _on_comment_toggle(self, _: ft.ControlEvent | None) -> None:
        comment_enabled = (not self.comment_present.disabled) and bool(self.comment_present.value)
        self.comment_text.disabled = not comment_enabled
        self.comment_text.visible = comment_enabled
        if not comment_enabled:
            self.comment_text.value = ""
        self._refresh_scores(None)
        self.page.update()

    def _selected_comment_tags(self) -> list[str]:
        return [
            tag
            for tag, checkbox in self.comment_tag_checkboxes.items()
            if bool(checkbox.value)
        ]

    def _compute_form_state(self) -> RubricState:
        agenda_present = bool(self.agenda_present.value)
        agenda_filled_today = (self.agenda_filled_today.value or "").strip().lower()
        if agenda_filled_today not in AGENDA_FILLED_OPTIONS:
            agenda_filled_today = AGENDA_FILLED_BLANK
        agenda_readable = bool(self.agenda_readable.value) if agenda_present else False

        notebook_present = bool(self.notebook_present.value)
        notebook_work_today = (self.notebook_work_today.value or "").strip().lower()
        if notebook_work_today not in NOTEBOOK_WORK_OPTIONS:
            notebook_work_today = NOTEBOOK_WORK_MISSING
        notebook_organized = bool(self.notebook_organized.value) if notebook_present else False

        if not agenda_present:
            agenda_filled_today = AGENDA_FILLED_BLANK
        if not notebook_present:
            notebook_work_today = NOTEBOOK_WORK_MISSING

        agenda_score = compute_agenda_score_v2(
            agenda_present=agenda_present,
            agenda_filled_today=agenda_filled_today,
            agenda_readable=agenda_readable,
        )
        notebook_score = compute_notebook_score_v2(
            notebook_present=notebook_present,
            notebook_work_today=notebook_work_today,
            notebook_organized=notebook_organized,
        )

        comment_tags = self._selected_comment_tags()
        comment_note = (self.comment_text.value or "").strip() if bool(self.comment_present.value) else ""
        negative_tags = [tag for tag in comment_tags if tag in NEGATIVE_COMMENT_DEDUCTION_BY_TAG]
        comment_deduction = compute_comment_deduction(negative_tags)

        internal_score = compute_internal_total(
            agenda_score=agenda_score,
            notebook_score=notebook_score,
            deduction=comment_deduction,
        )
        gradebook_score = round(internal_score / 2, 2)

        entry_written = agenda_present and agenda_filled_today != AGENDA_FILLED_BLANK
        all_subjects_filled = agenda_present and agenda_filled_today == AGENDA_FILLED_COMPLETE
        organized = agenda_readable and notebook_organized
        auto_flag = self._compute_issue_flag(
            notebook_score=notebook_score,
            agenda_present=agenda_present,
            entry_written=entry_written,
            all_subjects_filled=all_subjects_filled,
            organized=organized,
        )

        return RubricState(
            agenda_present=agenda_present,
            agenda_filled_today=agenda_filled_today,
            agenda_readable=agenda_readable,
            notebook_present=notebook_present,
            notebook_work_today=notebook_work_today,
            notebook_organized=notebook_organized,
            agenda_score=agenda_score,
            notebook_score=notebook_score,
            comment_tags=comment_tags,
            comments=comment_note,
            comment_deduction=comment_deduction,
            internal_score=internal_score,
            gradebook_score=gradebook_score,
            entry_written=entry_written,
            all_subjects_filled=all_subjects_filled,
            organized=organized,
            auto_flag=auto_flag,
        )

    def _compute_issue_flag(
        self,
        *,
        notebook_score: float,
        agenda_present: bool,
        entry_written: bool,
        all_subjects_filled: bool,
        organized: bool,
    ) -> str:
        return compute_issue_flag(
            notebook_score=notebook_score,
            agenda_present=agenda_present,
            entry_written=entry_written,
            all_subjects_filled=all_subjects_filled,
            organized=organized,
        )

    def _refresh_scores(self, _: ft.ControlEvent | None = None) -> None:
        state = self._compute_form_state()
        self.flag_auto_text.value = f"Auto flag now: {state.auto_flag}"
        self.agenda_score_text.value = str(state.agenda_score)
        self.notebook_score_text.value = str(state.notebook_score)
        self.internal_score_text.value = str(state.internal_score)
        self.gradebook_score_text.value = str(state.gradebook_score)
        self.page.update()

    def _save_next(self, _: ft.ControlEvent | None) -> None:
        if not self.session or not self.roster:
            self._show_message("Select grade to auto-load roster before saving.", error=True)
            return
        if self.current_index >= len(self.roster):
            self._show_message("All students already saved for this roster.")
            return

        now = time.monotonic()
        if now - self.last_save_at < 0.35:
            return
        self.last_save_at = now

        self.save_next_btn.disabled = True
        self.page.update()
        try:
            state = self._compute_form_state()
            checker = self._selected_checker_name(strict=True)
            assert checker is not None

            student = self.roster[self.current_index]
            has_comment_input_enabled = bool(self.comment_present.value)
            has_comment_content = bool(state.comment_tags) or bool(state.comments)
            if has_comment_input_enabled and not has_comment_content:
                self.comment_present.value = False
                self._on_comment_toggle(None)
                state = self._compute_form_state()

            record = CheckRecord.from_student(
                student=student,
                check_date=self.session.check_date,
                checker=checker,
                notebook_score=state.notebook_score,
                agenda_present=state.agenda_present,
                entry_written=state.entry_written,
                all_subjects_filled=state.all_subjects_filled,
                organized=state.organized,
                agenda_score=int(round(state.agenda_score)),
                gradebook_score=state.gradebook_score,
                agenda_filled_today=state.agenda_filled_today,
                agenda_readable=state.agenda_readable,
                notebook_present_detail=state.notebook_present,
                notebook_work_today=state.notebook_work_today,
                notebook_organized=state.notebook_organized,
                comment_tags="|".join(state.comment_tags),
                comment_deduction=state.comment_deduction,
                internal_score=state.internal_score,
                score_model=SCORE_MODEL_INTERNAL20_GRADEBOOK10_V1,
                flag=state.auto_flag,
                comments=state.comments,
            )
            append_record(record, self.session.output_file)
            self.save_history.append((self.current_index, record))
            self.undo_btn.disabled = False

            saved_name = student.full_name
            self.current_index += 1
            self._reset_inputs()
            self._render_current_student()
            self._refresh_history_and_reliability()
            if self.current_index >= len(self.roster):
                self._show_message(f"Saved final student. Output: {self.session.output_file}")
            else:
                self._show_message(f"Saved {saved_name}.")
                self._focus_if_supported(self.notebook_present)
        except Exception as exc:  # noqa: BLE001
            self._show_message(str(exc), error=True)
        finally:
            done = self.current_index >= len(self.roster)
            self.save_next_btn.disabled = done
            self.page.update()

    def _on_keyboard(self, event: ft.KeyboardEvent) -> None:
        key = (event.key or "").lower()
        if key == "enter":
            self._save_next(None)
        elif key == "u" and not self.undo_btn.disabled:
            self._undo_last(None)

    def _undo_last(self, _: ft.ControlEvent | None) -> None:
        if not self.session:
            self._show_message("No active session to undo.", error=True)
            return
        if not self.save_history:
            self._show_message("Nothing to undo.", error=True)
            return

        removed = remove_last_record(self.session.output_file)
        if not removed:
            self._show_message("Could not undo because output file has no rows.", error=True)
            return

        index_before_save, record = self.save_history.pop()
        self.current_index = index_before_save
        self._load_record_into_form(record)
        self._render_current_student()
        self._refresh_history_and_reliability()
        self.undo_btn.disabled = not self.save_history
        self._show_message("Undid last saved student.")

    def _load_record_into_form(self, record: CheckRecord) -> None:
        self.agenda_present.value = record.agenda_present
        self.agenda_filled_today.value = record.agenda_filled_today
        self.agenda_readable.value = record.agenda_readable
        self.notebook_present.value = record.notebook_present_detail
        self.notebook_work_today.value = record.notebook_work_today
        self.notebook_organized.value = record.notebook_organized
        selected_tags = {tag.strip() for tag in record.comment_tags.split("|") if tag.strip()}
        for tag, checkbox in self.comment_tag_checkboxes.items():
            checkbox.value = tag in selected_tags
        saved_comment = (record.comments or "").strip()
        self.comment_present.value = bool(saved_comment)
        self.comment_text.value = saved_comment

        self._on_agenda_present_changed(None)
        self._on_notebook_present_changed(None)
        self._on_comment_toggle(None)
        self._refresh_scores(None)

    def _reset_inputs(self) -> None:
        self.agenda_present.value = False
        self.agenda_filled_today.value = AGENDA_FILLED_BLANK
        self.agenda_readable.value = False
        self.notebook_present.value = False
        self.notebook_work_today.value = NOTEBOOK_WORK_MISSING
        self.notebook_organized.value = False
        for checkbox in self.comment_tag_checkboxes.values():
            checkbox.value = False
        self.comment_present.value = False
        self.comment_text.value = ""
        self.flag_auto_text.value = f"Auto flag now: {NO_ISSUE_FLAG}"
        self.notebook_score_text.value = "0.0"
        self.internal_score_text.value = "0.0"
        self.gradebook_score_text.value = "0.0"
        self.agenda_score_text.value = "0.0"
        self._on_agenda_present_changed(None)
        self._on_notebook_present_changed(None)
        self._on_comment_toggle(None)
        self._refresh_scores(None)
        self._focus_if_supported(self.notebook_present)

    def _records_for_current_class(self) -> tuple[list[CheckRecord], list[str]]:
        if not self.session:
            return [], []
        load_result = load_records_with_warnings(self.session.output_file)
        filtered = [
            record
            for record in load_result.records
            if record.grade == self.session.grade
        ]
        return filtered, load_result.warnings

    def _refresh_history_and_reliability(self, _: ft.ControlEvent | None = None) -> None:
        class_records, warnings = self._records_for_current_class()

        if warnings:
            self.status_text.value = f"{len(warnings)} invalid row(s) skipped in output CSV."
            self.status_text.color = COLOR_WARN

        self._refresh_history(class_records)
        self.page.update()

    def _resolved_history_scores(self, record: CheckRecord) -> tuple[float, float]:
        if record.score_model == SCORE_MODEL_INTERNAL20_GRADEBOOK10_V1:
            internal_score = record.internal_score
            if internal_score <= 0 and (
                record.agenda_score > 0
                or record.notebook_score > 0
                or record.comment_deduction > 0
            ):
                internal_score = compute_internal_total(
                    agenda_score=record.agenda_score,
                    notebook_score=record.notebook_score,
                    deduction=record.comment_deduction,
                )
            return round(internal_score, 2), round(record.gradebook_score, 2)

        legacy_gradebook = round(record.gradebook_score, 2)
        if legacy_gradebook > 10:
            return legacy_gradebook, round(legacy_gradebook / 2, 2)
        return round(legacy_gradebook * 2, 2), legacy_gradebook

    def _refresh_history(self, class_records: list[CheckRecord]) -> None:
        self.history_table.rows.clear()
        if not self.session:
            return

        date_filtered = [record for record in class_records if record.date == self.session.check_date]
        include_with_comments = bool(self.history_with_comments.value)
        include_without_comments = bool(self.history_without_comments.value)
        if include_with_comments or include_without_comments:
            date_filtered = [
                record
                for record in date_filtered
                if (
                    include_with_comments
                    and (bool(record.comments.strip()) or bool(record.comment_tags.strip()))
                )
                or (
                    include_without_comments
                    and not (bool(record.comments.strip()) or bool(record.comment_tags.strip()))
                )
            ]
        else:
            date_filtered = []

        display = date_filtered[-50:]
        for record in display:
            has_comment = bool(record.comments.strip()) or bool(record.comment_tags.strip())
            internal_score, gradebook_score = self._resolved_history_scores(record)
            self.history_table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(record.date)),
                        ft.DataCell(ft.Text(record.student_name)),
                        ft.DataCell(ft.Text(str(record.agenda_score))),
                        ft.DataCell(ft.Text(str(record.notebook_score))),
                        ft.DataCell(ft.Text(str(internal_score))),
                        ft.DataCell(ft.Text(str(gradebook_score))),
                        ft.DataCell(ft.Text(str(record.comment_deduction))),
                        ft.DataCell(ft.Text("Yes" if has_comment else "")),
                        ft.DataCell(ft.Text(record.comments if has_comment else "-")),
                    ]
                )
            )

        if not display:
            empty_message = (
                "No records match selected comment filters."
                if not include_with_comments and not include_without_comments
                else "No records yet for this class/date."
            )
            self.history_table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text("-")),
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(empty_message, color=COLOR_MUTED),
                                alignment=ft.alignment.center_left,
                            )
                        ),
                        ft.DataCell(ft.Text("-")),
                        ft.DataCell(ft.Text("-")),
                        ft.DataCell(ft.Text("-")),
                        ft.DataCell(ft.Text("-")),
                        ft.DataCell(ft.Text("-")),
                        ft.DataCell(ft.Text("-")),
                        ft.DataCell(ft.Text("-")),
                    ]
                )
            )

def main(page: ft.Page) -> None:
    app = NAFletApp(page)
    app.build()


if __name__ == "__main__":
    ft.app(target=main)

