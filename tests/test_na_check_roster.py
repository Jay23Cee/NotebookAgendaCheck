from __future__ import annotations

import csv
from pathlib import Path

import pytest
from openpyxl import Workbook

from notebookagendacheck.nicegui_app.na_check.roster import RosterValidationError, load_roster


def _write_roster(path: Path, header: list[str], rows: list[list[object]]) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(header)
    for row in rows:
        sheet.append(row)
    workbook.save(path)
    workbook.close()


def _write_csv(path: Path, header: list[str], rows: list[list[object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


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


def test_load_roster_csv_imports_valid_rows_with_period_default(tmp_path: Path) -> None:
    roster_file = tmp_path / "students.csv"
    _write_csv(
        roster_file,
        ["StudentID", "StudentName", "Grade", "Subject"],
        [
            ["S1", "Ava One", "6", "math"],
            ["S2", "Ben Two", "7", "Science"],
        ],
    )

    students = load_roster(roster_file)

    assert len(students) == 2
    assert students[0].student_id == "S1"
    assert students[0].student_name == "Ava One"
    assert students[0].grade == "6"
    assert students[0].subject == "Math"
    assert students[0].period == "Unknown"


def test_load_roster_csv_missing_required_header_fails(tmp_path: Path) -> None:
    roster_file = tmp_path / "missing_header.csv"
    _write_csv(
        roster_file,
        ["StudentID", "StudentName", "Grade"],
        [["S1", "Ava One", "6"]],
    )

    with pytest.raises(RosterValidationError) as exc_info:
        load_roster(roster_file)

    assert "required columns" in str(exc_info.value).lower()
    assert any(issue.column == "Subject" for issue in exc_info.value.issues)


def test_load_roster_csv_invalid_grade_fails(tmp_path: Path) -> None:
    roster_file = tmp_path / "invalid_grade.csv"
    _write_csv(
        roster_file,
        ["StudentID", "StudentName", "Grade", "Subject"],
        [["S1", "Ava One", "5", "Math"]],
    )

    with pytest.raises(RosterValidationError) as exc_info:
        load_roster(roster_file)

    assert any(issue.column == "Grade" for issue in exc_info.value.issues)


def test_load_roster_csv_invalid_subject_fails(tmp_path: Path) -> None:
    roster_file = tmp_path / "invalid_subject.csv"
    _write_csv(
        roster_file,
        ["StudentID", "StudentName", "Grade", "Subject"],
        [["S1", "Ava One", "6", "History"]],
    )

    with pytest.raises(RosterValidationError) as exc_info:
        load_roster(roster_file)

    assert any(issue.column == "Subject" for issue in exc_info.value.issues)


def test_load_roster_csv_duplicate_student_id_fails(tmp_path: Path) -> None:
    roster_file = tmp_path / "duplicate_ids.csv"
    _write_csv(
        roster_file,
        ["StudentID", "StudentName", "Grade", "Subject", "Period"],
        [
            ["S1", "Ava One", "6", "Math", "1"],
            ["S1", "Ben Two", "6", "Science", "2"],
        ],
    )

    with pytest.raises(RosterValidationError) as exc_info:
        load_roster(roster_file)

    assert any("Duplicate StudentID" in issue.message for issue in exc_info.value.issues)


def test_load_roster_xlsx_path_still_supported(tmp_path: Path) -> None:
    roster_file = tmp_path / "students.xlsx"
    _write_roster(
        roster_file,
        ["StudentID", "FirstName", "LastName", "Grade", "Period", "Subject"],
        [["S1", "Ava", "One", 6, 1, "mathematics"]],
    )

    students = load_roster(roster_file)

    assert len(students) == 1
    assert students[0].student_id == "S1"
    assert students[0].subject == "Math"

