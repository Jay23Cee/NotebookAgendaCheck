from __future__ import annotations

from pathlib import Path

from app.constants import DEFAULT_OUTPUT_FILE
from app.models import CheckRecord
from app.storage import LoadResult, append_record, load_records_with_warnings, remove_last_record


class PersistenceService:
    def __init__(self, output_file: Path = DEFAULT_OUTPUT_FILE) -> None:
        self.output_file = output_file

    def append(self, record: CheckRecord) -> None:
        append_record(record, self.output_file)

    def undo_last(self) -> bool:
        return remove_last_record(self.output_file)

    def load_all(self) -> LoadResult:
        return load_records_with_warnings(self.output_file)

    def load_for_class(
        self,
        *,
        grade: int,
        check_date: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> LoadResult:
        result = self.load_all()
        filtered = [record for record in result.records if record.grade == grade]
        if check_date is not None:
            filtered = [record for record in filtered if record.date == check_date]
        if start_date is not None:
            filtered = [record for record in filtered if record.date >= start_date]
        if end_date is not None:
            filtered = [record for record in filtered if record.date <= end_date]
        return LoadResult(records=filtered, warnings=result.warnings)
