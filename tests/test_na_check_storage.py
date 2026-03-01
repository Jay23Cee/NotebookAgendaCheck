from __future__ import annotations

import csv
from pathlib import Path

from notebookagendacheck.nicegui_app.na_check.storage import CsvStore


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_list_saved_refs_reads_legacy_headers(tmp_path: Path) -> None:
    output = tmp_path / "legacy.csv"
    output.write_text(
        "StudentID,Date,Grade,Period\n"
        "S1,02/25/2026,7,1\n"
        "S2,2026-02-25,7,1\n",
        encoding="utf-8",
    )

    store = CsvStore(output)
    refs = store.list_saved_refs()

    assert len(refs) == 2
    assert refs[0].student_id == "S1"
    assert refs[0].check_date == "02/25/2026"
    assert refs[1].student_id == "S2"
    assert refs[1].check_date == "02/25/2026"


def test_append_rows_and_undo_last_saved_rows(tmp_path: Path) -> None:
    output = tmp_path / "rows.csv"
    store = CsvStore(output)

    store.append_rows(
        [
            {"StudentID": "S1", "Date": "02/25/2026"},
            {"StudentID": "S2", "Date": "02/25/2026"},
            {"StudentID": "S3", "Date": "02/25/2026"},
        ]
    )
    removed = store.undo_last_saved_rows(2)

    assert removed == 2
    rows = _read_rows(output)
    assert len(rows) == 1
    assert rows[0]["StudentID"] == "S1"


