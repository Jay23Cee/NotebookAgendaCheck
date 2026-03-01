from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

AgendaEntryStatus = Literal["complete", "partial", "blank"]
NotebookNotesStatus = Literal["complete", "partial", "missing"]
NotebookQualityStatus = Literal["full", "partial", "none"]


@dataclass(frozen=True)
class RosterStudent:
    grade: str
    period: str
    subject: str
    student_id: str
    student_name: str


@dataclass
class CheckFormState:
    agenda_present: bool = True
    agenda_entry_status: AgendaEntryStatus = "complete"
    agenda_legible: bool = True
    nb_present: bool = True
    nb_date_status: NotebookQualityStatus = "full"
    nb_title_status: NotebookQualityStatus = "full"
    nb_notes_status: NotebookNotesStatus = "complete"
    nb_organization_status: NotebookQualityStatus = "full"
    nb_legibility_status: NotebookQualityStatus = "full"
    tags: list[str] = field(default_factory=list)
    comment_checks: list[str] = field(default_factory=list)
    comment_text: str = ""


@dataclass(frozen=True)
class ScoreBreakdown:
    agenda_score: float
    notebook_score: float
    status_score: float
    comment_deduction: float
    total_score: float
    gradebook_score: float
    auto_flag: str
