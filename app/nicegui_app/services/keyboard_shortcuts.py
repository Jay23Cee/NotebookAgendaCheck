from __future__ import annotations

from collections.abc import Callable

from nicegui.events import KeyEventArguments

from app.nicegui_app.models.ui_state import ViewState


class KeyboardShortcutService:
    def handle_key(
        self,
        event: KeyEventArguments,
        *,
        state: ViewState,
        on_save: Callable[[], None],
        on_undo: Callable[[], None],
    ) -> bool:
        if not event.action.keydown:
            return False
        if event.action.repeat:
            return False
        if event.modifiers.alt or event.modifiers.ctrl or event.modifiers.meta:
            return False
        if state.shortcuts_suspended or state.session.locked:
            return False

        key_name = str(event.key).lower()
        if event.key.enter:
            if not state.can_save:
                return False
            on_save()
            return True
        if key_name == "u":
            if not state.can_undo:
                return False
            on_undo()
            return True
        return False
