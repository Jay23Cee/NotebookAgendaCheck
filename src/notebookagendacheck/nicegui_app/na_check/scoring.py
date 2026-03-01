from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from notebookagendacheck.flags import compute_issue_flag
from notebookagendacheck.nicegui_app.na_check.models import CheckFormState, ScoreBreakdown
from notebookagendacheck.scoring import (
    CHECK_MODE_BOTH,
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
    compute_comment_deduction,
    compute_mode_totals,
)

AGENDA_ENTRY_POINTS = {
    "complete": 3.0,
    "partial": 1.5,
    "blank": 0.0,
}

NB_ONE_POINT_STATUS = {
    "full": 1.0,
    "partial": 0.5,
    "none": 0.0,
}

NB_TWO_POINT_STATUS = {
    "full": 2.0,
    "partial": 1.0,
    "none": 0.0,
}

NB_NOTES_POINTS = {
    "complete": 3.0,
    "partial": 1.5,
    "missing": 0.0,
}


@dataclass(frozen=True)
class TagDefinition:
    tag: str
    label: str
    deduction: float


TAG_DEFINITIONS: tuple[TagDefinition, ...] = (
    TagDefinition(COMMENT_TAG_EXCEEDS_EXPECTATIONS, "Exceeds expectations", 0.0),
    TagDefinition(COMMENT_TAG_MEETS_EXPECTATIONS, "Meets expectations", 0.0),
    TagDefinition(COMMENT_TAG_STRONG_EFFORT, "Strong effort", 0.0),
    TagDefinition(COMMENT_TAG_IMPROVEMENT_SHOWN, "Improvement shown", 0.0),
    TagDefinition(COMMENT_TAG_UNREADABLE, "Unreadable", 1.0),
    TagDefinition(COMMENT_TAG_DIFFICULT_TO_READ, "Difficult to read", 0.5),
    TagDefinition(COMMENT_TAG_DISORGANIZED, "Disorganized", 0.5),
    TagDefinition(COMMENT_TAG_MISSING_DATE, "Missing date", 0.25),
    TagDefinition(COMMENT_TAG_INCOMPLETE_WORK, "Incomplete work", 5.0),
    TagDefinition(COMMENT_TAG_MISSING_COMPONENTS, "Missing components", 5.0),
)

TAG_LABEL_BY_KEY: dict[str, str] = {item.tag: item.label for item in TAG_DEFINITIONS}

COMMENT_PRESETS: tuple[str, ...] = (
    "Very neat",
    "Credit with reminder",
    "Needs attention",
    "Incomplete today",
)


def default_form_state() -> CheckFormState:
    return CheckFormState()


def apply_auto_rules(form: CheckFormState) -> CheckFormState:
    normalized = deepcopy(form)

    if not normalized.agenda_present:
        normalized.agenda_entry_status = "blank"
        normalized.agenda_legible = False

    if not normalized.nb_present:
        normalized.nb_date_status = "none"
        normalized.nb_title_status = "none"
        normalized.nb_notes_status = "missing"
        normalized.nb_organization_status = "none"
        normalized.nb_legibility_status = "none"

    normalized.tags = _dedupe_ordered(normalized.tags)
    normalized.comment_checks = _dedupe_ordered(normalized.comment_checks)
    return normalized


def score_form(form: CheckFormState) -> ScoreBreakdown:
    normalized = apply_auto_rules(form)

    agenda_score = (
        (4.0 if normalized.agenda_present else 0.0)
        + AGENDA_ENTRY_POINTS[normalized.agenda_entry_status]
        + (3.0 if normalized.agenda_legible else 0.0)
    )

    notebook_score = (
        (1.0 if normalized.nb_present else 0.0)
        + NB_ONE_POINT_STATUS[normalized.nb_date_status]
        + NB_ONE_POINT_STATUS[normalized.nb_title_status]
        + NB_NOTES_POINTS[normalized.nb_notes_status]
        + NB_TWO_POINT_STATUS[normalized.nb_organization_status]
        + NB_TWO_POINT_STATUS[normalized.nb_legibility_status]
    )

    selected_negative_tags = [
        tag for tag in normalized.tags if tag in NEGATIVE_COMMENT_DEDUCTION_BY_TAG
    ]
    comment_deduction = compute_comment_deduction(selected_negative_tags)

    internal_total, gradebook_score = compute_mode_totals(
        check_mode=CHECK_MODE_BOTH,
        agenda_score=agenda_score,
        notebook_score=notebook_score,
        deduction=comment_deduction,
    )

    entry_written = normalized.agenda_present and normalized.agenda_entry_status != "blank"
    all_subjects_filled = normalized.agenda_present and normalized.agenda_entry_status == "complete"
    organized = (
        normalized.agenda_legible
        and normalized.nb_organization_status != "none"
        and normalized.nb_legibility_status != "none"
    )
    auto_flag = compute_issue_flag(
        notebook_score=notebook_score,
        agenda_present=normalized.agenda_present,
        entry_written=entry_written,
        all_subjects_filled=all_subjects_filled,
        organized=organized,
        check_mode=CHECK_MODE_BOTH,
    )

    return ScoreBreakdown(
        agenda_score=round(agenda_score, 2),
        notebook_score=round(notebook_score, 2),
        status_score=round(-comment_deduction, 2),
        comment_deduction=round(comment_deduction, 2),
        total_score=round(internal_total, 2),
        gradebook_score=round(gradebook_score, 2),
        auto_flag=auto_flag,
    )


def _dedupe_ordered(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for raw_value in values:
        value = str(raw_value).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped

