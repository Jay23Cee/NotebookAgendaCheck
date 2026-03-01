from __future__ import annotations

import json
from pathlib import Path

from notebookagendacheck.nicegui_app.pages.dashboard_core.preferences import load_preferences, persist_preferences


def test_persist_preferences_merges_into_existing_payload(tmp_path: Path) -> None:
    prefs_file = tmp_path / "prefs.json"
    prefs_file.write_text(json.dumps({"another_key": {"enabled": True}}), encoding="utf-8")

    persist_preferences(
        prefs_file,
        preferences_key="na_check_dashboard",
        sticky_enabled=True,
        grade="6",
        subject="Math",
        check_date="02/28/2026",
    )

    payload = json.loads(prefs_file.read_text(encoding="utf-8"))
    assert payload["another_key"] == {"enabled": True}
    assert payload["na_check_dashboard"] == {
        "sticky_enabled": True,
        "grade": "6",
        "subject": "Math",
        "check_date": "02/28/2026",
    }


def test_load_preferences_returns_empty_dict_for_missing_file(tmp_path: Path) -> None:
    prefs_file = tmp_path / "missing.json"
    assert load_preferences(prefs_file, preferences_key="na_check_dashboard") == {}


def test_load_preferences_calls_error_handler_for_invalid_json(tmp_path: Path) -> None:
    prefs_file = tmp_path / "prefs.json"
    prefs_file.write_text("{invalid-json", encoding="utf-8")
    errors: list[str] = []

    loaded = load_preferences(
        prefs_file,
        preferences_key="na_check_dashboard",
        on_error=lambda exc: errors.append(type(exc).__name__),
    )

    assert loaded == {}
    assert errors == ["JSONDecodeError"]


