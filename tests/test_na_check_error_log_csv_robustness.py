from __future__ import annotations

import csv
from pathlib import Path

from notebookagendacheck.nicegui_app.na_check.reliability import ErrorEvent, ResilientErrorLogger


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_error_log_csv_handles_long_multiline_and_unicode_fields(tmp_path: Path) -> None:
    log_path = tmp_path / "error_log.csv"
    logger = ResilientErrorLogger(log_path, session_id="robust-session")

    long_text = "x" * 10000
    message = f"Failure, unicode=naive {long_text}"
    context = {"notes": "line1\nline2\nline3", "emoji_like_text": "caf\u00e9"}

    try:
        raise RuntimeError(f"multiline error\n{long_text}")
    except RuntimeError as exc:
        event = ErrorEvent.from_exception(
            session_id="robust-session",
            severity="ERROR",
            source="RobustnessTest",
            operation="log_long_traceback",
            message=message,
            exception=exc,
            context=context,
        )

    logger.log(event)

    rows = _read_rows(log_path)
    assert len(rows) == 1
    row = rows[0]
    assert row["SessionID"] == "robust-session"
    assert len(row["Message"]) >= 10000
    assert "multiline error" in row["ExceptionMessage"]
    assert "\n" in row["Traceback"]
    assert "café" in row["ContextJson"]

