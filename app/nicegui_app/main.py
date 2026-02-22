from __future__ import annotations

from nicegui import ui

from app.constants import APP_DISPLAY_NAME
from app.nicegui_app.pages.check_page import build_check_page
from app.nicegui_app.styles.theme import apply_theme


def run() -> None:
    apply_theme()
    build_check_page()
    ui.run(title=APP_DISPLAY_NAME, dark=False, reload=False)


if __name__ == "__main__":
    run()
