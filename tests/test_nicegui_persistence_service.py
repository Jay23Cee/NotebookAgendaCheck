from __future__ import annotations

from pathlib import Path

from app.models import CheckRecord
from app.nicegui_app.services.persistence_service import PersistenceService


def _record(*, student_id: str, student_name: str, date: str, grade: int = 7) -> CheckRecord:
    return CheckRecord(
        student_id=student_id,
        student_name=student_name,
        grade=grade,
        check_mode="both",
        date=date,
        checker="TEACHER",
        notebook_score=10.0,
        agenda_present=True,
        entry_written=True,
        all_subjects_filled=True,
        organized=True,
        agenda_score=10,
        gradebook_score=10.0,
    )


def test_load_for_class_filters_by_student_and_mixed_date_formats(tmp_path: Path) -> None:
    output = tmp_path / "checks.csv"
    service = PersistenceService(output)
    service.append(_record(student_id="S1", student_name="Lovelace, Ada", date="2026-02-20"))
    service.append(_record(student_id="S1", student_name="Lovelace, Ada", date="02/21/2026"))
    service.append(_record(student_id="S2", student_name="Hopper, Grace", date="02/22/2026"))

    result = service.load_for_class(
        grade=7,
        student_id="S1",
        start_date="2026-02-20",
        end_date="02/21/2026",
    )

    assert result.warnings == []
    assert len(result.records) == 2
    assert all(record.student_id == "S1" for record in result.records)


def test_load_for_class_skips_unparsable_record_dates_when_range_filtering(tmp_path: Path) -> None:
    output = tmp_path / "checks.csv"
    service = PersistenceService(output)
    service.append(_record(student_id="S1", student_name="Lovelace, Ada", date="02/22/2026"))
    service.append(_record(student_id="S1", student_name="Lovelace, Ada", date="not-a-date"))

    result = service.load_for_class(
        grade=7,
        start_date="02/01/2026",
        end_date="02/28/2026",
    )

    assert result.warnings == []
    assert len(result.records) == 1
    assert result.records[0].date == "02/22/2026"


def test_load_for_class_preserves_row_parse_warnings(tmp_path: Path) -> None:
    output = tmp_path / "checks.csv"
    output.write_text(
        "\n".join(
            [
                "StudentID,StudentName,Grade,CheckMode,Date,Checker,NotebookScore,AgendaPresent,EntryWritten,AllSubjectsFilled,Organized,AgendaScore,GradebookScore,AgendaFilledToday,AgendaReadable,NotebookPresentDetail,NotebookWorkToday,NotebookOrganized,CommentTags,CommentDeduction,InternalScore,ScoreModel,Flag,Comments",
                "S1,\"Lovelace, Ada\",7,both,02/22/2026,TEACHER,10,True,True,True,True,10,10,complete,True,True,complete,True,,0,20,internal20_gradebook10_v1,None,",
                "S2,\"Hopper, Grace\",7,both,02/22/2026,TEACHER,10,maybe,True,True,True,10,10,complete,True,True,complete,True,,0,20,internal20_gradebook10_v1,None,",
            ]
        ),
        encoding="utf-8",
    )
    service = PersistenceService(output)

    result = service.load_for_class(grade=7)

    assert len(result.records) == 1
    assert len(result.warnings) == 1
