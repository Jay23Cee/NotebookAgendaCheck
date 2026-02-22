from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from pathlib import Path
import time

from app.constants import DEFAULT_OUTPUT_FILE, DEFAULT_STUDENTS_FILE
from app.models import CheckRecord
from app.nicegui_app.models.ui_events import ActionResult, HistoryDisplayRow
from app.nicegui_app.models.ui_state import CheckerMode, FormState, SaveHistoryEntry, StatusLevel, ViewState
from app.nicegui_app.services.history_service import HistoryService
from app.nicegui_app.services.persistence_service import PersistenceService
from app.nicegui_app.services.roster_service import RosterService
from app.nicegui_app.services.scoring_service import ScoringService
from app.scoring import (
    AGENDA_FILLED_BLANK,
    AGENDA_FILLED_COMPLETE,
    CHECK_MODE_AGENDA_ONLY,
    CHECK_MODE_BOTH,
    CHECK_MODE_NOTEBOOK_ONLY,
    CHECK_MODE_OPTIONS,
    NOTEBOOK_WORK_MISSING,
    SCORE_MODEL_INTERNAL20_GRADEBOOK10_V1,
    normalize_check_mode,
)

CHECKER_NAME_TEACHER = "TEACHER"


class NAWorkflowController:
    def __init__(
        self,
        *,
        students_file: Path = DEFAULT_STUDENTS_FILE,
        output_file: Path = DEFAULT_OUTPUT_FILE,
        roster_service: RosterService | None = None,
        scoring_service: ScoringService | None = None,
        persistence_service: PersistenceService | None = None,
        history_service: HistoryService | None = None,
    ) -> None:
        self.students_file = students_file
        self.output_file = output_file
        self.roster_service = roster_service or RosterService(students_file)
        self.scoring_service = scoring_service or ScoringService()
        self.persistence_service = persistence_service or PersistenceService(output_file)
        self.history_service = history_service or HistoryService()

        self.state = ViewState()
        self._refresh_scores()

    def export_view_state(self) -> dict[str, object]:
        return asdict(self.state)

    def set_grade(self, grade_value: str | int | None) -> ActionResult:
        if grade_value in (None, ""):
            self.state.session.grade = None
            return self._reset_class_context()

        try:
            self.state.session.grade = int(str(grade_value).strip())
        except ValueError:
            return self._set_status("Grade must be a valid number.", level="error")
        return self._reload_class_context()

    def set_check_mode(self, mode_value: str | None) -> ActionResult:
        if self.state.session.locked:
            return self._set_status("Select Grade to load class roster first.", level="error")
        if self.state.session.check_mode_locked:
            return self._set_status("Check mode is locked after first save.", level="warn")

        normalized = str(mode_value or "").strip().lower()
        if normalized not in CHECK_MODE_OPTIONS:
            return self._set_status("Select Notebook-only, Both, or Agenda-only mode.", level="warn")

        self.state.session.check_mode = normalized
        self.state.form.check_mode = normalize_check_mode(normalized)
        self._refresh_scores()
        return self._set_status("Check mode updated.", level="info")

    def set_date(self, check_date: str) -> ActionResult:
        normalized = str(check_date).strip()
        try:
            self._validate_date(normalized)
        except ValueError:
            return self._set_status("Date must use MM/DD/YYYY.", level="error")
        self.state.session.check_date = normalized
        return self._set_status("Date updated.", level="info")

    def set_checker_mode(self, mode_value: str) -> ActionResult:
        normalized = str(mode_value).strip().lower()
        if normalized not in {"teacher", "student"}:
            return self._set_status("User mode must be Teacher or Student.", level="error")

        mode: CheckerMode = "teacher" if normalized == "teacher" else "student"
        self.state.session.checker_mode = mode
        self.state.session.checker_id = None

        if mode == "teacher":
            return self._set_status("Checker set to TEACHER.", level="info")
        return self._set_status("Select student checker from this class roster.", level="warn")

    def set_checker_student(self, checker_id: str | None) -> ActionResult:
        if self.state.session.checker_mode != "student":
            self.state.session.checker_id = None
            return self._set_status("User mode is Teacher.", level="info")

        resolved_id = (checker_id or "").strip() or None
        if resolved_id is None:
            self.state.session.checker_id = None
            return self._set_status("Select student checker from this class roster.", level="warn")

        if resolved_id not in self.state.session.checker_name_by_id:
            return self._set_status("Select a valid student checker from this class roster.", level="error")

        self.state.session.checker_id = resolved_id
        return self._set_status("Student checker updated.", level="info")

    def set_checker(self, checker_id: str | None) -> ActionResult:
        return self.set_checker_student(checker_id)

    def select_student(self, student_index: str | int) -> ActionResult:
        if self.state.session.locked or not self.state.session.roster:
            return self._set_status("Select Grade to load class roster first.", level="error")

        try:
            index = int(str(student_index).strip())
        except ValueError:
            return self._set_status("Selected student index is invalid.", level="error")

        if index < 0 or index >= len(self.state.session.roster):
            return self._set_status("Selected student is out of range.", level="error")

        self.state.session.current_index = index
        self._reset_form_state()
        student = self.state.session.roster[index]
        return self._set_status(f"Ready for {student.full_name}.", level="info")

    def set_agenda_present(self, value: bool) -> None:
        self.state.form.agenda_present = bool(value)
        if not self.state.form.agenda_present:
            self.state.form.agenda_readable = False
        self._refresh_scores()

    def set_agenda_filled_today(self, value: str) -> None:
        self.state.form.agenda_filled_today = str(value).strip().lower()
        self._refresh_scores()

    def set_agenda_readable(self, value: bool) -> None:
        self.state.form.agenda_readable = bool(value)
        self._refresh_scores()

    def set_notebook_present(self, value: bool) -> None:
        self.state.form.notebook_present = bool(value)
        if not self.state.form.notebook_present:
            self.state.form.notebook_organized = False
        self._refresh_scores()

    def set_notebook_work_today(self, value: str) -> None:
        self.state.form.notebook_work_today = str(value).strip().lower()
        self._refresh_scores()

    def set_notebook_organized(self, value: bool) -> None:
        self.state.form.notebook_organized = bool(value)
        self._refresh_scores()

    def toggle_comment_tag(self, tag: str, selected: bool) -> None:
        if selected:
            self.state.form.selected_comment_tags.add(tag)
        else:
            self.state.form.selected_comment_tags.discard(tag)
        self._refresh_scores()

    def set_comment_enabled(self, enabled: bool) -> None:
        self.state.form.comment_enabled = bool(enabled)
        if not self.state.form.comment_enabled:
            self.state.form.comments = ""
        self._refresh_scores()

    def set_comment_text(self, comments: str) -> None:
        self.state.form.comments = str(comments)
        self._refresh_scores()

    def save_next(self) -> ActionResult:
        if self.state.session.locked or not self.state.session.roster:
            return self._set_status("Select grade to auto-load roster before saving.", level="error")
        if self.state.session.roster_complete:
            return self._set_status("All students already saved for this roster.", level="info")
        if self.state.session.check_mode not in CHECK_MODE_OPTIONS:
            return self._set_status("Select a check mode before saving.", level="error")

        now = time.monotonic()
        if now - self.state.last_save_at < 0.35:
            return ActionResult(ok=False, message="", level="info")
        self.state.last_save_at = now

        self.state.save_in_progress = True
        try:
            self._validate_date(self.state.session.check_date)
            checker_name = self._selected_checker_name(strict=True)
            assert checker_name is not None

            if self.state.form.comment_enabled and not (
                self.state.form.selected_comment_tags or self.state.form.comments.strip()
            ):
                self.state.form.comment_enabled = False
                self.state.form.comments = ""
                self._refresh_scores()

            student = self.state.session.roster[self.state.session.current_index]
            comment_text = self.state.form.comments.strip() if self.state.form.comment_enabled else ""
            mode = normalize_check_mode(self.state.session.check_mode)

            agenda_present = self.state.form.agenda_present
            agenda_filled_today = self.state.form.agenda_filled_today
            agenda_readable = self.state.form.agenda_readable
            notebook_present = self.state.form.notebook_present
            notebook_work_today = self.state.form.notebook_work_today
            notebook_organized = self.state.form.notebook_organized
            if mode == CHECK_MODE_NOTEBOOK_ONLY:
                agenda_present = False
                agenda_filled_today = AGENDA_FILLED_BLANK
                agenda_readable = False
            elif mode == CHECK_MODE_AGENDA_ONLY:
                notebook_present = False
                notebook_work_today = NOTEBOOK_WORK_MISSING
                notebook_organized = False

            record = CheckRecord.from_student(
                student=student,
                check_date=self.state.session.check_date,
                checker=checker_name,
                notebook_score=self.state.computed.notebook_score,
                agenda_present=agenda_present,
                entry_written=agenda_present and agenda_filled_today != AGENDA_FILLED_BLANK,
                all_subjects_filled=agenda_present and agenda_filled_today == AGENDA_FILLED_COMPLETE,
                organized=self.state.computed.organized,
                agenda_score=int(round(self.state.computed.agenda_score)),
                gradebook_score=self.state.computed.gradebook_score,
                agenda_filled_today=agenda_filled_today,
                agenda_readable=agenda_readable,
                notebook_present_detail=notebook_present,
                notebook_work_today=notebook_work_today,
                notebook_organized=notebook_organized,
                comment_tags="|".join(sorted(self.state.form.selected_comment_tags)),
                comment_deduction=self.state.computed.comment_deduction,
                internal_score=self.state.computed.internal_score,
                score_model=SCORE_MODEL_INTERNAL20_GRADEBOOK10_V1,
                flag=self.state.computed.auto_flag,
                comments=comment_text,
                check_mode=mode,
            )
            self.persistence_service.append(record)
            self.state.save_history.append(
                SaveHistoryEntry(index_before_save=self.state.session.current_index, record=record)
            )
            self.state.session.check_mode_locked = True

            saved_name = student.full_name
            self.state.session.current_index += 1
            self._reset_form_state()

            if self.state.session.roster_complete:
                return self._set_status(f"Saved final student. Output: {self.output_file}", level="info")
            return self._set_status(f"Saved {saved_name}.", level="info")
        except Exception as exc:  # noqa: BLE001
            return self._set_status(str(exc), level="error")
        finally:
            self.state.save_in_progress = False

    def undo_last(self) -> ActionResult:
        if self.state.session.grade is None:
            return self._set_status("No active session to undo.", level="error")
        if not self.state.save_history:
            return self._set_status("Nothing to undo.", level="error")

        removed = self.persistence_service.undo_last()
        if not removed:
            return self._set_status("Could not undo because output file has no rows.", level="error")

        history_entry = self.state.save_history.pop()
        self.state.session.current_index = history_entry.index_before_save
        self._load_record_into_form(history_entry.record)
        if not self.state.save_history:
            self.state.session.check_mode_locked = False
        self._refresh_scores()
        return self._set_status("Undid last saved student.", level="info")

    def history_rows(
        self,
        *,
        student_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        include_with_comments: bool = True,
        include_without_comments: bool = True,
    ) -> tuple[list[HistoryDisplayRow], list[str]]:
        grade = self.state.session.grade
        if grade is None:
            return [], []
        result = self.persistence_service.load_for_class(
            grade=grade,
            student_id=student_id,
            start_date=start_date,
            end_date=end_date,
        )
        rows = self.history_service.to_display_rows(result.records, limit=50)
        if include_with_comments and include_without_comments:
            return rows, result.warnings
        if not include_with_comments and not include_without_comments:
            return [], result.warnings

        filtered_rows = [
            row
            for row in rows
            if (include_with_comments and row.has_comment) or (include_without_comments and not row.has_comment)
        ]
        return filtered_rows, result.warnings

    def _reload_class_context(self) -> ActionResult:
        grade = self.state.session.grade
        if grade is None:
            return self._reset_class_context()

        try:
            roster = self.roster_service.class_roster(grade=grade)
        except Exception as exc:  # noqa: BLE001
            self.state.session.locked = True
            self.state.session.roster = []
            self.state.session.current_index = 0
            self.state.session.check_mode = None
            self.state.session.check_mode_locked = False
            self.state.session.checker_mode = "teacher"
            self.state.session.checker_id = None
            self.state.session.checker_name_by_id = {}
            self.state.session.checker_label_by_id = {}
            self._reset_form_state()
            return self._set_status(str(exc), level="error")

        if not roster:
            self.state.session.locked = True
            self.state.session.roster = []
            self.state.session.current_index = 0
            self.state.session.check_mode = None
            self.state.session.check_mode_locked = False
            self.state.session.checker_mode = "teacher"
            self.state.session.checker_id = None
            self.state.session.checker_name_by_id = {}
            self.state.session.checker_label_by_id = {}
            self._reset_form_state()
            return self._set_status(
                f"No students found for grade {grade}.",
                level="error",
            )

        checker_name_by_id, checker_label_by_id = self.roster_service.checker_options(
            grade=grade,
        )
        self.state.session.roster = roster
        self.state.session.current_index = 0
        self.state.session.locked = False
        self.state.session.check_mode = None
        self.state.session.check_mode_locked = False
        self.state.session.checker_mode = "teacher"
        self.state.session.checker_id = None
        self.state.session.checker_name_by_id = checker_name_by_id
        self.state.session.checker_label_by_id = checker_label_by_id

        self.state.save_history = []
        self._reset_form_state()

        return self._set_status(
            f"Loaded {len(roster)} students for Grade {grade}. Select check mode.",
            level="info",
        )

    def _reset_class_context(self) -> ActionResult:
        self.state.session.locked = True
        self.state.session.roster = []
        self.state.session.current_index = 0
        self.state.session.check_mode = None
        self.state.session.check_mode_locked = False
        self.state.session.checker_mode = "teacher"
        self.state.session.checker_id = None
        self.state.session.checker_name_by_id = {}
        self.state.session.checker_label_by_id = {}
        self.state.save_history = []
        self._reset_form_state()
        return self._set_status("Select Grade to begin.", level="info")

    def _selected_checker_name(self, *, strict: bool) -> str | None:
        if self.state.session.checker_mode == "teacher":
            return CHECKER_NAME_TEACHER

        checker_id = self.state.session.checker_id
        if not checker_id:
            if strict:
                raise ValueError("Select student checker from this class roster.")
            return None

        checker_name = self.state.session.checker_name_by_id.get(checker_id)
        if checker_name is None and strict:
            raise ValueError("Select a valid student checker from this class roster.")
        return checker_name

    def _validate_date(self, value: str) -> None:
        datetime.strptime(value, "%m/%d/%Y")

    def _load_record_into_form(self, record: CheckRecord) -> None:
        self.state.session.check_mode = normalize_check_mode(record.check_mode)
        self.state.form = FormState(
            check_mode=normalize_check_mode(record.check_mode),
            agenda_present=record.agenda_present,
            agenda_filled_today=record.agenda_filled_today,
            agenda_readable=record.agenda_readable,
            notebook_present=record.notebook_present_detail,
            notebook_work_today=record.notebook_work_today,
            notebook_organized=record.notebook_organized,
            selected_comment_tags={tag.strip() for tag in record.comment_tags.split("|") if tag.strip()},
            comment_enabled=bool(record.comments.strip()),
            comments=record.comments.strip(),
        )

    def _reset_form_state(self) -> None:
        self.state.form = self.scoring_service.reset_form()
        self.state.form.check_mode = normalize_check_mode(self.state.session.check_mode)
        self._refresh_scores()

    def _refresh_scores(self) -> None:
        self.state.form.check_mode = normalize_check_mode(self.state.session.check_mode)
        self.state.form = self.scoring_service.normalize_form(self.state.form)
        self.state.computed = self.scoring_service.compute(self.state.form)

    def _set_status(self, message: str, *, level: StatusLevel) -> ActionResult:
        self.state.status_message = message
        self.state.status_level = level
        return ActionResult(ok=level != "error", message=message, level=level)
