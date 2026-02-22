from __future__ import annotations

from dataclasses import dataclass

from app.flags import compute_issue_flag
from app.nicegui_app.models.ui_state import ComputedState, FormState
from app.scoring import (
    CHECK_MODE_AGENDA_ONLY,
    CHECK_MODE_BOTH,
    CHECK_MODE_NOTEBOOK_ONLY,
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
    NOTEBOOK_WORK_MISSING,
    NOTEBOOK_WORK_OPTIONS,
    compute_agenda_score_v2,
    compute_comment_deduction,
    compute_mode_totals,
    compute_notebook_score_v2,
    normalize_check_mode,
)


@dataclass(frozen=True)
class TagDefinition:
    tag: str
    label: str
    deduction: float
    category: str


POSITIVE_TAGS: tuple[TagDefinition, ...] = (
    TagDefinition(COMMENT_TAG_EXCEEDS_EXPECTATIONS, "Exceeds expectations", 0.0, "positive"),
    TagDefinition(COMMENT_TAG_MEETS_EXPECTATIONS, "Meets expectations", 0.0, "positive"),
    TagDefinition(COMMENT_TAG_STRONG_EFFORT, "Strong effort", 0.0, "positive"),
    TagDefinition(COMMENT_TAG_IMPROVEMENT_SHOWN, "Improvement shown", 0.0, "positive"),
)

LEGIBILITY_TAGS: tuple[TagDefinition, ...] = (
    TagDefinition(COMMENT_TAG_UNREADABLE, "Unreadable", 1.0, "deduction"),
    TagDefinition(COMMENT_TAG_DIFFICULT_TO_READ, "Difficult to read", 0.5, "deduction"),
    TagDefinition(COMMENT_TAG_DISORGANIZED, "Disorganized", 0.5, "deduction"),
    TagDefinition(COMMENT_TAG_MISSING_DATE, "Missing date", 0.25, "deduction"),
)

COMPLETION_TAGS: tuple[TagDefinition, ...] = (
    TagDefinition(COMMENT_TAG_INCOMPLETE_WORK, "Incomplete work", 5.0, "deduction"),
    TagDefinition(COMMENT_TAG_MISSING_COMPONENTS, "Missing components", 5.0, "deduction"),
)

COMMENT_TAGS_BY_GROUP: dict[str, tuple[TagDefinition, ...]] = {
    "positive": POSITIVE_TAGS,
    "legibility": LEGIBILITY_TAGS,
    "completion": COMPLETION_TAGS,
}


class ScoringService:
    def normalize_form(self, form: FormState) -> FormState:
        form.check_mode = normalize_check_mode(form.check_mode)
        if not form.agenda_present:
            form.agenda_filled_today = AGENDA_FILLED_BLANK
            form.agenda_readable = False
        elif form.agenda_filled_today not in AGENDA_FILLED_OPTIONS:
            form.agenda_filled_today = AGENDA_FILLED_BLANK

        if not form.notebook_present:
            form.notebook_work_today = NOTEBOOK_WORK_MISSING
            form.notebook_organized = False
        elif form.notebook_work_today not in NOTEBOOK_WORK_OPTIONS:
            form.notebook_work_today = NOTEBOOK_WORK_MISSING

        if not form.comment_enabled:
            form.comments = ""

        return form

    def reset_form(self) -> FormState:
        return FormState()

    def compute(self, form: FormState) -> ComputedState:
        normalized = self.normalize_form(form)
        mode = normalize_check_mode(normalized.check_mode)

        agenda_score_raw = compute_agenda_score_v2(
            agenda_present=normalized.agenda_present,
            agenda_filled_today=normalized.agenda_filled_today,
            agenda_readable=normalized.agenda_readable,
        )
        notebook_score_raw = compute_notebook_score_v2(
            notebook_present=normalized.notebook_present,
            notebook_work_today=normalized.notebook_work_today,
            notebook_organized=normalized.notebook_organized,
        )
        agenda_score = 0.0 if mode == CHECK_MODE_NOTEBOOK_ONLY else agenda_score_raw
        notebook_score = 0.0 if mode == CHECK_MODE_AGENDA_ONLY else notebook_score_raw

        negative_tags = [
            tag for tag in sorted(normalized.selected_comment_tags) if tag in NEGATIVE_COMMENT_DEDUCTION_BY_TAG
        ]
        comment_deduction = compute_comment_deduction(negative_tags)

        internal_score, gradebook_score = compute_mode_totals(
            check_mode=mode,
            agenda_score=agenda_score,
            notebook_score=notebook_score,
            deduction=comment_deduction,
        )

        entry_written = normalized.agenda_present and normalized.agenda_filled_today != AGENDA_FILLED_BLANK
        all_subjects_filled = normalized.agenda_present and normalized.agenda_filled_today == AGENDA_FILLED_COMPLETE
        if mode == CHECK_MODE_NOTEBOOK_ONLY:
            organized = normalized.notebook_organized
        elif mode == CHECK_MODE_AGENDA_ONLY:
            organized = normalized.agenda_readable
        else:
            organized = normalized.agenda_readable and normalized.notebook_organized

        auto_flag = compute_issue_flag(
            notebook_score=notebook_score,
            agenda_present=normalized.agenda_present if mode != CHECK_MODE_NOTEBOOK_ONLY else True,
            entry_written=entry_written,
            all_subjects_filled=all_subjects_filled,
            organized=organized,
            check_mode=mode,
        )

        return ComputedState(
            check_mode=mode,
            agenda_score=agenda_score,
            notebook_score=notebook_score,
            comment_deduction=comment_deduction,
            internal_score=internal_score,
            gradebook_score=gradebook_score,
            entry_written=entry_written,
            all_subjects_filled=all_subjects_filled,
            organized=organized,
            auto_flag=auto_flag,
        )
