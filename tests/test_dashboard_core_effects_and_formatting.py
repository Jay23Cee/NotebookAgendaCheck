from __future__ import annotations

from notebookagendacheck.nicegui_app.pages.dashboard_core.effects import (
    compose_card_classes,
    effect_class_for_student,
    queue_card_effect,
    queue_enter_effect_for_new_selection,
)
from notebookagendacheck.nicegui_app.pages.dashboard_core.formatting import (
    comment_summary_text,
    normalized_check_date,
    tags_summary_text,
)


def test_queue_enter_effect_for_new_selection_only_tracks_new_ids() -> None:
    pending: dict[str, str] = {}
    effects = {"enter": "na2-card-effect-enter"}

    queue_enter_effect_for_new_selection(
        pending_effects=pending,
        previous_ids=["S1"],
        current_ids=["S1", "S2", "S3"],
        effect="enter",
        effect_class_by_name=effects,
    )

    assert pending == {"S2": "enter", "S3": "enter"}


def test_compose_card_classes_includes_effect_class() -> None:
    pending: dict[str, str] = {}
    effects = {"save": "na2-card-effect-save"}
    queue_card_effect(
        pending_effects=pending,
        student_ids=["S1"],
        effect="save",
        effect_class_by_name=effects,
    )

    composed = compose_card_classes(
        pending_effects=pending,
        student_id="S1",
        is_saved=True,
        is_draft=False,
        effect_class_by_name=effects,
    )

    assert composed == "na2-student-card na2-card-saved na2-card-effect-save"
    assert effect_class_for_student(
        pending_effects=pending,
        student_id="S1",
        effect_class_by_name=effects,
    ) == "na2-card-effect-save"


def test_tags_comment_and_date_formatting() -> None:
    assert tags_summary_text(
        ["missing_date", "incomplete_work", "messy", "extra"],
        tag_label_by_key={
            "missing_date": "Missing Date",
            "incomplete_work": "Incomplete Work",
            "messy": "Messy",
            "extra": "Extra",
        },
    ) == "Tags: Missing Date, Incomplete Work, Messy..."
    assert comment_summary_text([], "") == "Comment: None"
    assert comment_summary_text(["Unreadable"], "") == "Comment: Unreadable"
    assert normalized_check_date("2026-02-28") == "02/28/2026"
    assert normalized_check_date("bad-date") is None


