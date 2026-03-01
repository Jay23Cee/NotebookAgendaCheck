from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
import os

from nicegui import app, ui

from notebookagendacheck.constants import APP_DISPLAY_NAME
from notebookagendacheck.nicegui_app.pages.na_check_dashboard import build_na_check_dashboard
from notebookagendacheck.nicegui_app.styles.theme import apply_theme

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080
DEFAULT_APP_VERSION = "0.1.0"
HEALTH_ROUTE_PATH = "/_nach/health"
HEALTH_APP_NAME = "NotebookAgendaCheck"
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


def _app_version() -> str:
    try:
        return version("notebookagendacheck")
    except PackageNotFoundError:
        return DEFAULT_APP_VERSION


def _health_payload() -> dict[str, str]:
    return {
        "status": "ok",
        "app": HEALTH_APP_NAME,
        "version": _app_version(),
    }


def _register_health_route() -> None:
    if any(getattr(route, "path", None) == HEALTH_ROUTE_PATH for route in app.routes):
        return
    app.add_api_route(HEALTH_ROUTE_PATH, _health_payload, methods=["GET"])


def run() -> None:
    _register_health_route()
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

