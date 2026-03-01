from __future__ import annotations

from dataclasses import dataclass

from app.nicegui_app.models.ui_state import StatusLevel


@dataclass(frozen=True)
class ActionResult:
    ok: bool
    message: str
    level: StatusLevel = "info"


@dataclass(frozen=True)
class HistoryDisplayRow:
    student_name: str
    date: str
    check_mode: str
    agenda_score: float
    notebook_score: float
    internal_score: float
    gradebook_score: float
    comment_deduction: float
    has_comment: bool
    comments: str
