import csv
import json
from dataclasses import dataclass
from pathlib import Path

from app.models import CSV_FIELDNAMES, CheckRecord


@dataclass(frozen=True)
class LoadResult:
    records: list[CheckRecord]
    warnings: list[str]


def append_record(record: CheckRecord, output_file: Path) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    needs_header = (not output_file.exists()) or output_file.stat().st_size == 0
    fieldnames = CSV_FIELDNAMES if needs_header else _ensure_output_headers(output_file)

    with output_file.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        if needs_header:
            writer.writeheader()
        writer.writerow(record.to_csv_row())


def load_records(output_file: Path) -> list[CheckRecord]:
    return load_records_with_warnings(output_file).records


def load_records_with_warnings(output_file: Path) -> LoadResult:
    if not output_file.exists():
        return LoadResult(records=[], warnings=[])

    records: list[CheckRecord] = []
    warnings: list[str] = []
    with output_file.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for line_no, row in enumerate(reader, start=2):
            try:
                records.append(CheckRecord.from_csv_row(row))
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"Skipped invalid row at line {line_no}: {exc}")

    return LoadResult(records=records, warnings=warnings)


def summarize_reliability(records: list[CheckRecord]) -> dict[str, float]:
    total_by_student: dict[str, int] = {}
    completed_by_student: dict[str, int] = {}

    for record in records:
        total_by_student[record.student_id] = total_by_student.get(record.student_id, 0) + 1
        if record.agenda_score == 10:
            completed_by_student[record.student_id] = completed_by_student.get(record.student_id, 0) + 1

    summary: dict[str, float] = {}
    for student_id, total in total_by_student.items():
        completed = completed_by_student.get(student_id, 0)
        summary[student_id] = round((completed / total) * 100, 2) if total else 0.0
    return summary


def remove_last_record(output_file: Path) -> bool:
    if not output_file.exists():
        return False

    with output_file.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        headers = reader.fieldnames or CSV_FIELDNAMES

    if not rows:
        return False

    rows = rows[:-1]
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(_sanitize_rows_for_headers(rows, headers))
    return True


def export_summary_csv(output_file: Path, rows: list[dict[str, str | int | float]]) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "StudentID",
        "StudentName",
        "Grade",
        "TotalChecks",
        "ReliabilityPercent",
        "MissingAgendaCount",
        "IncompleteSubjectsCount",
    ]
    with output_file.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def load_insights_visibility(preferences_file: Path) -> dict[str, bool]:
    if not preferences_file.exists():
        return {}

    try:
        payload = json.loads(preferences_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}

    if not isinstance(payload, dict):
        return {}

    raw_visibility = payload.get("insights_visibility_by_class")
    if not isinstance(raw_visibility, dict):
        return {}

    visibility_by_class: dict[str, bool] = {}
    for class_key, visible in raw_visibility.items():
        if isinstance(class_key, str) and isinstance(visible, bool):
            visibility_by_class[class_key] = visible
    return visibility_by_class


def save_insights_visibility(preferences_file: Path, visibility_by_class: dict[str, bool]) -> None:
    preferences_file.parent.mkdir(parents=True, exist_ok=True)
    cleaned_visibility = {
        class_key: bool(visible)
        for class_key, visible in visibility_by_class.items()
        if isinstance(class_key, str)
    }
    payload = {"insights_visibility_by_class": cleaned_visibility}

    temp_file = preferences_file.with_name(f"{preferences_file.name}.tmp")
    with temp_file.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    temp_file.replace(preferences_file)


def _load_existing_headers(output_file: Path) -> list[str] | None:
    try:
        with output_file.open("r", newline="", encoding="utf-8") as handle:
            reader = csv.reader(handle)
            headers = next(reader, None)
    except OSError:
        return None

    if not headers:
        return None
    cleaned = [header.strip() for header in headers if header and header.strip()]
    return cleaned or None


def _sanitize_rows_for_headers(rows: list[dict[str, str]], headers: list[str]) -> list[dict[str, str]]:
    valid_keys = set(headers)
    return [{key: value for key, value in row.items() if key in valid_keys} for row in rows]


def _ensure_output_headers(output_file: Path) -> list[str]:
    existing_headers = _load_existing_headers(output_file)
    if not existing_headers:
        return CSV_FIELDNAMES

    missing_headers = [header for header in CSV_FIELDNAMES if header not in existing_headers]
    if not missing_headers:
        return existing_headers

    upgraded_headers = [*existing_headers, *missing_headers]
    with output_file.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    temp_file = output_file.with_name(f"{output_file.name}.tmp")
    with temp_file.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=upgraded_headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(_sanitize_rows_for_headers(rows, upgraded_headers))
    temp_file.replace(output_file)

    return upgraded_headers
