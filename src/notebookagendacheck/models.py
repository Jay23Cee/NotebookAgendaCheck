from dataclasses import dataclass
from pathlib import Path

from notebookagendacheck.flags import normalize_issue_flag
from notebookagendacheck.scoring import (
    AGENDA_FILLED_BLANK,
    AGENDA_FILLED_COMPLETE,
    AGENDA_FILLED_OPTIONS,
    AGENDA_FILLED_PARTIAL,
    NOTEBOOK_WORK_COMPLETE,
    NOTEBOOK_WORK_MISSING,
    NOTEBOOK_WORK_OPTIONS,
)
from notebookagendacheck.students import Student


CSV_FIELDNAMES = [
    "StudentID",
    "StudentName",
    "Grade",
    "CheckMode",
    "Date",
    "Checker",
    "NotebookScore",
    "AgendaPresent",
    "EntryWritten",
    "AllSubjectsFilled",
    "Organized",
    "AgendaScore",
    "GradebookScore",
    "AgendaFilledToday",
    "AgendaReadable",
    "NotebookPresentDetail",
    "NotebookWorkToday",
    "NotebookOrganized",
    "CommentTags",
    "CommentDeduction",
    "InternalScore",
    "ScoreModel",
    "Flag",
    "Comments",
]


@dataclass(frozen=True)
class SessionConfig:
    checker: str
    check_date: str
    grade: int
    students_file: Path
    output_file: Path


@dataclass(frozen=True)
class CheckRecord:
    student_id: str
    student_name: str
    grade: int
    check_mode: str
    date: str
    checker: str
    notebook_score: float
    agenda_present: bool
    entry_written: bool
    all_subjects_filled: bool
    organized: bool
    agenda_score: int
    gradebook_score: float
    agenda_filled_today: str = AGENDA_FILLED_BLANK
    agenda_readable: bool = False
    notebook_present_detail: bool = False
    notebook_work_today: str = NOTEBOOK_WORK_MISSING
    notebook_organized: bool = False
    comment_tags: str = ""
    comment_deduction: float = 0.0
    internal_score: float = 0.0
    score_model: str = ""
    flag: str = ""
    comments: str = ""

    @classmethod
    def from_student(
        cls,
        student: Student,
        check_date: str,
        checker: str,
        notebook_score: float,
        agenda_present: bool,
        entry_written: bool,
        all_subjects_filled: bool,
        organized: bool,
        agenda_score: int,
        gradebook_score: float,
        agenda_filled_today: str | None = None,
        agenda_readable: bool | None = None,
        notebook_present_detail: bool | None = None,
        notebook_work_today: str | None = None,
        notebook_organized: bool | None = None,
        comment_tags: str = "",
        comment_deduction: float = 0.0,
        internal_score: float = 0.0,
        score_model: str = "",
        flag: str = "",
        comments: str = "",
        check_mode: str = "both",
    ) -> "CheckRecord":
        resolved_notebook_present = bool(notebook_present_detail) if notebook_present_detail is not None else notebook_score > 0
        resolved_agenda_filled = (
            _normalize_agenda_filled_today(agenda_filled_today)
            if agenda_filled_today is not None
            else _derive_agenda_filled_today(
                agenda_present=bool(agenda_present),
                entry_written=bool(entry_written),
                all_subjects_filled=bool(all_subjects_filled),
            )
        )
        resolved_notebook_work = (
            _normalize_notebook_work_today(notebook_work_today)
            if notebook_work_today is not None
            else (NOTEBOOK_WORK_COMPLETE if resolved_notebook_present else NOTEBOOK_WORK_MISSING)
        )
        resolved_agenda_readable = bool(agenda_readable) if agenda_readable is not None else bool(organized)
        resolved_notebook_organized = bool(notebook_organized) if notebook_organized is not None else bool(organized)

        return cls(
            student_id=student.student_id,
            student_name=student.full_name,
            grade=student.grade,
            check_mode=_normalize_check_mode(check_mode),
            date=check_date,
            checker=checker,
            notebook_score=round(float(notebook_score), 2),
            agenda_present=bool(agenda_present),
            entry_written=bool(entry_written),
            all_subjects_filled=bool(all_subjects_filled),
            organized=bool(organized),
            agenda_score=int(agenda_score),
            gradebook_score=round(float(gradebook_score), 2),
            agenda_filled_today=resolved_agenda_filled,
            agenda_readable=resolved_agenda_readable,
            notebook_present_detail=resolved_notebook_present,
            notebook_work_today=resolved_notebook_work,
            notebook_organized=resolved_notebook_organized,
            comment_tags=_normalize_comment_tags(comment_tags),
            comment_deduction=round(float(comment_deduction), 2),
            internal_score=round(float(internal_score), 2),
            score_model=score_model.strip(),
            flag=normalize_issue_flag(flag),
            comments=comments.strip(),
        )

    def to_csv_row(self) -> dict[str, str | int | float | bool]:
        return {
            "StudentID": self.student_id,
            "StudentName": self.student_name,
            "Grade": self.grade,
            "CheckMode": self.check_mode,
            "Date": self.date,
            "Checker": self.checker,
            "NotebookScore": self.notebook_score,
            "AgendaPresent": self.agenda_present,
            "EntryWritten": self.entry_written,
            "AllSubjectsFilled": self.all_subjects_filled,
            "Organized": self.organized,
            "AgendaScore": self.agenda_score,
            "GradebookScore": self.gradebook_score,
            "AgendaFilledToday": self.agenda_filled_today,
            "AgendaReadable": self.agenda_readable,
            "NotebookPresentDetail": self.notebook_present_detail,
            "NotebookWorkToday": self.notebook_work_today,
            "NotebookOrganized": self.notebook_organized,
            "CommentTags": self.comment_tags,
            "CommentDeduction": self.comment_deduction,
            "InternalScore": self.internal_score,
            "ScoreModel": self.score_model,
            "Flag": self.flag,
            "Comments": self.comments,
        }

    @classmethod
    def from_csv_row(cls, row: dict[str, str]) -> "CheckRecord":
        agenda_present = _parse_bool(row["AgendaPresent"])
        entry_written = _parse_bool(row["EntryWritten"])
        all_subjects_filled = _parse_bool(row["AllSubjectsFilled"])
        organized = _parse_bool(row["Organized"])
        notebook_score = float(row["NotebookScore"])
        gradebook_score = float(row["GradebookScore"])

        agenda_filled_today = _parse_text(row.get("AgendaFilledToday"))
        if agenda_filled_today:
            normalized_agenda_filled = _normalize_agenda_filled_today(agenda_filled_today)
        else:
            normalized_agenda_filled = _derive_agenda_filled_today(
                agenda_present=agenda_present,
                entry_written=entry_written,
                all_subjects_filled=all_subjects_filled,
            )

        notebook_present_detail_raw = _parse_text(row.get("NotebookPresentDetail"))
        notebook_present_detail = (
            _parse_bool(notebook_present_detail_raw)
            if notebook_present_detail_raw != ""
            else notebook_score > 0
        )

        notebook_work_today = _parse_text(row.get("NotebookWorkToday"))
        if notebook_work_today:
            normalized_notebook_work = _normalize_notebook_work_today(notebook_work_today)
        else:
            normalized_notebook_work = NOTEBOOK_WORK_COMPLETE if notebook_present_detail else NOTEBOOK_WORK_MISSING

        agenda_readable_raw = _parse_text(row.get("AgendaReadable"))
        agenda_readable = _parse_bool(agenda_readable_raw) if agenda_readable_raw != "" else organized

        notebook_organized_raw = _parse_text(row.get("NotebookOrganized"))
        notebook_organized = _parse_bool(notebook_organized_raw) if notebook_organized_raw != "" else organized

        comment_deduction = _parse_float(row.get("CommentDeduction"), default=0.0)
        internal_score_raw = _parse_text(row.get("InternalScore"))
        if internal_score_raw != "":
            internal_score = round(float(internal_score_raw), 2)
        else:
            internal_score = round(gradebook_score if gradebook_score > 10 else gradebook_score * 2, 2)

        return cls(
            student_id=row["StudentID"],
            student_name=row["StudentName"],
            grade=int(row["Grade"]),
            check_mode=_normalize_check_mode(_parse_text(row.get("CheckMode"))),
            date=row["Date"],
            checker=row["Checker"],
            notebook_score=notebook_score,
            agenda_present=agenda_present,
            entry_written=entry_written,
            all_subjects_filled=all_subjects_filled,
            organized=organized,
            agenda_score=int(float(row["AgendaScore"])),
            gradebook_score=gradebook_score,
            agenda_filled_today=normalized_agenda_filled,
            agenda_readable=agenda_readable,
            notebook_present_detail=notebook_present_detail,
            notebook_work_today=normalized_notebook_work,
            notebook_organized=notebook_organized,
            comment_tags=_normalize_comment_tags(_parse_text(row.get("CommentTags"))),
            comment_deduction=comment_deduction,
            internal_score=internal_score,
            score_model=_parse_text(row.get("ScoreModel")),
            flag=normalize_issue_flag(_parse_text(row.get("Flag"))),
            comments=_parse_text(row.get("Comments")),
        )


def _parse_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "y"}:
        return True
    if normalized in {"0", "false", "no", "n", ""}:
        return False
    raise ValueError(f"Invalid boolean value: {value}")


def _parse_text(value: str | None) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _parse_float(value: str | None, default: float) -> float:
    cleaned = _parse_text(value)
    if cleaned == "":
        return default
    return float(cleaned)


def _normalize_agenda_filled_today(value: str) -> str:
    cleaned = value.strip().lower()
    if cleaned in AGENDA_FILLED_OPTIONS:
        return cleaned
    raise ValueError(f"Invalid AgendaFilledToday value: {value}")


def _normalize_notebook_work_today(value: str) -> str:
    cleaned = value.strip().lower()
    if cleaned in NOTEBOOK_WORK_OPTIONS:
        return cleaned
    raise ValueError(f"Invalid NotebookWorkToday value: {value}")


def _normalize_comment_tags(value: str) -> str:
    if not value.strip():
        return ""

    tags: list[str] = []
    seen: set[str] = set()
    for raw_tag in value.split("|"):
        tag = raw_tag.strip()
        if not tag or tag in seen:
            continue
        seen.add(tag)
        tags.append(tag)
    return "|".join(tags)


def _normalize_check_mode(value: str) -> str:
    cleaned = value.strip().lower()
    if cleaned in {"", "both"}:
        return "both"
    if cleaned in {"notebook_only", "agenda_only"}:
        return cleaned
    return "both"


def _derive_agenda_filled_today(*, agenda_present: bool, entry_written: bool, all_subjects_filled: bool) -> str:
    if not agenda_present:
        return AGENDA_FILLED_BLANK
    if all_subjects_filled:
        return AGENDA_FILLED_COMPLETE
    if entry_written:
        return AGENDA_FILLED_PARTIAL
    return AGENDA_FILLED_BLANK

