from __future__ import annotations

import pytest

from notebookagendacheck.nicegui_app import main


def _capture_ui_run(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    captured: dict[str, object] = {}

    monkeypatch.setattr(main, "apply_theme", lambda: None)
    monkeypatch.setattr(main, "build_na_check_dashboard", lambda: None)
    monkeypatch.setattr(main.ui, "run", lambda **kwargs: captured.update(kwargs))

    return captured


def test_run_uses_safe_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = _capture_ui_run(monkeypatch)

    monkeypatch.delenv("NACH_HOST", raising=False)
    monkeypatch.delenv("NACH_PORT", raising=False)
    monkeypatch.delenv("NACH_SHOW", raising=False)
    monkeypatch.delenv("NACH_RELOAD", raising=False)

    main.run()

    assert captured["host"] == "127.0.0.1"
    assert captured["port"] == 8080
    assert captured["show"] is False
    assert captured["reload"] is False


def test_run_uses_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = _capture_ui_run(monkeypatch)

    monkeypatch.setenv("NACH_HOST", "0.0.0.0")
    monkeypatch.setenv("NACH_PORT", "9090")
    monkeypatch.setenv("NACH_SHOW", "true")
    monkeypatch.setenv("NACH_RELOAD", "1")

    main.run()

    assert captured["host"] == "0.0.0.0"
    assert captured["port"] == 9090
    assert captured["show"] is True
    assert captured["reload"] is True


def test_run_ignores_invalid_env_values(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = _capture_ui_run(monkeypatch)

    monkeypatch.setenv("NACH_HOST", "   ")
    monkeypatch.setenv("NACH_PORT", "not-a-number")
    monkeypatch.setenv("NACH_SHOW", "maybe")
    monkeypatch.setenv("NACH_RELOAD", "maybe")

    main.run()

    assert captured["host"] == "127.0.0.1"
    assert captured["port"] == 8080
    assert captured["show"] is False
    assert captured["reload"] is False

