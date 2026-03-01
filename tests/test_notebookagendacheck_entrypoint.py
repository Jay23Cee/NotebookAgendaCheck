from __future__ import annotations

import os

from notebookagendacheck import __main__ as entrypoint


def test_main_sets_default_host_and_port(monkeypatch) -> None:
    monkeypatch.delenv("NACH_HOST", raising=False)
    monkeypatch.delenv("NACH_PORT", raising=False)
    called = {"ran": False}

    monkeypatch.setattr(entrypoint, "run", lambda: called.__setitem__("ran", True))
    entrypoint.main()

    assert os.environ["NACH_HOST"] == "127.0.0.1"
    assert os.environ["NACH_PORT"] == "8080"
    assert called["ran"] is True


def test_main_preserves_existing_env(monkeypatch) -> None:
    monkeypatch.setenv("NACH_HOST", "0.0.0.0")
    monkeypatch.setenv("NACH_PORT", "9090")
    monkeypatch.setattr(entrypoint, "run", lambda: None)

    entrypoint.main()

    assert os.environ["NACH_HOST"] == "0.0.0.0"
    assert os.environ["NACH_PORT"] == "9090"
