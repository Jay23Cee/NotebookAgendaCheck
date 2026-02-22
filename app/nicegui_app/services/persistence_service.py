from __future__ import annotations

from datetime import date, datetime
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
        student_id: str | None = None,
        check_date: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> LoadResult:
        result = self.load_all()
        filtered = [record for record in result.records if record.grade == grade]
        if student_id is not None:
            filtered = [record for record in filtered if record.student_id == str(student_id).strip()]

        if check_date is not None:
            exact_date = _parse_supported_date(check_date)
            if exact_date is None:
                filtered = [record for record in filtered if record.date == check_date]
            else:
                exact_filtered: list[CheckRecord] = []
                for record in filtered:
                    record_date = _parse_supported_date(record.date)
                    if record_date is None:
                        continue
                    if record_date == exact_date:
                        exact_filtered.append(record)
                filtered = exact_filtered

        start_date_obj = _parse_supported_date(start_date)
        end_date_obj = _parse_supported_date(end_date)
        if start_date_obj is not None or end_date_obj is not None:
            date_filtered: list[CheckRecord] = []
            for record in filtered:
                record_date = _parse_supported_date(record.date)
                if record_date is None:
                    continue
                if start_date_obj is not None and record_date < start_date_obj:
                    continue
                if end_date_obj is not None and record_date > end_date_obj:
                    continue
                date_filtered.append(record)
            filtered = date_filtered
        return LoadResult(records=filtered, warnings=result.warnings)


def _parse_supported_date(value: str | None) -> date | None:
    cleaned = str(value or "").strip()
    if not cleaned:
        return None

    for date_format in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(cleaned, date_format).date()
        except ValueError:
            continue
    return None
