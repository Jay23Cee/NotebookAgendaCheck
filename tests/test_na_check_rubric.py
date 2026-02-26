from __future__ import annotations

from app.flags import MESSY_UNREADABLE_FLAG, MISSING_AGENDA_FLAG, MISSING_NOTEBOOK_FLAG, NO_ISSUE_FLAG
from app.nicegui_app.na_check.models import CheckFormState
from app.nicegui_app.na_check.scoring import apply_auto_rules, score_form
from app.scoring import COMMENT_TAG_INCOMPLETE_WORK


def test_default_speed_mode_scores_full_credit() -> None:
    form = CheckFormState()
    scores = score_form(form)

    assert scores.agenda_score == 10.0
    assert scores.notebook_score == 10.0
    assert scores.status_score == 0.0
    assert scores.comment_deduction == 0.0
    assert scores.total_score == 20.0
    assert scores.gradebook_score == 10.0
    assert scores.auto_flag == NO_ISSUE_FLAG


def test_agenda_not_present_forces_blank_and_not_legible() -> None:
    form = CheckFormState(
        agenda_present=False,
        agenda_entry_status="complete",
        agenda_legible=True,
    )
    normalized = apply_auto_rules(form)
    scores = score_form(form)

    assert normalized.agenda_entry_status == "blank"
    assert normalized.agenda_legible is False
    assert scores.agenda_score == 0.0
    assert scores.auto_flag == MISSING_AGENDA_FLAG


def test_notebook_not_present_forces_notebook_details_to_none() -> None:
    form = CheckFormState(
        nb_present=False,
        nb_date_status="full",
        nb_title_status="full",
        nb_notes_status="complete",
        nb_organization_status="full",
        nb_legibility_status="full",
    )
    normalized = apply_auto_rules(form)
    scores = score_form(form)

    assert normalized.nb_present is False
    assert normalized.nb_date_status == "none"
    assert normalized.nb_title_status == "none"
    assert normalized.nb_notes_status == "missing"
    assert normalized.nb_organization_status == "none"
    assert normalized.nb_legibility_status == "none"
    assert scores.notebook_score == 0.0
    assert scores.auto_flag == MISSING_NOTEBOOK_FLAG


def test_date_and_title_partial_apply_half_credit() -> None:
    form = CheckFormState(
        nb_date_status="partial",
        nb_title_status="partial",
    )
    scores = score_form(form)

    assert scores.notebook_score == 9.0


def test_notes_partial_apply_half_credit() -> None:
    form = CheckFormState(
        nb_notes_status="partial",
    )
    scores = score_form(form)

    assert scores.notebook_score == 8.5


def test_organization_and_legibility_partial_apply_half_credit() -> None:
    form = CheckFormState(
        nb_organization_status="partial",
        nb_legibility_status="partial",
    )
    scores = score_form(form)

    assert scores.notebook_score == 8.0


def test_missing_notes_does_not_auto_zero_organization_or_legibility() -> None:
    form = CheckFormState(
        nb_notes_status="missing",
        nb_organization_status="full",
        nb_legibility_status="full",
    )
    normalized = apply_auto_rules(form)
    scores = score_form(form)

    assert normalized.nb_notes_status == "missing"
    assert normalized.nb_organization_status == "full"
    assert normalized.nb_legibility_status == "full"
    assert scores.notebook_score == 7.0


def test_partial_organization_and_legibility_do_not_trigger_messy_flag() -> None:
    form = CheckFormState(
        nb_organization_status="partial",
        nb_legibility_status="partial",
    )
    scores = score_form(form)

    assert scores.auto_flag == NO_ISSUE_FLAG


def test_none_organization_triggers_messy_flag_when_other_requirements_met() -> None:
    form = CheckFormState(
        nb_organization_status="none",
        nb_legibility_status="full",
        nb_notes_status="complete",
    )
    scores = score_form(form)

    assert scores.auto_flag == MESSY_UNREADABLE_FLAG


def test_negative_tag_applies_status_deduction() -> None:
    form = CheckFormState(tags=[COMMENT_TAG_INCOMPLETE_WORK])
    scores = score_form(form)

    assert scores.comment_deduction == 5.0
    assert scores.status_score == -5.0
    assert scores.total_score == 15.0
    assert scores.gradebook_score == 7.5
