from __future__ import annotations

from collections.abc import Callable
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
import time
from typing import TypeVar

from app.models import CSV_FIELDNAMES
from app.nicegui_app.na_check.reliability import LogSeverity, ResilientErrorLogger

OUTPUT_COLUMNS = ["StudentID", "StudentName", "Grade", "Period"] + [
    column for column in CSV_FIELDNAMES if column not in {"StudentID", "StudentName", "Grade"}
]
REQUIRED_HEADERS = {"StudentID", "Date"}
SHARE_LOCK_WINERRORS = {32, 33}
T = TypeVar("T")


@dataclass(frozen=True)
class SavedRecordRef:
    student_id: str
    check_date: str
    grade: str
    period: str


class CsvCorruptionError(ValueError):
    pass


class CsvValidationError(ValueError):
    pass


class CsvStore:
    def __init__(
        self,
        output_path: Path,
        *,
        quarantine_dir: Path | None = None,
        session_id: str = "local",
        logger: ResilientErrorLogger | None = None,
        max_retry_attempts: int = 2,
        retry_delay_seconds: float = 0.150,
    ) -> None:
        self.output_path = output_path
        self.quarantine_dir = quarantine_dir if quarantine_dir is not None else output_path.parent / "quarantine"
        self.session_id = session_id
        self.logger = logger
        self.max_retry_attempts = max(1, int(max_retry_attempts))
        self.retry_delay_seconds = max(0.0, float(retry_delay_seconds))

    def append_row(self, row: dict[str, object]) -> None:
        self.append_rows([row])

    def append_rows(self, rows: list[dict[str, object]]) -> None:
        if not rows:
            return
        self._validate_rows(rows)

        def write_operation() -> None:
            headers, current_rows = self._load_snapshot(recover_corruption=True, operation="append_rows")
            writable_headers = self._headers_for_write(headers)
            sanitized_current = self._sanitize_rows_for_headers(current_rows, writable_headers)
            sanitized_new = [{column: row.get(column, "") for column in writable_headers} for row in rows]
            self._write_snapshot_atomic(writable_headers, [*sanitized_current, *sanitized_new])

        self._with_retry(write_operation, operation="append_rows")

    def undo_last_saved_row(self) -> bool:
        return self.undo_last_saved_rows(1) == 1

    def undo_last_saved_rows(self, count: int) -> int:
        if count <= 0:
            return 0

        def undo_operation() -> int:
            headers, rows = self._load_snapshot(recover_corruption=True, operation="undo_last_saved_rows")
            if not rows:
                return 0

            removed = min(count, len(rows))
            remaining_rows = rows[:-removed]
            self._write_snapshot_atomic(headers, self._sanitize_rows_for_headers(remaining_rows, headers))
            return removed

        return self._with_retry(undo_operation, operation="undo_last_saved_rows")

    def list_saved_refs(self) -> list[SavedRecordRef]:
        def read_operation() -> list[SavedRecordRef]:
            _headers, rows = self._load_snapshot(recover_corruption=True, operation="list_saved_refs")
            if not rows:
                return []

            refs: list[SavedRecordRef] = []
            for row in rows:
                student_id = self._value(row, ("StudentID", "student_id"))
                if not student_id:
                    continue

                normalized_date = self._normalized_date(self._value(row, ("Date", "check_date")))
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

        return self._with_retry(read_operation, operation="list_saved_refs")

    def _validate_rows(self, rows: list[dict[str, object]]) -> None:
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                raise CsvValidationError(f"Row at index {index} must be a dict")
            for key in row:
                if not isinstance(key, str) or not key.strip():
                    raise CsvValidationError(f"Row at index {index} has invalid key: {key!r}")

    def _with_retry(self, action: Callable[[], T], *, operation: str) -> T:
        last_error: Exception | None = None
        for attempt in range(1, self.max_retry_attempts + 1):
            try:
                return action()
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt < self.max_retry_attempts and self._is_share_lock_error(exc):
                    self._log(
                        severity="WARNING",
                        operation=operation,
                        message="Transient file lock detected; retrying operation",
                        exception=exc,
                        context={
                            "attempt": attempt,
                            "max_attempts": self.max_retry_attempts,
                            "retry_delay_seconds": self.retry_delay_seconds,
                            "output_path": str(self.output_path),
                        },
                    )
                    time.sleep(self.retry_delay_seconds)
                    continue
                raise
        assert last_error is not None
        raise last_error

    def _load_snapshot(self, *, recover_corruption: bool, operation: str) -> tuple[list[str], list[dict[str, str]]]:
        if (not self.output_path.exists()) or self.output_path.stat().st_size == 0:
            return list(OUTPUT_COLUMNS), []

        try:
            headers, rows = self._read_snapshot()
            return self._headers_for_write(headers), rows
        except CsvCorruptionError as exc:
            if not recover_corruption:
                raise
            self._recover_from_corruption(cause=exc, operation=operation)
            return list(OUTPUT_COLUMNS), []

    def _read_snapshot(self) -> tuple[list[str], list[dict[str, str]]]:
        try:
            with self.output_path.open("r", newline="", encoding="utf-8") as csv_file:
                reader = csv.DictReader(csv_file)
                headers = self._normalized_headers(reader.fieldnames)
                rows = [
                    {
                        str(key): "" if value is None else str(value)
                        for key, value in row.items()
                        if key is not None
                    }
                    for row in reader
                ]
                return headers, rows
        except UnicodeDecodeError as exc:
            raise CsvCorruptionError("CSV contains invalid UTF-8 bytes") from exc
        except csv.Error as exc:
            raise CsvCorruptionError("CSV contains malformed row or quoting") from exc

    def _normalized_headers(self, headers: list[str] | None) -> list[str]:
        cleaned_headers = [str(header).strip() for header in (headers or []) if str(header).strip()]
        if not cleaned_headers:
            raise CsvCorruptionError("CSV header row is missing or empty")
        if len(cleaned_headers) != len(set(cleaned_headers)):
            raise CsvCorruptionError("CSV header row contains duplicate columns")

        missing_required = sorted(header for header in REQUIRED_HEADERS if header not in cleaned_headers)
        if missing_required:
            missing_text = ", ".join(missing_required)
            raise CsvCorruptionError(f"CSV is missing required headers: {missing_text}")

        return cleaned_headers

    def _headers_for_write(self, existing_headers: list[str]) -> list[str]:
        cleaned_existing = [header for header in existing_headers if header]
        if not cleaned_existing:
            return list(OUTPUT_COLUMNS)
        missing_headers = [header for header in OUTPUT_COLUMNS if header not in cleaned_existing]
        return [*cleaned_existing, *missing_headers]

    def _write_snapshot_atomic(self, headers: list[str], rows: list[dict[str, object]]) -> None:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        temp_file = self.output_path.with_name(
            f"{self.output_path.name}.tmp.{os.getpid()}.{time.time_ns()}"
        )
        try:
            with temp_file.open("w", newline="", encoding="utf-8") as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=headers)
                writer.writeheader()
                writer.writerows(self._sanitize_rows_for_headers(rows, headers))
                csv_file.flush()
                os.fsync(csv_file.fileno())
            os.replace(temp_file, self.output_path)
        finally:
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except OSError:
                    pass

    def _recover_from_corruption(self, *, cause: Exception, operation: str) -> None:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        quarantine_path = self.quarantine_dir / (
            f"{self.output_path.name}.corrupt.{timestamp}.{self.session_id}.csv"
        )

        quarantine_error: Exception | None = None
        try:
            self.quarantine_dir.mkdir(parents=True, exist_ok=True)
            if self.output_path.exists():
                self.output_path.replace(quarantine_path)
        except Exception as exc:  # noqa: BLE001
            quarantine_error = exc
            self._log(
                severity="CRITICAL",
                operation=operation,
                message="Failed to quarantine corrupted CSV before recreation",
                exception=exc,
                context={
                    "output_path": str(self.output_path),
                    "quarantine_path": str(quarantine_path),
                },
            )

        recreate_error: Exception | None = None
        try:
            self._write_snapshot_atomic(list(OUTPUT_COLUMNS), [])
        except Exception as exc:  # noqa: BLE001
            recreate_error = exc
            self._log(
                severity="CRITICAL",
                operation=operation,
                message="Failed to recreate clean CSV after corruption",
                exception=exc,
                context={"output_path": str(self.output_path)},
            )

        self._log(
            severity="CRITICAL",
            operation=operation,
            message="Recovered from corrupted CSV using quarantine-and-recreate policy",
            exception=cause,
            context={
                "output_path": str(self.output_path),
                "quarantine_path": str(quarantine_path),
                "quarantine_move_ok": quarantine_error is None,
                "recreate_ok": recreate_error is None,
            },
        )

    def _is_share_lock_error(self, error: Exception) -> bool:
        if not isinstance(error, (OSError, PermissionError)):
            return False
        winerror = getattr(error, "winerror", None)
        if winerror in SHARE_LOCK_WINERRORS:
            return True
        message = str(error).lower()
        return "used by another process" in message or "sharing violation" in message

    def _sanitize_rows_for_headers(
        self,
        rows: list[dict[str, object]],
        headers: list[str],
    ) -> list[dict[str, object]]:
        return [{header: row.get(header, "") for header in headers} for row in rows]

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

    def _log(
        self,
        *,
        severity: LogSeverity,
        operation: str,
        message: str,
        exception: BaseException | None = None,
        context: dict[str, object] | None = None,
    ) -> None:
        if self.logger is None:
            return
        self.logger.log_exception(
            severity=severity,
            source="CsvStore",
            operation=operation,
            message=message,
            exception=exception,
            context=context,
        )
