from dataclasses import dataclass


AGENDA_FILLED_COMPLETE = "complete"
AGENDA_FILLED_PARTIAL = "partial"
AGENDA_FILLED_BLANK = "blank"
AGENDA_FILLED_OPTIONS = (
    AGENDA_FILLED_COMPLETE,
    AGENDA_FILLED_PARTIAL,
    AGENDA_FILLED_BLANK,
)

NOTEBOOK_WORK_COMPLETE = "complete"
NOTEBOOK_WORK_PARTIAL = "partial"
NOTEBOOK_WORK_MISSING = "missing"
NOTEBOOK_WORK_OPTIONS = (
    NOTEBOOK_WORK_COMPLETE,
    NOTEBOOK_WORK_PARTIAL,
    NOTEBOOK_WORK_MISSING,
)

COMMENT_TAG_EXCEEDS_EXPECTATIONS = "Exceeds_Expectations"
COMMENT_TAG_MEETS_EXPECTATIONS = "Meets_Expectations"
COMMENT_TAG_STRONG_EFFORT = "Strong_Effort"
COMMENT_TAG_IMPROVEMENT_SHOWN = "Improvement_Shown"
COMMENT_TAG_UNREADABLE = "Unreadable"
COMMENT_TAG_DIFFICULT_TO_READ = "Difficult_To_Read"
COMMENT_TAG_DISORGANIZED = "Disorganized"
COMMENT_TAG_MISSING_DATE = "Missing_Date"
COMMENT_TAG_INCOMPLETE_WORK = "Incomplete_Work"
COMMENT_TAG_MISSING_COMPONENTS = "Missing_Components"

POSITIVE_COMMENT_TAGS = (
    COMMENT_TAG_EXCEEDS_EXPECTATIONS,
    COMMENT_TAG_MEETS_EXPECTATIONS,
    COMMENT_TAG_STRONG_EFFORT,
    COMMENT_TAG_IMPROVEMENT_SHOWN,
)

NEGATIVE_COMMENT_DEDUCTION_BY_TAG = {
    COMMENT_TAG_UNREADABLE: 1.0,
    COMMENT_TAG_DIFFICULT_TO_READ: 0.5,
    COMMENT_TAG_DISORGANIZED: 0.5,
    COMMENT_TAG_MISSING_DATE: 0.25,
    COMMENT_TAG_INCOMPLETE_WORK: 5.0,
    COMMENT_TAG_MISSING_COMPONENTS: 5.0,
}

SCORE_MODEL_INTERNAL20_GRADEBOOK10_V1 = "internal20_gradebook10_v1"
MAX_COMMENT_DEDUCTION = 5.0

CHECK_MODE_BOTH = "both"
CHECK_MODE_NOTEBOOK_ONLY = "notebook_only"
CHECK_MODE_AGENDA_ONLY = "agenda_only"
CHECK_MODE_OPTIONS = (
    CHECK_MODE_NOTEBOOK_ONLY,
    CHECK_MODE_BOTH,
    CHECK_MODE_AGENDA_ONLY,
)


@dataclass(frozen=True)
class AgendaInput:
    agenda_present: bool
    entry_written: bool = False
    all_subjects_filled: bool = False
    organized: bool = False


@dataclass(frozen=True)
class AgendaScoreResult:
    agenda_present: bool
    entry_written: bool
    all_subjects_filled: bool
    organized: bool
    agenda_score: int
    auto_zero_reason: str = ""


@dataclass(frozen=True)
class QuickModeInput:
    agenda_present: bool
    acceptable_today: bool
    manual_score_if_not_acceptable: int | None = None


def compute_agenda_score_v2(*, agenda_present: bool, agenda_filled_today: str, agenda_readable: bool) -> float:
    normalized_filled = _normalize_choice(
        value=agenda_filled_today,
        valid_options=AGENDA_FILLED_OPTIONS,
        label="Agenda filled today",
    )
    if not agenda_present:
        return 0.0

    filled_points = {
        AGENDA_FILLED_COMPLETE: 4.0,
        AGENDA_FILLED_PARTIAL: 2.0,
        AGENDA_FILLED_BLANK: 0.0,
    }[normalized_filled]
    readable_points = 2.0 if agenda_readable else 0.0
    return round(4.0 + filled_points + readable_points, 2)


def compute_notebook_score_v2(*, notebook_present: bool, notebook_work_today: str, notebook_organized: bool) -> float:
    normalized_work = _normalize_choice(
        value=notebook_work_today,
        valid_options=NOTEBOOK_WORK_OPTIONS,
        label="Notebook work today",
    )
    if not notebook_present:
        return 0.0

    work_points = {
        NOTEBOOK_WORK_COMPLETE: 4.0,
        NOTEBOOK_WORK_PARTIAL: 2.0,
        NOTEBOOK_WORK_MISSING: 0.0,
    }[normalized_work]
    organized_points = 2.0 if notebook_organized else 0.0
    return round(4.0 + work_points + organized_points, 2)


def compute_comment_deduction(selected_negative_tags: list[str] | tuple[str, ...] | set[str]) -> float:
    seen: set[str] = set()
    deduction = 0.0
    for raw_tag in selected_negative_tags:
        tag = str(raw_tag).strip()
        if not tag or tag in seen:
            continue
        seen.add(tag)
        deduction += NEGATIVE_COMMENT_DEDUCTION_BY_TAG.get(tag, 0.0)
    return round(min(deduction, MAX_COMMENT_DEDUCTION), 2)


def compute_internal_total(*, agenda_score: float, notebook_score: float, deduction: float) -> float:
    if agenda_score < 0 or agenda_score > 10:
        raise ValueError("Agenda score must be between 0 and 10.")
    if notebook_score < 0 or notebook_score > 10:
        raise ValueError("Notebook score must be between 0 and 10.")
    if deduction < 0:
        raise ValueError("Deduction must be non-negative.")

    capped_deduction = min(float(deduction), MAX_COMMENT_DEDUCTION)
    return round(max(0.0, float(agenda_score) + float(notebook_score) - capped_deduction), 2)


def normalize_check_mode(value: str | None) -> str:
    cleaned = str(value or "").strip().lower()
    if cleaned in CHECK_MODE_OPTIONS:
        return cleaned
    return CHECK_MODE_BOTH


def compute_mode_totals(
    *,
    check_mode: str,
    agenda_score: float,
    notebook_score: float,
    deduction: float,
) -> tuple[float, float]:
    mode = normalize_check_mode(check_mode)
    if deduction < 0:
        raise ValueError("Deduction must be non-negative.")
    if agenda_score < 0 or agenda_score > 10:
        raise ValueError("Agenda score must be between 0 and 10.")
    if notebook_score < 0 or notebook_score > 10:
        raise ValueError("Notebook score must be between 0 and 10.")

    capped_deduction = min(float(deduction), MAX_COMMENT_DEDUCTION)
    if mode == CHECK_MODE_NOTEBOOK_ONLY:
        gradebook = round(max(0.0, float(notebook_score) - capped_deduction), 2)
        return round(gradebook * 2, 2), gradebook
    if mode == CHECK_MODE_AGENDA_ONLY:
        gradebook = round(max(0.0, float(agenda_score) - capped_deduction), 2)
        return round(gradebook * 2, 2), gradebook

    internal = compute_internal_total(
        agenda_score=agenda_score,
        notebook_score=notebook_score,
        deduction=capped_deduction,
    )
    return internal, round(internal / 2, 2)


def compute_agenda_score(data: AgendaInput) -> AgendaScoreResult:
    if not data.agenda_present:
        return AgendaScoreResult(
            agenda_present=False,
            entry_written=False,
            all_subjects_filled=False,
            organized=False,
            agenda_score=0,
            auto_zero_reason="Missing agenda",
        )

    score = 2
    if data.entry_written:
        score += 3
    if data.all_subjects_filled:
        score += 3
    if data.organized:
        score += 2

    return AgendaScoreResult(
        agenda_present=True,
        entry_written=data.entry_written,
        all_subjects_filled=data.all_subjects_filled,
        organized=data.organized,
        agenda_score=score,
    )


def compute_gradebook_score(notebook_score: float, agenda_score: int) -> float:
    if notebook_score < 0 or notebook_score > 10:
        raise ValueError("Notebook score must be between 0 and 10.")
    if agenda_score < 0 or agenda_score > 10:
        raise ValueError("Agenda score must be between 0 and 10.")
    return round((notebook_score + agenda_score) / 2, 2)


def compute_quick_mode_agenda_score(data: QuickModeInput) -> AgendaScoreResult:
    if not data.agenda_present:
        return compute_agenda_score(AgendaInput(agenda_present=False))

    if data.acceptable_today:
        return AgendaScoreResult(
            agenda_present=True,
            entry_written=True,
            all_subjects_filled=True,
            organized=True,
            agenda_score=10,
        )

    if data.manual_score_if_not_acceptable is None:
        raise ValueError("Manual score is required when agenda is not acceptable in quick mode.")

    manual_score = int(data.manual_score_if_not_acceptable)
    if manual_score < 0 or manual_score > 5:
        raise ValueError("Manual quick-mode agenda score must be between 0 and 5.")

    return AgendaScoreResult(
        agenda_present=True,
        entry_written=False,
        all_subjects_filled=False,
        organized=False,
        agenda_score=manual_score,
    )


def _normalize_choice(*, value: str, valid_options: tuple[str, ...], label: str) -> str:
    cleaned = str(value).strip().lower()
    if cleaned in valid_options:
        return cleaned
    allowed = ", ".join(valid_options)
    raise ValueError(f"{label} must be one of: {allowed}.")
