from __future__ import annotations

from nicegui.events import KeyEventArguments, KeyboardAction, KeyboardKey, KeyboardModifiers

from app.models import CheckRecord
from app.nicegui_app.models.ui_state import SaveHistoryEntry, ViewState
from app.nicegui_app.services.keyboard_shortcuts import KeyboardShortcutService


def _event(
    *,
    name: str,
    code: str,
    keydown: bool = True,
    repeat: bool = False,
    alt: bool = False,
    ctrl: bool = False,
    meta: bool = False,
    shift: bool = False,
) -> KeyEventArguments:
    return KeyEventArguments(
        sender=None,  # type: ignore[arg-type]
        client=None,  # type: ignore[arg-type]
        action=KeyboardAction(keydown=keydown, keyup=not keydown, repeat=repeat),
        key=KeyboardKey(name=name, code=code, location=0),
        modifiers=KeyboardModifiers(alt=alt, ctrl=ctrl, meta=meta, shift=shift),
    )


def test_enter_shortcut_calls_save_callback() -> None:
    service = KeyboardShortcutService()
    state = ViewState()
    state.session.locked = False
    state.session.check_mode = "both"
    calls = {"save": 0, "undo": 0}

    handled = service.handle_key(
        _event(name="Enter", code="Enter"),
        state=state,
        on_save=lambda: calls.__setitem__("save", calls["save"] + 1),
        on_undo=lambda: calls.__setitem__("undo", calls["undo"] + 1),
    )

    assert handled is True
    assert calls == {"save": 1, "undo": 0}


def test_u_shortcut_calls_undo_callback() -> None:
    service = KeyboardShortcutService()
    state = ViewState()
    state.session.locked = False
    state.save_history.append(
        SaveHistoryEntry(
            index_before_save=0,
            record=CheckRecord(
                student_id="S1",
                student_name="Lovelace, Ada",
                grade=7,
                check_mode="both",
                date="2026-02-22",
                checker="Lovelace, Ada",
                notebook_score=0.0,
                agenda_present=False,
                entry_written=False,
                all_subjects_filled=False,
                organized=False,
                agenda_score=0,
                gradebook_score=0.0,
            ),
        )
    )
    calls = {"save": 0, "undo": 0}

    handled = service.handle_key(
        _event(name="u", code="KeyU"),
        state=state,
        on_save=lambda: calls.__setitem__("save", calls["save"] + 1),
        on_undo=lambda: calls.__setitem__("undo", calls["undo"] + 1),
    )

    assert handled is True
    assert calls == {"save": 0, "undo": 1}


def test_repeated_key_events_are_ignored() -> None:
    service = KeyboardShortcutService()
    state = ViewState()
    state.session.locked = False
    state.session.check_mode = "both"
    calls = {"save": 0, "undo": 0}

    handled = service.handle_key(
        _event(name="Enter", code="Enter", repeat=True),
        state=state,
        on_save=lambda: calls.__setitem__("save", calls["save"] + 1),
        on_undo=lambda: calls.__setitem__("undo", calls["undo"] + 1),
    )

    assert handled is False
    assert calls == {"save": 0, "undo": 0}


def test_modifier_key_events_are_ignored() -> None:
    service = KeyboardShortcutService()
    state = ViewState()
    state.session.locked = False
    state.session.check_mode = "both"
    calls = {"save": 0, "undo": 0}

    handled = service.handle_key(
        _event(name="Enter", code="Enter", ctrl=True),
        state=state,
        on_save=lambda: calls.__setitem__("save", calls["save"] + 1),
        on_undo=lambda: calls.__setitem__("undo", calls["undo"] + 1),
    )

    assert handled is False
    assert calls == {"save": 0, "undo": 0}


def test_locked_or_suspended_state_blocks_shortcuts() -> None:
    service = KeyboardShortcutService()
    state = ViewState()
    calls = {"save": 0, "undo": 0}

    state.session.locked = True
    handled_locked = service.handle_key(
        _event(name="Enter", code="Enter"),
        state=state,
        on_save=lambda: calls.__setitem__("save", calls["save"] + 1),
        on_undo=lambda: calls.__setitem__("undo", calls["undo"] + 1),
    )

    state.session.locked = False
    state.shortcuts_suspended = True
    handled_suspended = service.handle_key(
        _event(name="u", code="KeyU"),
        state=state,
        on_save=lambda: calls.__setitem__("save", calls["save"] + 1),
        on_undo=lambda: calls.__setitem__("undo", calls["undo"] + 1),
    )

    assert handled_locked is False
    assert handled_suspended is False
    assert calls == {"save": 0, "undo": 0}


def test_enter_shortcut_respects_checker_requirements() -> None:
    service = KeyboardShortcutService()
    state = ViewState()
    state.session.locked = False
    state.session.check_mode = "both"
    state.session.checker_mode = "student"
    calls = {"save": 0, "undo": 0}

    handled = service.handle_key(
        _event(name="Enter", code="Enter"),
        state=state,
        on_save=lambda: calls.__setitem__("save", calls["save"] + 1),
        on_undo=lambda: calls.__setitem__("undo", calls["undo"] + 1),
    )

    assert handled is False
    assert calls == {"save": 0, "undo": 0}
