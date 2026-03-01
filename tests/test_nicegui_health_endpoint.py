from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from notebookagendacheck.nicegui_app import main


def _health_route_count() -> int:
    return sum(1 for route in main.app.routes if getattr(route, "path", None) == main.HEALTH_ROUTE_PATH)


def test_health_route_returns_expected_payload() -> None:
    main._register_health_route()
    client = TestClient(main.app)

    response = client.get(main.HEALTH_ROUTE_PATH)

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "app": "NotebookAgendaCheck",
        "version": "0.1.0",
    }


def test_health_route_registration_is_idempotent() -> None:
    before = _health_route_count()

    main._register_health_route()
    after_first = _health_route_count()
    main._register_health_route()
    after_second = _health_route_count()

    assert after_first >= max(1, before)
    assert after_second == after_first


def test_run_keeps_health_route_available(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}
    monkeypatch.setattr(main, "apply_theme", lambda: None)
    monkeypatch.setattr(main, "build_na_check_dashboard", lambda: None)
    monkeypatch.setattr(main.ui, "run", lambda **kwargs: captured.update(kwargs))

    main.run()

    client = TestClient(main.app)
    response = client.get(main.HEALTH_ROUTE_PATH)

    assert captured["host"] == "127.0.0.1"
    assert captured["port"] == 8080
    assert response.status_code == 200
