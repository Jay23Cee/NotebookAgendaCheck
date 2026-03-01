from __future__ import annotations

import csv
from pathlib import Path

from notebookagendacheck.nicegui_app.na_check.reliability import ResilientErrorLogger
from notebookagendacheck.nicegui_app.na_check.storage import CsvStore


def _read_headers(path: Path) -> list[str]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        return next(reader, [])


def test_corrupted_utf8_file_is_quarantined_and_recreated(tmp_path: Path) -> None:
    output = tmp_path / "checks.csv"
    quarantine_dir = tmp_path / "quarantine"
    logger = ResilientErrorLogger(tmp_path / "error_log.csv", session_id="session-1")
    store = CsvStore(
        output,
        quarantine_dir=quarantine_dir,
        session_id="session-1",
        logger=logger,
    )
    output.write_bytes(b"\xff\xfe\x00\x00bad")

    refs = store.list_saved_refs()

    assert refs == []
    assert output.exists()
    headers = _read_headers(output)
    assert "StudentID" in headers
    assert "Date" in headers
    quarantined = list(quarantine_dir.glob("checks.csv.corrupt.*.session-1.csv"))
    assert len(quarantined) == 1


def test_missing_required_header_is_quarantined_and_recreated(tmp_path: Path) -> None:
    output = tmp_path / "checks.csv"
    quarantine_dir = tmp_path / "quarantine"
    logger = ResilientErrorLogger(tmp_path / "error_log.csv", session_id="session-2")
    store = CsvStore(
        output,
        quarantine_dir=quarantine_dir,
        session_id="session-2",
        logger=logger,
    )
    output.write_text("StudentID,Grade\nS1,6\n", encoding="utf-8")

    refs = store.list_saved_refs()

    assert refs == []
    headers = _read_headers(output)
    assert "StudentID" in headers
    assert "Date" in headers
    quarantined = list(quarantine_dir.glob("checks.csv.corrupt.*.session-2.csv"))
    assert len(quarantined) == 1

