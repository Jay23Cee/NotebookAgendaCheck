from __future__ import annotations

from typing import Mapping, MutableMapping, Sequence


def queue_card_effect(
    *,
    pending_effects: MutableMapping[str, str],
    student_ids: Sequence[str],
    effect: str,
    effect_class_by_name: Mapping[str, str],
) -> None:
    if effect not in effect_class_by_name:
        return
    for student_id in student_ids:
        normalized_student_id = str(student_id).strip()
        if normalized_student_id:
            pending_effects[normalized_student_id] = effect


def queue_enter_effect_for_new_selection(
    *,
    pending_effects: MutableMapping[str, str],
    previous_ids: Sequence[str],
    current_ids: Sequence[str],
    effect: str,
    effect_class_by_name: Mapping[str, str],
) -> None:
    previous_set = set(previous_ids)
    newly_selected_ids = [student_id for student_id in current_ids if student_id not in previous_set]
    queue_card_effect(
        pending_effects=pending_effects,
        student_ids=newly_selected_ids,
        effect=effect,
        effect_class_by_name=effect_class_by_name,
    )


def effect_class_for_student(
    *,
    pending_effects: Mapping[str, str],
    student_id: str,
    effect_class_by_name: Mapping[str, str],
) -> str:
    effect = pending_effects.get(student_id)
    if effect is None:
        return ""
    return effect_class_by_name.get(effect, "")


def compose_card_classes(
    *,
    pending_effects: Mapping[str, str],
    student_id: str,
    is_saved: bool,
    is_draft: bool,
    effect_class_by_name: Mapping[str, str],
) -> str:
    if is_saved:
        card_class = "na2-student-card na2-card-saved"
    elif is_draft:
        card_class = "na2-student-card"
    else:
        card_class = "na2-student-card na2-card-pending"

    effect_class = effect_class_for_student(
        pending_effects=pending_effects,
        student_id=student_id,
        effect_class_by_name=effect_class_by_name,
    )
    if effect_class:
        return f"{card_class} {effect_class}"
    return card_class

