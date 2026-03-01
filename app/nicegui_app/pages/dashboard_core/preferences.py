from __future__ import annotations

import json
from pathlib import Path
from typing import Callable


ErrorHandler = Callable[[Exception], None]


def load_preferences(
    preferences_file: Path,
    *,
    preferences_key: str,
    on_error: ErrorHandler | None = None,
) -> dict[str, object]:
    if not preferences_file.exists():
        return {}
    try:
        payload = json.loads(preferences_file.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        if on_error is not None:
            on_error(exc)
        return {}
    if not isinstance(payload, dict):
        return {}
    prefs = payload.get(preferences_key)
    if not isinstance(prefs, dict):
        return {}
    return prefs


def persist_preferences(
    preferences_file: Path,
    *,
    preferences_key: str,
    sticky_enabled: bool,
    grade: str,
    subject: str,
    check_date: str,
    on_error: ErrorHandler | None = None,
) -> None:
    payload: dict[str, object] = {}
    try:
        if preferences_file.exists():
            try:
                raw = json.loads(preferences_file.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    payload = raw
            except (OSError, ValueError):
                payload = {}

        payload[preferences_key] = {
            "sticky_enabled": sticky_enabled,
            "grade": grade,
            "subject": subject,
            "check_date": check_date,
        }

        preferences_file.parent.mkdir(parents=True, exist_ok=True)
        temp_file = preferences_file.with_name(f"{preferences_file.name}.tmp")
        with temp_file.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        temp_file.replace(preferences_file)
    except Exception as exc:  # noqa: BLE001
        if on_error is not None:
            on_error(exc)

