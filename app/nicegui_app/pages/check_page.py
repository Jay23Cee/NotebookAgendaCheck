from __future__ import annotations

from nicegui import ui
from nicegui.events import KeyEventArguments, ValueChangeEventArguments

from app.nicegui_app.components.agenda_card import AgendaCardHandles, build_agenda_card
from app.nicegui_app.components.check_mode_picker import CheckModePickerHandles, build_check_mode_picker
from app.nicegui_app.components.footer_bar import FooterBarHandles, build_footer_bar
from app.nicegui_app.components.header_bar import HeaderBarHandles, build_header_bar
from app.nicegui_app.components.history_panel import HistoryPanelHandles, build_history_panel
from app.nicegui_app.components.lock_overlay import LockOverlayHandles, build_lock_overlay
from app.nicegui_app.components.notebook_card import NotebookCardHandles, build_notebook_card
from app.nicegui_app.components.shell import ShellHandles, build_shell
from app.nicegui_app.components.status_tags_card import StatusTagsCardHandles, build_status_tags_card
from app.nicegui_app.services.keyboard_shortcuts import KeyboardShortcutService
from app.nicegui_app.services.workflow_controller import NAWorkflowController
from app.scoring import CHECK_MODE_AGENDA_ONLY, CHECK_MODE_BOTH, CHECK_MODE_NOTEBOOK_ONLY


class CheckPage:
    def __init__(self) -> None:
        self.controller = NAWorkflowController()
        self.shortcuts = KeyboardShortcutService()

        self.shell: ShellHandles | None = None
        self.header: HeaderBarHandles | None = None
        self.student_name_label: ui.label | None = None
        self.mode_picker: CheckModePickerHandles | None = None
        self.cards_grid: ui.element | None = None
        self.agenda_card: AgendaCardHandles | None = None
        self.notebook_card: NotebookCardHandles | None = None
        self.status_card: StatusTagsCardHandles | None = None
        self.history_panel: HistoryPanelHandles | None = None
        self.footer: FooterBarHandles | None = None
        self.lock_overlay: LockOverlayHandles | None = None

        self._syncing = False

    def build(self) -> None:
        self.shell = build_shell()

        assert self.shell is not None
        with self.shell.header_slot:
            self.header = build_header_bar(
                on_grade_change=self._on_grade_change,
                on_student_change=self._on_student_change,
                on_checker_mode_change=self._on_checker_mode_change,
                on_checker_student_change=self._on_checker_student_change,
                on_date_change=self._on_date_change,
                initial_date=self.controller.state.session.check_date,
            )

        with self.shell.content_slot:
            with ui.row().classes("student_strip"):
                ui.icon("person").classes("student_icon")
                self.student_name_label = ui.label("No roster loaded").classes("na-student-name student_name")

            self.mode_picker = build_check_mode_picker(
                on_mode_change=self._on_check_mode_change,
            )

            with ui.element("div").classes("na-cards-grid cards_grid") as cards_grid:
                self.agenda_card = build_agenda_card(
                    on_agenda_present=self._on_agenda_present,
                    on_agenda_filled=self._on_agenda_filled,
                    on_agenda_readable=self._on_agenda_readable,
                )
                self.notebook_card = build_notebook_card(
                    on_notebook_present=self._on_notebook_present,
                    on_notebook_work=self._on_notebook_work,
                    on_notebook_organized=self._on_notebook_organized,
                )
                self.status_card = build_status_tags_card(
                    on_tag_toggle=self._on_tag_toggle,
                    on_comment_toggle=self._on_comment_toggle,
                    on_comment_change=self._on_comment_change,
                )
            self.cards_grid = cards_grid
            self.history_panel = build_history_panel(on_filter_change=self._on_history_filter_change)
            self.lock_overlay = build_lock_overlay()

        with self.shell.footer_slot:
            self.footer = build_footer_bar(on_save=self._save_action, on_undo=self._undo_action)

        self._bind_focus_guard()
        self._set_default_history_range()
        ui.keyboard(on_key=self._on_keyboard, repeating=False, ignore=["textarea"])
        self._refresh_ui()

    def _bind_focus_guard(self) -> None:
        if self.header is None or self.status_card is None:
            return

        self.header.date_input.on("focus", lambda _: self._set_shortcuts_suspended(True))
        self.header.date_input.on("blur", lambda _: self._set_shortcuts_suspended(False))
        self.status_card.comment_input.on("focus", lambda _: self._set_shortcuts_suspended(True))
        self.status_card.comment_input.on("blur", lambda _: self._set_shortcuts_suspended(False))

    def _set_shortcuts_suspended(self, suspended: bool) -> None:
        self.controller.state.shortcuts_suspended = suspended

    def _on_keyboard(self, event: KeyEventArguments) -> None:
        handled = self.shortcuts.handle_key(
            event,
            state=self.controller.state,
            on_save=self._save_action,
            on_undo=self._undo_action,
        )
        if handled:
            self._refresh_ui()

    def _on_grade_change(self, event: ValueChangeEventArguments) -> None:
        if self._syncing:
            return
        result = self.controller.set_grade(event.value)
        self._set_default_history_range()
        self._refresh_ui()
        self._apply_result(result, notify=result.level != "info")

    def _on_check_mode_change(self, event: ValueChangeEventArguments) -> None:
        if self._syncing:
            return
        result = self.controller.set_check_mode(str(event.value))
        self._refresh_ui()
        self._apply_result(result, notify=False)

    def _on_student_change(self, event: ValueChangeEventArguments) -> None:
        if self._syncing:
            return
        result = self.controller.select_student(event.value)
        self._refresh_ui()
        self._apply_result(result, notify=False)

    def _on_checker_mode_change(self, event: ValueChangeEventArguments) -> None:
        if self._syncing:
            return
        result = self.controller.set_checker_mode(str(event.value))
        self._refresh_ui()
        self._apply_result(result, notify=False)

    def _on_checker_student_change(self, event: ValueChangeEventArguments) -> None:
        if self._syncing:
            return
        result = self.controller.set_checker_student(event.value)
        self._refresh_ui()
        self._apply_result(result, notify=False)

    def _on_date_change(self, event: ValueChangeEventArguments) -> None:
        if self._syncing:
            return
        result = self.controller.set_date(event.value)
        self._set_default_history_range()
        self._refresh_ui()
        self._apply_result(result, notify=False)

    def _on_history_filter_change(self, _: ValueChangeEventArguments | None = None) -> None:
        if self._syncing:
            return
        self._refresh_ui()

    def _set_default_history_range(self) -> None:
        if self.history_panel is None:
            return
        default_date = self.controller.state.session.check_date
        self.history_panel.start_date_input.value = default_date
        self.history_panel.end_date_input.value = default_date
        self.history_panel.start_date_input.update()
        self.history_panel.end_date_input.update()

    def _on_agenda_present(self, event: ValueChangeEventArguments) -> None:
        if self._syncing:
            return
        self.controller.set_agenda_present(bool(event.value))
        self._refresh_ui()

    def _on_agenda_filled(self, event: ValueChangeEventArguments) -> None:
        if self._syncing:
            return
        self.controller.set_agenda_filled_today(str(event.value))
        self._refresh_ui()

    def _on_agenda_readable(self, event: ValueChangeEventArguments) -> None:
        if self._syncing:
            return
        self.controller.set_agenda_readable(bool(event.value))
        self._refresh_ui()

    def _on_notebook_present(self, event: ValueChangeEventArguments) -> None:
        if self._syncing:
            return
        self.controller.set_notebook_present(bool(event.value))
        self._refresh_ui()

    def _on_notebook_work(self, event: ValueChangeEventArguments) -> None:
        if self._syncing:
            return
        self.controller.set_notebook_work_today(str(event.value))
        self._refresh_ui()

    def _on_notebook_organized(self, event: ValueChangeEventArguments) -> None:
        if self._syncing:
            return
        self.controller.set_notebook_organized(bool(event.value))
        self._refresh_ui()

    def _on_tag_toggle(self, tag: str, selected: bool) -> None:
        if self._syncing:
            return
        self.controller.toggle_comment_tag(tag, selected)
        self._refresh_ui()

    def _on_comment_toggle(self, event: ValueChangeEventArguments) -> None:
        if self._syncing:
            return
        self.controller.set_comment_enabled(bool(event.value))
        self._refresh_ui()

    def _on_comment_change(self, event: ValueChangeEventArguments) -> None:
        if self._syncing:
            return
        self.controller.set_comment_text(str(event.value))
        self._refresh_ui()

    def _save_action(self) -> None:
        result = self.controller.save_next()
        self._refresh_ui()
        self._apply_result(result, notify=True)

    def _undo_action(self) -> None:
        result = self.controller.undo_last()
        self._refresh_ui()
        self._apply_result(result, notify=True)

    def _refresh_ui(self) -> None:
        if not all(
            [
                self.shell,
                self.header,
                self.student_name_label,
                self.mode_picker,
                self.cards_grid,
                self.agenda_card,
                self.notebook_card,
                self.status_card,
                self.history_panel,
                self.footer,
                self.lock_overlay,
            ]
        ):
            return

        session = self.controller.state.session
        form = self.controller.state.form
        computed = self.controller.state.computed

        self._syncing = True
        try:
            class_text = f"Grade {session.grade if session.grade is not None else '-'}"
            self.shell.class_context_label.set_text(class_text)
            self.shell.student_context_label.set_text(session.progress_text)
            self.shell.status_label.set_text(self.controller.state.status_message)
            self.shell.status_label.classes(replace=f"na-status {self.controller.state.status_level}")

            self.header.grade_select.value = str(session.grade) if session.grade is not None else None
            self.header.grade_select.update()

            self.student_name_label.set_text(session.student_heading)
            self.header.progress_chip.set_text(session.progress_text)

            self.header.student_select.options = session.student_options
            self.header.student_select.value = (
                str(session.current_index)
                if session.active_student is not None and not session.roster_complete
                else None
            )
            self.header.student_select.update()

            self.header.checker_mode_select.value = session.checker_mode
            self.header.checker_mode_select.update()

            self.header.checker_student_select.options = session.checker_label_by_id
            self.header.checker_student_select.value = session.checker_id if session.checker_mode == "student" else None
            self.header.checker_student_select.visible = session.checker_mode == "student"
            self.header.checker_student_select.update()

            self.header.date_input.value = session.check_date
            self.header.date_input.update()

            mode = session.check_mode
            mode_selected = mode in {CHECK_MODE_NOTEBOOK_ONLY, CHECK_MODE_BOTH, CHECK_MODE_AGENDA_ONLY}

            self.mode_picker.mode_radio.value = mode if mode_selected else None
            self.mode_picker.mode_radio.update()
            self.mode_picker.chooser_root.visible = not session.locked
            self.mode_picker.chooser_root.update()

            self.agenda_card.agenda_present.value = form.agenda_present
            self.agenda_card.agenda_present.update()
            self.agenda_card.agenda_filled_today.value = form.agenda_filled_today
            self.agenda_card.agenda_filled_today.update()
            self.agenda_card.agenda_readable.value = form.agenda_readable
            self.agenda_card.agenda_readable.update()
            self.agenda_card.mini_score.set_text(
                "-- / 10" if mode == CHECK_MODE_NOTEBOOK_ONLY else f"{computed.agenda_score} / 10"
            )

            self.notebook_card.notebook_present.value = form.notebook_present
            self.notebook_card.notebook_present.update()
            self.notebook_card.notebook_work_today.value = form.notebook_work_today
            self.notebook_card.notebook_work_today.update()
            self.notebook_card.notebook_organized.value = form.notebook_organized
            self.notebook_card.notebook_organized.update()
            self.notebook_card.mini_score.set_text(
                "-- / 10" if mode == CHECK_MODE_AGENDA_ONLY else f"{computed.notebook_score} / 10"
            )

            agenda_visible = (not mode_selected) or mode in {CHECK_MODE_BOTH, CHECK_MODE_AGENDA_ONLY}
            notebook_visible = (not mode_selected) or mode in {CHECK_MODE_BOTH, CHECK_MODE_NOTEBOOK_ONLY}
            self.agenda_card.root.visible = agenda_visible
            self.notebook_card.root.visible = notebook_visible
            self.agenda_card.root.update()
            self.notebook_card.root.update()
            if agenda_visible and notebook_visible:
                self.cards_grid.classes(replace="na-cards-grid cards_grid na-cards-three")
            else:
                self.cards_grid.classes(replace="na-cards-grid cards_grid na-cards-two")

            for tag, chip in self.status_card.chip_by_tag.items():
                chip.set_selected(tag in form.selected_comment_tags)

            self.status_card.comment_toggle.value = form.comment_enabled
            self.status_card.comment_toggle.update()
            self.status_card.comment_input.value = form.comments
            self.status_card.comment_input.visible = form.comment_enabled
            self.status_card.comment_input.update()

            self.status_card.auto_flag_chip.set_text(f"{computed.auto_flag}")
            auto_style = self._flag_style(computed.auto_flag)
            self.status_card.auto_flag_chip.style(replace=auto_style)
            self.status_card.deduction_value_label.set_text(f"Deduction: {computed.comment_deduction}")

            self.footer.agenda_value.set_text("--" if mode == CHECK_MODE_NOTEBOOK_ONLY else str(computed.agenda_score))
            self.footer.notebook_value.set_text("--" if mode == CHECK_MODE_AGENDA_ONLY else str(computed.notebook_score))
            self.footer.internal_value.set_text(str(computed.internal_score))
            self.footer.gradebook_value.set_text(str(computed.gradebook_score))

            interaction_enabled = not session.locked and not session.roster_complete
            scoring_enabled = interaction_enabled and mode_selected
            agenda_controls_enabled = scoring_enabled and mode in {CHECK_MODE_BOTH, CHECK_MODE_AGENDA_ONLY}
            notebook_controls_enabled = scoring_enabled and mode in {CHECK_MODE_BOTH, CHECK_MODE_NOTEBOOK_ONLY}
            agenda_details_enabled = agenda_controls_enabled and form.agenda_present
            notebook_details_enabled = notebook_controls_enabled and form.notebook_present
            comment_text_enabled = scoring_enabled and form.comment_enabled

            self._set_enabled(self.header.student_select, interaction_enabled and not session.roster_complete)
            self._set_enabled(self.header.checker_mode_select, interaction_enabled)
            self._set_enabled(
                self.header.checker_student_select,
                interaction_enabled and session.checker_mode == "student" and bool(session.checker_label_by_id),
            )
            self._set_enabled(self.header.date_input, interaction_enabled)
            self._set_enabled(
                self.mode_picker.mode_radio,
                interaction_enabled and not session.check_mode_locked and not session.roster_complete,
            )

            self._set_enabled(self.agenda_card.agenda_present, agenda_controls_enabled)
            self._set_enabled(self.agenda_card.agenda_filled_today, agenda_details_enabled)
            self._set_enabled(self.agenda_card.agenda_readable, agenda_details_enabled)

            self._set_enabled(self.notebook_card.notebook_present, notebook_controls_enabled)
            self._set_enabled(self.notebook_card.notebook_work_today, notebook_details_enabled)
            self._set_enabled(self.notebook_card.notebook_organized, notebook_details_enabled)

            self._set_enabled(self.status_card.comment_toggle, scoring_enabled)
            self._set_enabled(self.status_card.comment_input, comment_text_enabled)
            for chip in self.status_card.chip_by_tag.values():
                self._set_enabled(chip, scoring_enabled)

            self._set_enabled(self.footer.save_button, self.controller.state.can_save)
            self._set_enabled(self.footer.undo_button, self.controller.state.can_undo)

            self._refresh_history_panel()

            self.lock_overlay.root.visible = session.locked
            self.lock_overlay.root.update()
        finally:
            self._syncing = False

    def _set_enabled(self, control: ui.element, enabled: bool) -> None:
        if enabled:
            control.enable()
        else:
            control.disable()

    def _flag_style(self, flag: str) -> str:
        lowered = flag.lower()
        if "missing" in lowered:
            return "background:#fbd5d5;color:#7f1d1d;border:1px solid #dca8a8;"
        if "blank" in lowered or "incomplete" in lowered or "messy" in lowered:
            return "background:#ffe9c2;color:#7a4500;border:1px solid #e1c18b;"
        return "background:#edf2f7;color:#334155;border:1px solid #cbd5e1;"

    def _refresh_history_panel(self) -> None:
        if self.history_panel is None:
            return
        target_student_id = self._history_target_student_id()
        if target_student_id is None:
            self.history_panel.table.rows = []
            self.history_panel.table.update()
            self.history_panel.warning_label.set_text("")
            self.history_panel.warning_label.update()
            return

        start_date = (self.history_panel.start_date_input.value or "").strip() or None
        end_date = (self.history_panel.end_date_input.value or "").strip() or None
        rows, warnings = self.controller.history_rows(
            student_id=target_student_id,
            start_date=start_date,
            end_date=end_date,
            include_with_comments=bool(self.history_panel.include_with_comments.value),
            include_without_comments=bool(self.history_panel.include_without_comments.value),
        )
        mode_label = {
            CHECK_MODE_NOTEBOOK_ONLY: "Notebook only",
            CHECK_MODE_BOTH: "Both",
            CHECK_MODE_AGENDA_ONLY: "Agenda only",
        }
        self.history_panel.table.rows = [
            {
                "date": row.date,
                "student_name": row.student_name,
                "check_mode": mode_label.get(row.check_mode, "Both"),
                "agenda_score": row.agenda_score,
                "notebook_score": row.notebook_score,
                "internal_score": row.internal_score,
                "gradebook_score": row.gradebook_score,
                "comment_deduction": row.comment_deduction,
                "has_comment": "Yes" if row.has_comment else "",
                "comments": row.comments if row.has_comment else "-",
            }
            for row in rows
        ]
        self.history_panel.table.update()
        if warnings:
            self.history_panel.warning_label.set_text(f"{len(warnings)} invalid row(s) skipped in output CSV.")
        else:
            self.history_panel.warning_label.set_text("")
        self.history_panel.warning_label.update()

    def _history_target_student_id(self) -> str | None:
        session = self.controller.state.session
        if session.active_student is not None:
            return session.active_student.student_id
        if session.roster_complete and self.controller.state.save_history:
            return self.controller.state.save_history[-1].record.student_id
        return None

    def _apply_result(self, result, *, notify: bool) -> None:
        if not result.message:
            return
        if notify or result.level != "info":
            notify_type = {
                "info": "positive",
                "warn": "warning",
                "error": "negative",
            }.get(result.level, "positive")
            ui.notify(result.message, type=notify_type)


def build_check_page() -> None:
    page = CheckPage()
    page.build()
