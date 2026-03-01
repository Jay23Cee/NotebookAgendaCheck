from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook

from app.nicegui_app.na_check.roster import load_roster


def _write_roster(path: Path, header: list[str], rows: list[list[object]]) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(header)
    for row in rows:
        sheet.append(row)
    workbook.save(path)
    workbook.close()


def test_load_roster_normalizes_subject_values(tmp_path: Path) -> None:
    roster_file = tmp_path / "students.xlsx"
    _write_roster(
        roster_file,
        ["StudentID", "FirstName", "LastName", "Grade", "Period", "Subject"],
        [
            ["S1", "Ava", "One", 6, 1, "mathematics"],
            ["S2", "Ben", "Two", 6, 2, "sci"],
        ],
    )

    students = load_roster(roster_file)

    assert [student.subject for student in students] == ["Math", "Science"]
    assert [student.period for student in students] == ["1", "2"]


def test_load_roster_sets_empty_subject_when_subject_column_missing(tmp_path: Path) -> None:
    roster_file = tmp_path / "students_no_subject.xlsx"
    _write_roster(
        roster_file,
        ["StudentID", "FirstName", "LastName", "Grade", "Period"],
        [["S1", "Ava", "One", 6, 1]],
    )

    students = load_roster(roster_file)

    assert len(students) == 1
    assert students[0].subject == ""
