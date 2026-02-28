from __future__ import annotations

import csv
import os
from pathlib import Path

import pytest

from app.nicegui_app.na_check.storage import CsvStore


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_append_rows_preserves_original_when_atomic_replace_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output = tmp_path / "rows.csv"
    store = CsvStore(output, session_id="atomic-test")
    store.append_rows([{"StudentID": "S1", "Date": "02/28/2026"}])
    before = output.read_text(encoding="utf-8")

    monkeypatch.setattr(os, "replace", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("replace failed")))

    with pytest.raises(OSError):
        store.append_rows([{"StudentID": "S2", "Date": "02/28/2026"}])

    after = output.read_text(encoding="utf-8")
    assert after == before


def test_undo_last_saved_rows_uses_atomic_replace(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    output = tmp_path / "rows.csv"
    store = CsvStore(output, session_id="atomic-test")
    store.append_rows(
        [
            {"StudentID": "S1", "Date": "02/28/2026"},
            {"StudentID": "S2", "Date": "02/28/2026"},
        ]
    )

    calls = {"count": 0}
    original_replace = os.replace

    def wrapped_replace(src: str | bytes | os.PathLike[str] | os.PathLike[bytes], dst: str | bytes | os.PathLike[str] | os.PathLike[bytes]) -> None:
        calls["count"] += 1
        original_replace(src, dst)

    monkeypatch.setattr(os, "replace", wrapped_replace)

    removed = store.undo_last_saved_rows(1)
    assert removed == 1
    assert calls["count"] >= 1
    assert [row["StudentID"] for row in _read_rows(output)] == ["S1"]


def test_append_rows_retries_share_lock_once(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    output = tmp_path / "rows.csv"
    store = CsvStore(output, session_id="retry-test")

    calls = {"count": 0}

    class ShareLockError(PermissionError):
        def __init__(self) -> None:
            super().__init__("The process cannot access the file because it is being used by another process")
            self.winerror = 32

    original_write = store._write_snapshot_atomic

    def flaky_write(headers: list[str], rows: list[dict[str, object]]) -> None:
        calls["count"] += 1
        if calls["count"] == 1:
            raise ShareLockError()
        original_write(headers, rows)

    monkeypatch.setattr(store, "_write_snapshot_atomic", flaky_write)
    monkeypatch.setattr("app.nicegui_app.na_check.storage.time.sleep", lambda _seconds: None)

    store.append_rows([{"StudentID": "S1", "Date": "02/28/2026"}])

    assert calls["count"] == 2
    rows = _read_rows(output)
    assert len(rows) == 1
    assert rows[0]["StudentID"] == "S1"
