from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from app.flags import NO_ISSUE_FLAG
from app.models import CheckRecord
from app.scoring import (
    AGENDA_FILLED_BLANK,
    CHECK_MODE_BOTH,
    CHECK_MODE_OPTIONS,
    NOTEBOOK_WORK_MISSING,
)
from app.students import Student

StatusLevel = Literal["info", "warn", "error"]
CheckerMode = Literal["teacher", "student"]
CheckMode = Literal["notebook_only", "both", "agenda_only"]


@dataclass(frozen=True)
class SaveHistoryEntry:
    index_before_save: int
    record: CheckRecord


@dataclass
class SessionState:
    grade: int | None = None
    check_date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    check_mode: CheckMode | None = None
    check_mode_locked: bool = False
    checker_mode: CheckerMode = "teacher"
    checker_id: str | None = None
    checker_name_by_id: dict[str, str] = field(default_factory=dict)
    checker_label_by_id: dict[str, str] = field(default_factory=dict)
    roster: list[Student] = field(default_factory=list)
    current_index: int = 0
    locked: bool = True

    @property
    def active_student(self) -> Student | None:
        if not self.roster:
            return None
        if self.current_index < 0 or self.current_index >= len(self.roster):
            return None
        return self.roster[self.current_index]

    @property
    def roster_complete(self) -> bool:
        return bool(self.roster) and self.current_index >= len(self.roster)

    @property
    def progress_text(self) -> str:
        total = len(self.roster)
        if total == 0:
            return "Student 0 of 0"
        current = min(self.current_index + 1, total)
        return f"Student {current} of {total}"

    @property
    def student_heading(self) -> str:
        if not self.roster:
            return "No roster loaded"
        if self.roster_complete:
            return "Roster complete"
        student = self.roster[self.current_index]
        return f"{student.last_name}, {student.first_name} ({student.student_id})"

    @property
    def student_options(self) -> dict[str, str]:
        return {
            str(index): f"{student.last_name}, {student.first_name} ({student.student_id})"
            for index, student in enumerate(self.roster)
        }

    @property
    def checker_ready(self) -> bool:
        if self.checker_mode == "teacher":
            return True
        if not self.checker_id:
            return False
        return self.checker_id in self.checker_name_by_id


@dataclass
class FormState:
    check_mode: CheckMode = CHECK_MODE_BOTH
    agenda_present: bool = False
    agenda_filled_today: str = AGENDA_FILLED_BLANK
    agenda_readable: bool = False
    notebook_present: bool = False
    notebook_work_today: str = NOTEBOOK_WORK_MISSING
    notebook_organized: bool = False
    selected_comment_tags: set[str] = field(default_factory=set)
    comment_enabled: bool = False
    comments: str = ""


@dataclass
class ComputedState:
    check_mode: CheckMode = CHECK_MODE_BOTH
    agenda_score: float = 0.0
    notebook_score: float = 0.0
    comment_deduction: float = 0.0
    internal_score: float = 0.0
    gradebook_score: float = 0.0
    entry_written: bool = False
    all_subjects_filled: bool = False
    organized: bool = False
    auto_flag: str = NO_ISSUE_FLAG


@dataclass
class ViewState:
    session: SessionState = field(default_factory=SessionState)
    form: FormState = field(default_factory=FormState)
    computed: ComputedState = field(default_factory=ComputedState)
    status_message: str = "Select Grade to begin."
    status_level: StatusLevel = "info"
    save_history: list[SaveHistoryEntry] = field(default_factory=list)
    last_save_at: float = 0.0
    save_in_progress: bool = False
    shortcuts_suspended: bool = False

    @property
    def can_save(self) -> bool:
        return (
            not self.session.locked
            and not self.session.roster_complete
            and not self.save_in_progress
            and self.session.checker_ready
            and self.session.check_mode in CHECK_MODE_OPTIONS
        )

    @property
    def can_undo(self) -> bool:
        return not self.session.locked and bool(self.save_history)
