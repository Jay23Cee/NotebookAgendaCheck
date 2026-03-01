import pytest

from notebookagendacheck.scoring import (
    AGENDA_FILLED_BLANK,
    AGENDA_FILLED_COMPLETE,
    AGENDA_FILLED_PARTIAL,
    CHECK_MODE_AGENDA_ONLY,
    CHECK_MODE_BOTH,
    CHECK_MODE_NOTEBOOK_ONLY,
    COMMENT_TAG_DIFFICULT_TO_READ,
    COMMENT_TAG_DISORGANIZED,
    COMMENT_TAG_INCOMPLETE_WORK,
    COMMENT_TAG_MISSING_DATE,
    COMMENT_TAG_UNREADABLE,
    NOTEBOOK_WORK_COMPLETE,
    NOTEBOOK_WORK_MISSING,
    NOTEBOOK_WORK_PARTIAL,
    compute_agenda_score_v2,
    compute_comment_deduction,
    compute_gradebook_score,
    compute_internal_total,
    compute_mode_totals,
    compute_notebook_score_v2,
    normalize_check_mode,
)


def test_agenda_score_v2_matrix() -> None:
    assert (
        compute_agenda_score_v2(
            agenda_present=True,
            agenda_filled_today=AGENDA_FILLED_COMPLETE,
            agenda_readable=True,
        )
        == 10.0
    )
    assert (
        compute_agenda_score_v2(
            agenda_present=True,
            agenda_filled_today=AGENDA_FILLED_PARTIAL,
            agenda_readable=True,
        )
        == 8.0
    )
    assert (
        compute_agenda_score_v2(
            agenda_present=True,
            agenda_filled_today=AGENDA_FILLED_BLANK,
            agenda_readable=False,
        )
        == 4.0
    )
    assert (
        compute_agenda_score_v2(
            agenda_present=False,
            agenda_filled_today=AGENDA_FILLED_COMPLETE,
            agenda_readable=True,
        )
        == 0.0
    )


def test_notebook_score_v2_matrix() -> None:
    assert (
        compute_notebook_score_v2(
            notebook_present=True,
            notebook_work_today=NOTEBOOK_WORK_COMPLETE,
            notebook_organized=True,
        )
        == 10.0
    )
    assert (
        compute_notebook_score_v2(
            notebook_present=True,
            notebook_work_today=NOTEBOOK_WORK_PARTIAL,
            notebook_organized=False,
        )
        == 6.0
    )
    assert (
        compute_notebook_score_v2(
            notebook_present=True,
            notebook_work_today=NOTEBOOK_WORK_MISSING,
            notebook_organized=False,
        )
        == 4.0
    )
    assert (
        compute_notebook_score_v2(
            notebook_present=False,
            notebook_work_today=NOTEBOOK_WORK_COMPLETE,
            notebook_organized=True,
        )
        == 0.0
    )


def test_comment_deduction_cap_and_uniqueness() -> None:
    assert compute_comment_deduction([COMMENT_TAG_MISSING_DATE]) == 0.25
    assert (
        compute_comment_deduction(
            [
                COMMENT_TAG_DIFFICULT_TO_READ,
                COMMENT_TAG_DISORGANIZED,
                COMMENT_TAG_MISSING_DATE,
                COMMENT_TAG_INCOMPLETE_WORK,
                COMMENT_TAG_UNREADABLE,
            ]
        )
        == 5.0
    )
    assert compute_comment_deduction([COMMENT_TAG_DIFFICULT_TO_READ, COMMENT_TAG_DIFFICULT_TO_READ]) == 0.5


def test_internal_total_floor_and_bounds() -> None:
    assert compute_internal_total(agenda_score=8.0, notebook_score=7.0, deduction=0.5) == 14.5
    assert compute_internal_total(agenda_score=0.0, notebook_score=0.0, deduction=1.0) == 0.0
    assert compute_internal_total(agenda_score=10.0, notebook_score=10.0, deduction=3.0) == 17.0
    assert compute_internal_total(agenda_score=10.0, notebook_score=10.0, deduction=8.0) == 15.0
    with pytest.raises(ValueError):
        compute_internal_total(agenda_score=-1, notebook_score=10, deduction=0)
    with pytest.raises(ValueError):
        compute_internal_total(agenda_score=10, notebook_score=11, deduction=0)
    with pytest.raises(ValueError):
        compute_internal_total(agenda_score=10, notebook_score=10, deduction=-0.25)


def test_gradebook_score_bounds_and_rounding() -> None:
    assert compute_gradebook_score(8.0, 10) == 9.0
    assert compute_gradebook_score(8.75, 7.5) == 8.12
    with pytest.raises(ValueError):
        compute_gradebook_score(-1, 10)
    with pytest.raises(ValueError):
        compute_gradebook_score(11, 10)
    with pytest.raises(ValueError):
        compute_gradebook_score(8, -1)
    with pytest.raises(ValueError):
        compute_gradebook_score(8, 11)


def test_mode_totals_for_single_and_both_modes() -> None:
    assert compute_mode_totals(check_mode=CHECK_MODE_BOTH, agenda_score=8.0, notebook_score=7.0, deduction=1.5) == (
        13.5,
        6.75,
    )
    assert compute_mode_totals(
        check_mode=CHECK_MODE_NOTEBOOK_ONLY,
        agenda_score=8.0,
        notebook_score=7.0,
        deduction=1.5,
    ) == (11.0, 5.5)
    assert compute_mode_totals(
        check_mode=CHECK_MODE_AGENDA_ONLY,
        agenda_score=8.0,
        notebook_score=7.0,
        deduction=1.5,
    ) == (13.0, 6.5)


def test_normalize_check_mode_defaults_to_both() -> None:
    assert normalize_check_mode(None) == CHECK_MODE_BOTH
    assert normalize_check_mode("") == CHECK_MODE_BOTH
    assert normalize_check_mode("unknown") == CHECK_MODE_BOTH

