from __future__ import annotations

import csv
from pathlib import Path

from notebookagendacheck.nicegui_app.na_check.reliability import ErrorEvent, ResilientErrorLogger


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_resilient_logger_writes_csv(tmp_path: Path) -> None:
    log_path = tmp_path / "test_na_check_error_log.csv"
    logger = ResilientErrorLogger(log_path, session_id="session-1")

    event = ErrorEvent.from_exception(
        session_id="session-1",
        severity="ERROR",
        source="Test",
        operation="write",
        message="Failed write",
        exception=ValueError("boom"),
        context={"row_count": 2},
    )
    logger.log(event)

    rows = _read_rows(log_path)
    assert len(rows) >= 1
    assert rows[-1]["SessionID"] == "session-1"
    assert rows[-1]["Severity"] == "ERROR"
    assert rows[-1]["Operation"] == "write"
    assert rows[-1]["ExceptionType"] == "ValueError"


def test_resilient_logger_falls_back_to_stderr(monkeypatch, tmp_path: Path) -> None:
    logger = ResilientErrorLogger(tmp_path / "fallback.csv", session_id="session-2")
    stderr_calls: list[dict[str, str]] = []

    monkeypatch.setattr(logger, "_append_csv_row", lambda _row: (_ for _ in ()).throw(OSError("disk full")))
    monkeypatch.setattr(logger, "_write_stderr", lambda row, _exc: stderr_calls.append(row))

    logger.log_exception(
        severity="ERROR",
        source="Test",
        operation="stderr_fallback",
        message="Primary sink failed",
        exception=OSError("disk full"),
    )

    assert len(stderr_calls) == 1
    assert len(logger.ring_buffer) == 0

def test_resilient_logger_falls_back_to_ring_buffer(monkeypatch, tmp_path: Path) -> None:
    logger = ResilientErrorLogger(tmp_path / "fallback2.csv", session_id="session-3")

    monkeypatch.setattr(logger, "_append_csv_row", lambda _row: (_ for _ in ()).throw(OSError("disk full")))
    monkeypatch.setattr(logger, "_write_stderr", lambda _row, _exc: (_ for _ in ()).throw(RuntimeError("stderr down")))

    logger.log_exception(
        severity="CRITICAL",
        source="Test",
        operation="ring_buffer_fallback",
        message="All sinks failed",
        exception=RuntimeError("secondary fail"),
    )

    assert len(logger.ring_buffer) == 1
    assert logger.ring_buffer[0]["Operation"] == "ring_buffer_fallback"

