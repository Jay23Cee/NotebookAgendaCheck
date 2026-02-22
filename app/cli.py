import argparse
from datetime import date

from app.constants import APP_DISPLAY_NAME, DEFAULT_OUTPUT_FILE, DEFAULT_STUDENTS_FILE
from app.flags import ISSUE_FLAG_OPTIONS, NO_ISSUE_FLAG, compute_issue_flag
from app.models import CheckRecord
from app.scoring import AgendaInput, compute_agenda_score, compute_gradebook_score
from app.storage import append_record
from app.students import filter_students, load_students


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=f"{APP_DISPLAY_NAME} by grade")
    parser.add_argument("--grade", type=int, choices=[6, 7, 8], required=True)
    parser.add_argument("--checker", type=str, required=True)
    parser.add_argument("--date", type=str, default=str(date.today()))
    parser.add_argument("--limit", type=int, default=0, help="Optional limit for quick testing.")
    return parser.parse_args()


def prompt_yes_no(message: str) -> bool:
    while True:
        value = input(f"{message} [y/n]: ").strip().lower()
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        print("Enter y or n.")


def prompt_notebook_score() -> float:
    while True:
        raw = input("Notebook score (0-10): ").strip()
        try:
            score = float(raw)
        except ValueError:
            print("Enter a number from 0 to 10.")
            continue
        if 0 <= score <= 10:
            return round(score, 2)
        print("Score must be between 0 and 10.")


def prompt_flag() -> str:
    print("Manual Flag options (ignored on save):")
    for idx, flag in enumerate(ISSUE_FLAG_OPTIONS, start=1):
        print(f"  {idx}. {flag}")
    while True:
        raw = input("Select manual flag number: ").strip()
        try:
            selected = int(raw)
        except ValueError:
            print("Enter one number from the list.")
            continue
        if 1 <= selected <= len(ISSUE_FLAG_OPTIONS):
            return ISSUE_FLAG_OPTIONS[selected - 1]
        print("Enter one number from the list.")


def main() -> None:
    print(
        "Notice: app.cli is maintenance-only and deprecated. "
        "Use `python -m app.nicegui_app` for the supported workflow."
    )
    args = parse_args()
    students = load_students(DEFAULT_STUDENTS_FILE)
    roster = filter_students(students, args.grade)
    if args.limit > 0:
        roster = roster[: args.limit]

    if not roster:
        print(f"No students found for grade {args.grade}.")
        return

    print(f"Checking {len(roster)} students | Grade {args.grade}")
    print("Hard rule active: missing agenda = 0, remaining agenda checks auto-false.")
    print("Flag is auto-computed on save. Manual flag selections are ignored.")

    for idx, student in enumerate(roster, start=1):
        print("-" * 54)
        print(f"{idx}/{len(roster)} {student.full_name} ({student.student_id})")

        notebook_score = prompt_notebook_score()
        agenda_present = prompt_yes_no("Agenda present")

        if not agenda_present:
            agenda_input = AgendaInput(agenda_present=False)
        else:
            agenda_input = AgendaInput(
                agenda_present=True,
                entry_written=prompt_yes_no("Entry written today"),
                all_subjects_filled=prompt_yes_no("All subjects filled"),
                organized=prompt_yes_no("Legible/organized"),
            )

        agenda_result = compute_agenda_score(agenda_input)
        if agenda_result.auto_zero_reason:
            print(f"Auto rule: {agenda_result.auto_zero_reason}. Agenda score forced to 0.")

        computed_flag = compute_issue_flag(
            notebook_score=notebook_score,
            agenda_present=agenda_result.agenda_present,
            entry_written=agenda_result.entry_written,
            all_subjects_filled=agenda_result.all_subjects_filled,
            organized=agenda_result.organized,
        )
        print(f"Auto-computed flag: {computed_flag}")
        manual_flag = prompt_flag()
        if manual_flag != computed_flag:
            print(f"Notice: manual flag '{manual_flag}' ignored; saving '{computed_flag}'.")
        gradebook_score = compute_gradebook_score(notebook_score, agenda_result.agenda_score)

        record = CheckRecord.from_student(
            student=student,
            check_date=args.date,
            checker=args.checker,
            notebook_score=notebook_score,
            agenda_present=agenda_result.agenda_present,
            entry_written=agenda_result.entry_written,
            all_subjects_filled=agenda_result.all_subjects_filled,
            organized=agenda_result.organized,
            agenda_score=agenda_result.agenda_score,
            gradebook_score=gradebook_score,
            flag=computed_flag,
            check_mode="both",
        )
        append_record(record, DEFAULT_OUTPUT_FILE)

        print(
            f"Saved: Notebook {notebook_score}/10 | Agenda {agenda_result.agenda_score}/10 | "
            f"Gradebook {gradebook_score}/10 | Flag {computed_flag}"
        )
        if computed_flag == NO_ISSUE_FLAG:
            print("No issue detected (saved as 'None').")

    print("-" * 54)
    print(f"Done. Results saved to {DEFAULT_OUTPUT_FILE}")


if __name__ == "__main__":
    main()
