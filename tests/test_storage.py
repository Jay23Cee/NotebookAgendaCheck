import csv
from pathlib import Path

from notebookagendacheck.models import CheckRecord
from notebookagendacheck.scoring import SCORE_MODEL_INTERNAL20_GRADEBOOK10_V1
from notebookagendacheck.storage import (
    append_record,
    export_summary_csv,
    load_insights_visibility,
    load_records,
    load_records_with_warnings,
    remove_last_record,
    save_insights_visibility,
    summarize_reliability,
)


def _record(
    student_id: str,
    agenda_score: int = 10,
    agenda_present: bool = True,
    all_subjects: bool = True,
    comments: str = "",
) -> CheckRecord:
    return CheckRecord(
        student_id=student_id,
        student_name=f"{student_id}, Test",
        grade=7,
        check_mode="both",
        date="2026-02-21",
        checker="Ms Rivera",
        notebook_score=8.0,
        agenda_present=agenda_present,
        entry_written=True,
        all_subjects_filled=all_subjects,
        organized=True,
        agenda_score=agenda_score,
        gradebook_score=9.0,
        agenda_filled_today="complete",
        agenda_readable=True,
        notebook_present_detail=True,
        notebook_work_today="complete",
        notebook_organized=True,
        comment_tags="Strong_Effort",
        comment_deduction=0.25 if comments else 0.0,
        internal_score=18.0,
        score_model=SCORE_MODEL_INTERNAL20_GRADEBOOK10_V1,
        flag="",
        comments=comments,
    )


def test_append_and_load_records(tmp_path: Path) -> None:
    output = tmp_path / "checks.csv"
    append_record(_record("A1"), output)
    append_record(_record("A2", agenda_score=0, agenda_present=False, all_subjects=False), output)

    rows = load_records(output)
    assert len(rows) == 2
    assert rows[0].student_id == "A1"
    assert rows[1].agenda_present is False
    assert rows[0].check_mode == "both"


def test_reliability_summary(tmp_path: Path) -> None:
    output = tmp_path / "checks.csv"
    append_record(_record("A1", agenda_score=10), output)
    append_record(_record("A1", agenda_score=7), output)
    append_record(_record("A2", agenda_score=10), output)

    records = load_records(output)
    summary = summarize_reliability(records)
    assert summary["A1"] == 50.0
    assert summary["A2"] == 100.0


def test_load_with_corrupt_row_warns(tmp_path: Path) -> None:
    output = tmp_path / "checks.csv"
    output.write_text(
        "StudentID,StudentName,Grade,Period,Date,Checker,NotebookScore,AgendaPresent,EntryWritten,AllSubjectsFilled,Organized,AgendaScore,GradebookScore,Flag\n"
        "A1,\"A1, Test\",7,2,2026-02-21,Ms Rivera,8,True,True,True,True,10,9,\n"
        "BADROW\n",
        encoding="utf-8",
    )
    result = load_records_with_warnings(output)
    assert len(result.records) == 1
    assert len(result.warnings) == 1


def test_load_records_normalizes_legacy_flags_on_read(tmp_path: Path) -> None:
    output = tmp_path / "checks.csv"
    output.write_text(
        "StudentID,StudentName,Grade,Period,Date,Checker,NotebookScore,AgendaPresent,EntryWritten,AllSubjectsFilled,Organized,AgendaScore,GradebookScore,Flag,Comments\n"
        "A1,\"A1, Test\",7,2,2026-02-21,Ms Rivera,8,True,False,True,True,7,7.5,Entry not written,\n"
        "A2,\"A2, Test\",7,2,2026-02-21,Ms Rivera,8,True,True,True,True,10,9.0,Needs conference,\n",
        encoding="utf-8",
    )

    rows = load_records(output)
    assert len(rows) == 2
    assert rows[0].flag == "Blank entries"
    assert rows[1].flag == "Needs conference"


def test_append_record_auto_upgrades_legacy_headers_with_comments(tmp_path: Path) -> None:
    output = tmp_path / "checks.csv"
    output.write_text(
        "StudentID,StudentName,Grade,Period,Date,Checker,NotebookScore,AgendaPresent,EntryWritten,AllSubjectsFilled,Organized,AgendaScore,GradebookScore,Flag\n"
        "A1,\"A1, Test\",7,2,2026-02-21,Ms Rivera,8,True,True,True,True,10,18,\n",
        encoding="utf-8",
    )

    append_record(_record("A2", comments="Needs follow-up"), output)

    header = output.read_text(encoding="utf-8").splitlines()[0]
    assert header.endswith(",Comments")
    rows = load_records(output)
    assert len(rows) == 2
    assert rows[0].student_id == "A1"
    assert rows[0].comments == ""
    assert rows[1].student_id == "A2"
    assert rows[1].comments == "Needs follow-up"


def test_header_upgrade_preserves_non_empty_legacy_values(tmp_path: Path) -> None:
    output = tmp_path / "checks.csv"
    output.write_text(
        "StudentID,StudentName,Grade,Period,Date,Checker,NotebookScore,AgendaPresent,EntryWritten,AllSubjectsFilled,Organized,AgendaScore,GradebookScore,Flag,LegacyNote\n"
        "A1,\"A1, Test\",7,2,2026-02-21,Ms Rivera,8,True,True,True,True,10,18,,Keep me\n",
        encoding="utf-8",
    )

    append_record(_record("A2", comments="Stored comment"), output)

    with output.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames is not None
        assert reader.fieldnames == [
            "StudentID",
            "StudentName",
            "Grade",
            "Period",
            "Date",
            "Checker",
            "NotebookScore",
            "AgendaPresent",
            "EntryWritten",
            "AllSubjectsFilled",
            "Organized",
            "AgendaScore",
            "GradebookScore",
            "Flag",
            "LegacyNote",
            "CheckMode",
            "AgendaFilledToday",
            "AgendaReadable",
            "NotebookPresentDetail",
            "NotebookWorkToday",
            "NotebookOrganized",
            "CommentTags",
            "CommentDeduction",
            "InternalScore",
            "ScoreModel",
            "Comments",
        ]
        rows = list(reader)

    assert rows[0]["LegacyNote"] == "Keep me"
    assert rows[1]["LegacyNote"] == ""
    assert rows[1]["CheckMode"] == "both"
    assert rows[1]["Comments"] == "Stored comment"


def test_round_trip_new_scoring_and_comment_fields(tmp_path: Path) -> None:
    output = tmp_path / "checks.csv"
    record = CheckRecord(
        student_id="A1",
        student_name="A1, Test",
        grade=7,
        check_mode="both",
        date="2026-02-21",
        checker="Ms Rivera",
        notebook_score=9.0,
        agenda_present=True,
        entry_written=True,
        all_subjects_filled=False,
        organized=False,
        agenda_score=8,
        gradebook_score=8.25,
        agenda_filled_today="partial",
        agenda_readable=False,
        notebook_present_detail=True,
        notebook_work_today="complete",
        notebook_organized=False,
        comment_tags="Disorganized|Missing_Date",
        comment_deduction=0.75,
        internal_score=16.5,
        score_model=SCORE_MODEL_INTERNAL20_GRADEBOOK10_V1,
        flag="Messy/unreadable",
        comments="Needs cleaner layout",
    )

    append_record(record, output)
    rows = load_records(output)
    assert len(rows) == 1
    loaded = rows[0]
    assert loaded.agenda_filled_today == "partial"
    assert loaded.notebook_work_today == "complete"
    assert loaded.comment_tags == "Disorganized|Missing_Date"
    assert loaded.comment_deduction == 0.75
    assert loaded.internal_score == 16.5
    assert loaded.score_model == SCORE_MODEL_INTERNAL20_GRADEBOOK10_V1
    assert loaded.check_mode == "both"


def test_remove_last_record(tmp_path: Path) -> None:
    output = tmp_path / "checks.csv"
    append_record(_record("A1"), output)
    append_record(_record("A2"), output)

    removed = remove_last_record(output)
    assert removed is True
    rows = load_records(output)
    assert [row.student_id for row in rows] == ["A1"]


def test_export_summary_csv(tmp_path: Path) -> None:
    output = tmp_path / "summary.csv"
    export_summary_csv(
        output,
        [
            {
                "StudentID": "A1",
                "StudentName": "A1, Test",
                "Grade": 7,
                "TotalChecks": 5,
                "ReliabilityPercent": 80.0,
                "MissingAgendaCount": 1,
                "IncompleteSubjectsCount": 1,
            }
        ],
    )
    text = output.read_text(encoding="utf-8")
    assert "ReliabilityPercent" in text
    assert "A1" in text


def test_load_insights_visibility_missing_file(tmp_path: Path) -> None:
    prefs = tmp_path / "ui_preferences.json"
    assert load_insights_visibility(prefs) == {}


def test_insights_visibility_round_trip(tmp_path: Path) -> None:
    prefs = tmp_path / "ui_preferences.json"
    expected = {"6:1": True, "7:2": False}
    save_insights_visibility(prefs, expected)
    assert load_insights_visibility(prefs) == expected


def test_load_insights_visibility_malformed_json(tmp_path: Path) -> None:
    prefs = tmp_path / "ui_preferences.json"
    prefs.write_text("{not valid json", encoding="utf-8")
    assert load_insights_visibility(prefs) == {}


def test_load_insights_visibility_ignores_non_bool_values(tmp_path: Path) -> None:
    prefs = tmp_path / "ui_preferences.json"
    prefs.write_text(
        '{"insights_visibility_by_class":{"6:1":"yes","7:2":1,"8:3":false}}',
        encoding="utf-8",
    )
    assert load_insights_visibility(prefs) == {"8:3": False}

