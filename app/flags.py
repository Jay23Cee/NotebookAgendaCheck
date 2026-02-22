from app.scoring import (
    CHECK_MODE_AGENDA_ONLY,
    CHECK_MODE_BOTH,
    CHECK_MODE_NOTEBOOK_ONLY,
    normalize_check_mode,
)

MISSING_AGENDA_FLAG = "Missing agenda"
MISSING_NOTEBOOK_FLAG = "Missing notebook"
BLANK_ENTRIES_FLAG = "Blank entries"
INCOMPLETE_SUBJECTS_FLAG = "Incomplete subjects"
MESSY_UNREADABLE_FLAG = "Messy/unreadable"
NO_ISSUE_FLAG = "None"

AUTO_FLAG_PRIORITY = [
    MISSING_AGENDA_FLAG,
    MISSING_NOTEBOOK_FLAG,
    BLANK_ENTRIES_FLAG,
    INCOMPLETE_SUBJECTS_FLAG,
    MESSY_UNREADABLE_FLAG,
    NO_ISSUE_FLAG,
]

ISSUE_FLAG_OPTIONS = list(AUTO_FLAG_PRIORITY)

# Legacy labels that may exist in historical CSV rows.
_LEGACY_FLAG_NORMALIZATION = {
    "entry not written": BLANK_ENTRIES_FLAG,
    "blank entry": BLANK_ENTRIES_FLAG,
    "blank entries": BLANK_ENTRIES_FLAG,
    "incomplete subject entries": INCOMPLETE_SUBJECTS_FLAG,
    "messy / unreadable": MESSY_UNREADABLE_FLAG,
    "no issues": NO_ISSUE_FLAG,
}


def normalize_issue_flag(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        return ""
    if cleaned in ISSUE_FLAG_OPTIONS:
        return cleaned
    return _LEGACY_FLAG_NORMALIZATION.get(cleaned.lower(), cleaned)


def compute_issue_flag(
    *,
    notebook_score: float,
    agenda_present: bool,
    entry_written: bool,
    all_subjects_filled: bool,
    organized: bool,
    check_mode: str = CHECK_MODE_BOTH,
) -> str:
    mode = normalize_check_mode(check_mode)
    if mode == CHECK_MODE_NOTEBOOK_ONLY:
        if notebook_score <= 0:
            return MISSING_NOTEBOOK_FLAG
        if not organized:
            return MESSY_UNREADABLE_FLAG
        return NO_ISSUE_FLAG
    if mode == CHECK_MODE_AGENDA_ONLY:
        if not agenda_present:
            return MISSING_AGENDA_FLAG
        if not entry_written:
            return BLANK_ENTRIES_FLAG
        if not all_subjects_filled:
            return INCOMPLETE_SUBJECTS_FLAG
        if not organized:
            return MESSY_UNREADABLE_FLAG
        return NO_ISSUE_FLAG

    if not agenda_present:
        return MISSING_AGENDA_FLAG
    if notebook_score <= 0:
        return MISSING_NOTEBOOK_FLAG
    if not entry_written:
        return BLANK_ENTRIES_FLAG
    if not all_subjects_filled:
        return INCOMPLETE_SUBJECTS_FLAG
    if not organized:
        return MESSY_UNREADABLE_FLAG
    return NO_ISSUE_FLAG
