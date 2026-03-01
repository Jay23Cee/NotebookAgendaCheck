from __future__ import annotations

import os

from nicegui import ui

from app.constants import APP_DISPLAY_NAME
from app.nicegui_app.pages.na_check_dashboard import build_na_check_dashboard
from app.nicegui_app.styles.theme import apply_theme

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080
TRUE_VALUES = {"1", "true", "yes", "y", "on"}
FALSE_VALUES = {"0", "false", "no", "n", "off"}


def _env_str(name: str, *, default: str) -> str:
    raw = os.getenv(name)
    if raw is None:
        return default
    value = raw.strip()
    return value or default


def _env_int(name: str, *, default: int, minimum: int, maximum: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw.strip())
    except ValueError:
        return default
    if value < minimum or value > maximum:
        return default
    return value


def _env_bool(name: str, *, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    return default


def run() -> None:
    apply_theme()
    build_na_check_dashboard()
    ui.run(
        host=_env_str("NACH_HOST", default=DEFAULT_HOST),
        port=_env_int("NACH_PORT", default=DEFAULT_PORT, minimum=1, maximum=65535),
        show=_env_bool("NACH_SHOW", default=False),
        reload=_env_bool("NACH_RELOAD", default=False),
        title=APP_DISPLAY_NAME,
        dark=False,
    )


if __name__ == "__main__":
    run()
