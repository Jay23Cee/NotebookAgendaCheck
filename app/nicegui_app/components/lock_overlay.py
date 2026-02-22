from __future__ import annotations

from dataclasses import dataclass

from nicegui import ui


@dataclass
class LockOverlayHandles:
    root: ui.element
    title: ui.label


def build_lock_overlay() -> LockOverlayHandles:
    with ui.element("div").classes("na-lock-overlay") as root:
        title = ui.label("Select Grade to begin").classes("na-lock-title")
        ui.label("Choose Grade to load this class roster.").classes("na-lock-subtitle")
    return LockOverlayHandles(root=root, title=title)
