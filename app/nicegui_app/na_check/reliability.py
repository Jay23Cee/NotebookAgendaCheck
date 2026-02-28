from __future__ import annotations

from collections import deque
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time
import traceback
from typing import Literal

LogSeverity = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

ERROR_LOG_COLUMNS = [
    "TimestampUtc",
    "SessionID",
    "Severity",
    "Source",
    "Operation",
    "Message",
    "ExceptionType",
    "ExceptionMessage",
    "ContextJson",
    "Traceback",
]


def _utc_now_text() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _context_json(context: dict[str, object] | None) -> str:
    if context is None:
        return "{}"
    try:
        return json.dumps(context, sort_keys=True, ensure_ascii=False, default=str)
    except Exception:  # noqa: BLE001
        return json.dumps({"context_repr": repr(context)}, ensure_ascii=False)


@dataclass(frozen=True)
class ErrorEvent:
    timestamp_utc: str
    session_id: str
    severity: LogSeverity
    source: str
    operation: str
    message: str
    exception_type: str
    exception_message: str
    context_json: str
    traceback_text: str

    @classmethod
    def from_exception(
        cls,
        *,
        session_id: str,
        severity: LogSeverity,
        source: str,
        operation: str,
        message: str,
        exception: BaseException | None = None,
        context: dict[str, object] | None = None,
    ) -> ErrorEvent:
        if exception is None:
            exception_type = ""
            exception_message = ""
            traceback_text = ""
        else:
            exception_type = type(exception).__name__
            exception_message = str(exception)
            traceback_text = "".join(
                traceback.format_exception(type(exception), exception, exception.__traceback__)
            ).strip()
        return cls(
            timestamp_utc=_utc_now_text(),
            session_id=session_id,
            severity=severity,
            source=source,
            operation=operation,
            message=message,
            exception_type=exception_type,
            exception_message=exception_message,
            context_json=_context_json(context),
            traceback_text=traceback_text,
        )

    def to_csv_row(self) -> dict[str, str]:
        return {
            "TimestampUtc": self.timestamp_utc,
            "SessionID": self.session_id,
            "Severity": self.severity,
            "Source": self.source,
            "Operation": self.operation,
            "Message": self.message,
            "ExceptionType": self.exception_type,
            "ExceptionMessage": self.exception_message,
            "ContextJson": self.context_json,
            "Traceback": self.traceback_text,
        }


class ResilientErrorLogger:
    def __init__(self, log_path: Path, *, session_id: str, ring_buffer_size: int = 200) -> None:
        self.log_path = log_path
        self.session_id = session_id
        self.ring_buffer: deque[dict[str, str]] = deque(maxlen=ring_buffer_size)

    def log(self, event: ErrorEvent) -> None:
        row = event.to_csv_row()
        try:
            self._append_csv_row(row)
            return
        except Exception as csv_exc:  # noqa: BLE001
            try:
                self._write_stderr(row, csv_exc)
                return
            except Exception as stderr_exc:  # noqa: BLE001
                try:
                    fallback_row = dict(row)
                    fallback_row["Message"] = (
                        f"{row.get('Message', '')} | "
                        f"csv_sink={type(csv_exc).__name__}: {csv_exc} | "
                        f"stderr_sink={type(stderr_exc).__name__}: {stderr_exc}"
                    )
                    self.ring_buffer.append(fallback_row)
                except Exception:  # noqa: BLE001
                    return

    def log_exception(
        self,
        *,
        severity: LogSeverity,
        source: str,
        operation: str,
        message: str,
        exception: BaseException | None = None,
        context: dict[str, object] | None = None,
    ) -> None:
        event = ErrorEvent.from_exception(
            session_id=self.session_id,
            severity=severity,
            source=source,
            operation=operation,
            message=message,
            exception=exception,
            context=context,
        )
        self.log(event)

    def _append_csv_row(self, row: dict[str, str]) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        needs_header = (not self.log_path.exists()) or self.log_path.stat().st_size == 0
        with self.log_path.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=ERROR_LOG_COLUMNS)
            if needs_header:
                writer.writeheader()
            writer.writerow({column: row.get(column, "") for column in ERROR_LOG_COLUMNS})
            handle.flush()
            os.fsync(handle.fileno())

    def _write_stderr(self, row: dict[str, str], sink_error: Exception) -> None:
        payload = dict(row)
        payload["SinkFailure"] = f"{type(sink_error).__name__}: {sink_error}"
        sys.stderr.write(json.dumps(payload, ensure_ascii=False) + "\n")
        sys.stderr.flush()


class NotificationSuppressor:
    def __init__(self, *, window_seconds: float = 5.0) -> None:
        self.window_seconds = max(0.0, float(window_seconds))
        self._events: dict[str, tuple[float, int]] = {}

    def build_signature(
        self,
        *,
        source: str,
        operation: str,
        exception_type: str,
        message: str,
    ) -> str:
        normalized_message = " ".join(str(message).strip().lower().split())
        return "|".join(
            [
                str(source).strip().lower(),
                str(operation).strip().lower(),
                str(exception_type).strip().lower(),
                normalized_message,
            ]
        )

    def register(self, signature: str, *, now: float | None = None) -> tuple[bool, int]:
        now_value = time.monotonic() if now is None else float(now)
        previous = self._events.get(signature)
        if previous is None or now_value - previous[0] > self.window_seconds:
            self._events[signature] = (now_value, 1)
            return True, 1

        count = previous[1] + 1
        self._events[signature] = (now_value, count)
        return False, count
