from __future__ import annotations

from pathlib import Path

from app.models import CheckRecord
from app.nicegui_app.services.history_service import HistoryService
from app.nicegui_app.services.persistence_service import PersistenceService
from app.nicegui_app.services.roster_service import RosterService
from app.nicegui_app.services.scoring_service import COMMENT_TAGS_BY_GROUP
from app.nicegui_app.services.workflow_controller import NAWorkflowController
from app.scoring import SCORE_MODEL_INTERNAL20_GRADEBOOK10_V1
from app.storage import LoadResult
from app.students import Student


class StubRosterService(RosterService):
    def __init__(self, roster_by_grade: dict[int, list[Student]]) -> None:
        self.roster_by_grade = roster_by_grade

    def class_roster(self, *, grade: int) -> list[Student]:  # type: ignore[override]
        return list(self.roster_by_grade.get(grade, []))

    def checker_options(self, *, grade: int) -> tuple[dict[str, str], dict[str, str]]:  # type: ignore[override]
        roster = self.class_roster(grade=grade)
        checker_name_by_id = {student.student_id: student.full_name for student in roster}
        checker_label_by_id = {
            student.student_id: f"{student.full_name} ({student.student_id})" for student in roster
        }
        return checker_name_by_id, checker_label_by_id


class StubPersistenceService(PersistenceService):
    def __init__(self) -> None:
        self.output_file = Path("records/notebook_agenda_checks.csv")
        self.records: list[CheckRecord] = []
        self.warnings: list[str] = []

    def append(self, record: CheckRecord) -> None:  # type: ignore[override]
        self.records.append(record)

    def undo_last(self) -> bool:  # type: ignore[override]
        if not self.records:
            return False
        self.records.pop()
        return True

    def load_for_class(  # type: ignore[override]
        self,
        *,
        grade: int,
        check_date: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> LoadResult:
        filtered = [row for row in self.records if row.grade == grade]
        if check_date is not None:
            filtered = [row for row in filtered if row.date == check_date]
        if start_date is not None:
            filtered = [row for row in filtered if row.date >= start_date]
        if end_date is not None:
            filtered = [row for row in filtered if row.date <= end_date]
        return LoadResult(records=filtered, warnings=list(self.warnings))


def _student(student_id: str, grade: int = 7) -> Student:
    return Student(student_id=student_id, first_name="Ada", last_name="Lovelace", grade=grade)


def _controller() -> tuple[NAWorkflowController, StubPersistenceService]:
    roster = [_student("S1"), Student(student_id="S2", first_name="Grace", last_name="Hopper", grade=7)]
    roster_service = StubRosterService({7: roster})
    persistence = StubPersistenceService()
    controller = NAWorkflowController(
        roster_service=roster_service,
        persistence_service=persistence,
        history_service=HistoryService(),
    )
    return controller, persistence


def _set_full_scores(controller: NAWorkflowController) -> None:
    controller.set_agenda_present(True)
    controller.set_agenda_filled_today("complete")
    controller.set_agenda_readable(True)
    controller.set_notebook_present(True)
    controller.set_notebook_work_today("complete")
    controller.set_notebook_organized(True)


def test_set_grade_loads_roster_and_checker_options() -> None:
    controller, _persistence = _controller()

    result = controller.set_grade("7")
    assert result.ok is True
    assert controller.state.session.locked is False
    assert len(controller.state.session.roster) == 2
    assert controller.state.session.checker_mode == "teacher"
    assert controller.state.session.checker_id is None
    assert controller.state.session.progress_text == "Student 1 of 2"
    assert controller.state.session.check_mode is None


def test_mode_must_be_selected_before_save() -> None:
    controller, persistence = _controller()
    controller.set_grade("7")
    _set_full_scores(controller)

    result = controller.save_next()

    assert result.ok is False
    assert "check mode" in result.message.lower()
    assert len(persistence.records) == 0


def test_save_next_persists_score_model_mode_deductions_and_flag() -> None:
    controller, persistence = _controller()
    controller.set_grade("7")
    controller.set_check_mode("both")
    _set_full_scores(controller)

    missing_date_tag = COMMENT_TAGS_BY_GROUP["legibility"][-1].tag
    incomplete_tag = COMMENT_TAGS_BY_GROUP["completion"][0].tag
    controller.toggle_comment_tag(missing_date_tag, True)
    controller.toggle_comment_tag(incomplete_tag, True)
    controller.set_comment_enabled(True)
    controller.set_comment_text("Improving, still missing date")

    result = controller.save_next()

    assert result.ok is True
    assert len(persistence.records) == 1
    saved = persistence.records[0]
    assert saved.checker == "TEACHER"
    assert saved.check_mode == "both"
    assert saved.comment_deduction == 5.0
    assert saved.internal_score == 15.0
    assert saved.gradebook_score == 7.5
    assert saved.score_model == SCORE_MODEL_INTERNAL20_GRADEBOOK10_V1
    assert set(saved.comment_tags.split("|")) == {missing_date_tag, incomplete_tag}
    assert controller.state.session.current_index == 1
    assert controller.state.session.check_mode_locked is True


def test_save_next_with_empty_comment_auto_turns_off_comment_field() -> None:
    controller, persistence = _controller()
    controller.set_grade("7")
    controller.set_check_mode("both")
    _set_full_scores(controller)

    controller.set_comment_enabled(True)
    controller.set_comment_text("   ")

    result = controller.save_next()

    assert result.ok is True
    assert len(persistence.records) == 1
    saved = persistence.records[0]
    assert saved.comments == ""
    assert saved.comment_tags == ""


def test_notebook_only_mode_uses_notebook_as_gradebook_scale() -> None:
    controller, persistence = _controller()
    controller.set_grade("7")
    controller.set_check_mode("notebook_only")
    _set_full_scores(controller)
    incomplete_tag = COMMENT_TAGS_BY_GROUP["completion"][0].tag
    controller.toggle_comment_tag(incomplete_tag, True)

    result = controller.save_next()

    assert result.ok is True
    saved = persistence.records[0]
    assert saved.check_mode == "notebook_only"
    assert saved.notebook_score == 10.0
    assert saved.agenda_score == 0
    assert saved.gradebook_score == 5.0
    assert saved.internal_score == 10.0


def test_agenda_only_mode_uses_agenda_as_gradebook_scale() -> None:
    controller, persistence = _controller()
    controller.set_grade("7")
    controller.set_check_mode("agenda_only")
    _set_full_scores(controller)
    controller.toggle_comment_tag(COMMENT_TAGS_BY_GROUP["legibility"][-1].tag, True)

    result = controller.save_next()

    assert result.ok is True
    saved = persistence.records[0]
    assert saved.check_mode == "agenda_only"
    assert saved.notebook_score == 0.0
    assert saved.agenda_score == 10
    assert saved.gradebook_score == 9.75
    assert saved.internal_score == 19.5


def test_save_next_student_mode_requires_checker_selection() -> None:
    controller, persistence = _controller()
    controller.set_grade("7")
    controller.set_check_mode("both")
    _set_full_scores(controller)

    mode_result = controller.set_checker_mode("student")
    assert mode_result.ok is True
    assert controller.state.session.checker_mode == "student"
    assert controller.state.session.checker_id is None

    result = controller.save_next()

    assert result.ok is False
    assert result.level == "error"
    assert result.message == "Select student checker from this class roster."
    assert len(persistence.records) == 0


def test_save_next_student_mode_persists_selected_checker_name() -> None:
    controller, persistence = _controller()
    controller.set_grade("7")
    controller.set_check_mode("both")
    _set_full_scores(controller)

    controller.set_checker_mode("student")
    checker_result = controller.set_checker_student("S2")
    assert checker_result.ok is True

    result = controller.save_next()

    assert result.ok is True
    assert len(persistence.records) == 1
    saved = persistence.records[0]
    assert saved.checker == "Hopper, Grace"


def test_student_checker_mode_updates_save_readiness() -> None:
    controller, _persistence = _controller()
    controller.set_grade("7")

    assert controller.state.can_save is False
    controller.set_check_mode("both")
    assert controller.state.can_save is True
    controller.set_checker_mode("student")
    assert controller.state.can_save is False

    controller.set_checker_student("S1")
    assert controller.state.can_save is True


def test_undo_last_restores_previous_student_and_form_state() -> None:
    controller, persistence = _controller()
    controller.set_grade("7")
    controller.set_check_mode("both")

    controller.set_agenda_present(True)
    controller.set_agenda_filled_today("partial")
    controller.set_agenda_readable(True)
    controller.set_notebook_present(True)
    controller.set_notebook_work_today("partial")
    controller.set_notebook_organized(False)

    controller.set_comment_enabled(True)
    controller.set_comment_text("Needs more detail")
    controller.save_next()

    assert controller.state.session.current_index == 1
    assert len(persistence.records) == 1

    result = controller.undo_last()

    assert result.ok is True
    assert controller.state.session.current_index == 0
    assert len(persistence.records) == 0
    assert controller.state.form.agenda_present is True
    assert controller.state.form.agenda_filled_today == "partial"
    assert controller.state.form.notebook_present is True
    assert controller.state.form.comment_enabled is True
    assert controller.state.form.comments == "Needs more detail"
    assert controller.state.session.check_mode_locked is False


def test_history_rows_preserve_legacy_score_inference() -> None:
    controller, persistence = _controller()
    controller.set_grade("7")

    persistence.records = [
        CheckRecord(
            student_id="S1",
            student_name="Lovelace, Ada",
            grade=7,
            check_mode="both",
            date=controller.state.session.check_date,
            checker="Lovelace, Ada",
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
        ),
        CheckRecord(
            student_id="S2",
            student_name="Hopper, Grace",
            grade=7,
            check_mode="both",
            date=controller.state.session.check_date,
            checker="Lovelace, Ada",
            notebook_score=10.0,
            agenda_present=True,
            entry_written=True,
            all_subjects_filled=True,
            organized=True,
            agenda_score=10,
            gradebook_score=18.0,
            score_model="",
            flag="None",
        ),
    ]

    rows, warnings = controller.history_rows(
        start_date=controller.state.session.check_date,
        end_date=controller.state.session.check_date,
    )

    assert warnings == []
    assert len(rows) == 2
    assert rows[0].internal_score == 16.5
    assert rows[0].gradebook_score == 8.25
    assert rows[1].internal_score == 18.0
    assert rows[1].gradebook_score == 9.0
    assert rows[0].check_mode == "both"


def test_set_grade_none_relocks_ui() -> None:
    controller, _persistence = _controller()
    controller.set_grade("7")
    controller.set_check_mode("both")

    result = controller.set_grade(None)

    assert result.ok is True
    assert controller.state.session.locked is True
    assert controller.state.session.roster == []
    assert controller.state.save_history == []
    assert controller.state.session.check_mode is None
