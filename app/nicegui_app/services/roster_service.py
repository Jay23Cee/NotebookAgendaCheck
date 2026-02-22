from __future__ import annotations

from pathlib import Path

from app.constants import DEFAULT_STUDENTS_FILE
from app.students import Student, filter_students, load_students


class RosterService:
    def __init__(self, students_file: Path = DEFAULT_STUDENTS_FILE) -> None:
        self.students_file = students_file
        self._cache: list[Student] | None = None

    def load_all(self) -> list[Student]:
        if not self.students_file.exists():
            raise FileNotFoundError(f"Students file not found: {self.students_file}")
        if self._cache is None:
            self._cache = load_students(self.students_file)
        return self._cache

    def class_roster(self, *, grade: int) -> list[Student]:
        students = filter_students(self.load_all(), grade=grade)
        if not students:
            return []

        deduped: list[Student] = []
        seen_ids: set[str] = set()
        for student in students:
            if student.student_id in seen_ids:
                continue
            seen_ids.add(student.student_id)
            deduped.append(student)
        return deduped

    def checker_options(self, *, grade: int) -> tuple[dict[str, str], dict[str, str]]:
        roster = self.class_roster(grade=grade)
        checker_name_by_id = {student.student_id: student.full_name for student in roster}
        checker_select_options = {
            student.student_id: f"{student.full_name} ({student.student_id})"
            for student in roster
        }
        return checker_name_by_id, checker_select_options
