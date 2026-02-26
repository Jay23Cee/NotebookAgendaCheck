from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.models import CSV_FIELDNAMES

OUTPUT_COLUMNS = list(CSV_FIELDNAMES)


@dataclass(frozen=True)
class SavedRecordRef:
    student_id: str
    check_date: str
    grade: str
    period: str


class CsvStore:
    def __init__(self, output_path: Path) -> None:
        self.output_path = output_path

    def append_row(self, row: dict[str, object]) -> None:
        self.append_rows([row])

    def append_rows(self, rows: list[dict[str, object]]) -> None:
        if not rows:
            return

        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = self._ensure_output_headers()
        sanitized_rows = [{column: row.get(column, "") for column in fieldnames} for row in rows]
        needs_header = (not self.output_path.exists()) or self.output_path.stat().st_size == 0
        with self.output_path.open("a", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            if needs_header:
                writer.writeheader()
            writer.writerows(sanitized_rows)

    def undo_last_saved_row(self) -> bool:
        return self.undo_last_saved_rows(1) == 1

    def undo_last_saved_rows(self, count: int) -> int:
        if count <= 0:
            return 0
        if not self.output_path.exists():
            return 0

        with self.output_path.open("r", newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            rows = list(reader)
            fieldnames = reader.fieldnames or list(OUTPUT_COLUMNS)

        if not rows:
            return 0

        removed = min(count, len(rows))
        rows = rows[:-removed]
        with self.output_path.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self._sanitize_rows_for_headers(rows, fieldnames))
        return removed

    def list_saved_refs(self) -> list[SavedRecordRef]:
        if not self.output_path.exists():
            return []

        refs: list[SavedRecordRef] = []
        with self.output_path.open("r", newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                student_id = self._value(row, ("StudentID", "student_id"))
                if not student_id:
                    continue

                normalized_date = self._normalized_date(
                    self._value(row, ("Date", "check_date"))
                )
                if not normalized_date:
                    continue

                refs.append(
                    SavedRecordRef(
                        student_id=student_id,
                        check_date=normalized_date,
                        grade=self._value(row, ("Grade", "grade")),
                        period=self._value(row, ("Period", "period")),
                    )
                )
        return refs

    def _ensure_output_headers(self) -> list[str]:
        if (not self.output_path.exists()) or self.output_path.stat().st_size == 0:
            return list(OUTPUT_COLUMNS)

        with self.output_path.open("r", newline="", encoding="utf-8") as csv_file:
            reader = csv.reader(csv_file)
            existing_headers = next(reader, None)

        cleaned_existing = [str(value).strip() for value in (existing_headers or []) if str(value).strip()]
        if not cleaned_existing:
            return list(OUTPUT_COLUMNS)

        missing = [header for header in OUTPUT_COLUMNS if header not in cleaned_existing]
        if not missing:
            return cleaned_existing

        upgraded_headers = [*cleaned_existing, *missing]
        with self.output_path.open("r", newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            rows = list(reader)

        with self.output_path.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=upgraded_headers)
            writer.writeheader()
            writer.writerows(self._sanitize_rows_for_headers(rows, upgraded_headers))
        return upgraded_headers

    def _sanitize_rows_for_headers(
        self,
        rows: list[dict[str, str]],
        headers: list[str],
    ) -> list[dict[str, str]]:
        valid = set(headers)
        return [{key: value for key, value in row.items() if key in valid} for row in rows]

    def _value(self, row: dict[str, str], aliases: tuple[str, ...]) -> str:
        for alias in aliases:
            if alias in row:
                return str(row.get(alias, "")).strip()
        return ""

    def _normalized_date(self, value: str) -> str:
        raw = str(value or "").strip()
        if not raw:
            return ""
        for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
            try:
                parsed = datetime.strptime(raw, fmt)
                return parsed.strftime("%m/%d/%Y")
            except ValueError:
                continue
        return ""
