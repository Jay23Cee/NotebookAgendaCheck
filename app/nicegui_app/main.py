from __future__ import annotations

from nicegui import ui

from app.constants import APP_DISPLAY_NAME
from app.nicegui_app.pages.na_check_dashboard import build_na_check_dashboard
from app.nicegui_app.styles.theme import apply_theme


def run() -> None:
    apply_theme()
    build_na_check_dashboard()
    ui.run(title=APP_DISPLAY_NAME, dark=False, reload=False)


if __name__ == "__main__":
    run()
