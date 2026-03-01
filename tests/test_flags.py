from notebookagendacheck.flags import (
    AUTO_FLAG_PRIORITY,
    BLANK_ENTRIES_FLAG,
    INCOMPLETE_SUBJECTS_FLAG,
    ISSUE_FLAG_OPTIONS,
    MESSY_UNREADABLE_FLAG,
    MISSING_AGENDA_FLAG,
    MISSING_NOTEBOOK_FLAG,
    NO_ISSUE_FLAG,
    compute_issue_flag,
    normalize_issue_flag,
)
from notebookagendacheck.scoring import CHECK_MODE_AGENDA_ONLY, CHECK_MODE_NOTEBOOK_ONLY


def test_auto_flag_priority_order() -> None:
    assert AUTO_FLAG_PRIORITY == [
        MISSING_AGENDA_FLAG,
        MISSING_NOTEBOOK_FLAG,
        BLANK_ENTRIES_FLAG,
        INCOMPLETE_SUBJECTS_FLAG,
        MESSY_UNREADABLE_FLAG,
        NO_ISSUE_FLAG,
    ]
    assert ISSUE_FLAG_OPTIONS == AUTO_FLAG_PRIORITY


def test_missing_agenda_has_highest_priority() -> None:
    assert (
        compute_issue_flag(
            notebook_score=0,
            agenda_present=False,
            entry_written=False,
            all_subjects_filled=False,
            organized=False,
        )
        == MISSING_AGENDA_FLAG
    )


def test_missing_notebook_when_agenda_present() -> None:
    assert (
        compute_issue_flag(
            notebook_score=0,
            agenda_present=True,
            entry_written=True,
            all_subjects_filled=True,
            organized=True,
        )
        == MISSING_NOTEBOOK_FLAG
    )


def test_blank_entries_after_missing_checks() -> None:
    assert (
        compute_issue_flag(
            notebook_score=2,
            agenda_present=True,
            entry_written=False,
            all_subjects_filled=True,
            organized=True,
        )
        == BLANK_ENTRIES_FLAG
    )


def test_incomplete_subjects_after_blank_entries() -> None:
    assert (
        compute_issue_flag(
            notebook_score=2,
            agenda_present=True,
            entry_written=True,
            all_subjects_filled=False,
            organized=True,
        )
        == INCOMPLETE_SUBJECTS_FLAG
    )


def test_messy_unreadable_after_incomplete_subjects() -> None:
    assert (
        compute_issue_flag(
            notebook_score=2,
            agenda_present=True,
            entry_written=True,
            all_subjects_filled=True,
            organized=False,
        )
        == MESSY_UNREADABLE_FLAG
    )


def test_no_issue_returns_literal_none_flag() -> None:
    assert (
        compute_issue_flag(
            notebook_score=2,
            agenda_present=True,
            entry_written=True,
            all_subjects_filled=True,
            organized=True,
        )
        == NO_ISSUE_FLAG
    )


def test_normalize_legacy_issue_flag_to_canonical_value() -> None:
    assert normalize_issue_flag("Entry not written") == BLANK_ENTRIES_FLAG


def test_normalize_issue_flag_preserves_custom_non_empty_values() -> None:
    assert normalize_issue_flag("Needs conference") == "Needs conference"


def test_normalize_issue_flag_handles_blank_values() -> None:
    assert normalize_issue_flag("   ") == ""


def test_notebook_only_mode_ignores_missing_agenda() -> None:
    assert (
        compute_issue_flag(
            notebook_score=4,
            agenda_present=False,
            entry_written=False,
            all_subjects_filled=False,
            organized=True,
            check_mode=CHECK_MODE_NOTEBOOK_ONLY,
        )
        == NO_ISSUE_FLAG
    )


def test_agenda_only_mode_ignores_missing_notebook() -> None:
    assert (
        compute_issue_flag(
            notebook_score=0,
            agenda_present=True,
            entry_written=True,
            all_subjects_filled=True,
            organized=True,
            check_mode=CHECK_MODE_AGENDA_ONLY,
        )
        == NO_ISSUE_FLAG
    )

