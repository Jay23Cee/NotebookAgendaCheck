import csv
from datetime import date
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from app.constants import APP_DISPLAY_NAME, DEFAULT_OUTPUT_FILE, DEFAULT_STUDENTS_FILE
from app.flags import ISSUE_FLAG_OPTIONS, NO_ISSUE_FLAG, compute_issue_flag
from app.scoring import AgendaInput, compute_agenda_score, compute_gradebook_score
from app.students import Student, filter_students, load_students


def append_row(output_file: Path, row: dict[str, str | int | float | bool]) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    file_exists = output_file.exists()
    fieldnames = [
        "StudentID",
        "StudentName",
        "Grade",
        "CheckMode",
        "Date",
        "Checker",
        "NotebookScore",
        "AgendaPresent",
        "EntryWritten",
        "AllSubjectsFilled",
        "Organized",
        "AgendaScore",
        "GradebookScore",
        "Flag",
        "Comments",
    ]
    with output_file.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


class NotebookAgendaGui(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_DISPLAY_NAME)
        self.geometry("760x560")
        self.minsize(760, 560)

        self.checker_var = tk.StringVar(value="")
        self.date_var = tk.StringVar(value=str(date.today()))
        self.grade_var = tk.StringVar(value="6")

        self.notebook_score_var = tk.StringVar(value="10")
        self.agenda_present_var = tk.BooleanVar(value=True)
        self.entry_written_var = tk.BooleanVar(value=True)
        self.all_subjects_var = tk.BooleanVar(value=True)
        self.organized_var = tk.BooleanVar(value=True)
        self.flag_var = tk.StringVar(value=NO_ISSUE_FLAG)
        self.auto_flag_var = tk.StringVar(value=NO_ISSUE_FLAG)

        self.agenda_score_var = tk.StringVar(value="10")
        self.gradebook_score_var = tk.StringVar(value="10.0")
        self.status_var = tk.StringVar(value="Maintenance-only fallback UI. Prefer `python -m app.nicegui_app`.")
        self.student_var = tk.StringVar(value="No roster loaded.")
        self.student_picker_var = tk.StringVar(value="")

        self.roster: list[Student] = []
        self.current_index = 0

        self.entry_written_check: ttk.Checkbutton | None = None
        self.all_subjects_check: ttk.Checkbutton | None = None
        self.organized_check: ttk.Checkbutton | None = None
        self.agenda_present_check: ttk.Checkbutton | None = None
        self.notebook_entry: ttk.Entry | None = None
        self.flag_box: ttk.Combobox | None = None
        self.save_button: ttk.Button | None = None
        self.reset_button: ttk.Button | None = None
        self.student_picker: ttk.Combobox | None = None

        self._build_ui()
        self._bind_events()
        self._set_scoring_enabled(False)
        self._update_scores()

    def _build_ui(self) -> None:
        container = ttk.Frame(self, padding=14)
        container.pack(fill="both", expand=True)

        config_frame = ttk.LabelFrame(container, text="Session Setup", padding=10)
        config_frame.pack(fill="x")

        ttk.Label(config_frame, text=f"Roster source: {DEFAULT_STUDENTS_FILE}").grid(
            row=0, column=0, columnspan=3, sticky="w", padx=4, pady=4
        )
        ttk.Label(config_frame, text=f"Output CSV: {DEFAULT_OUTPUT_FILE}").grid(
            row=1, column=0, columnspan=3, sticky="w", padx=4, pady=4
        )

        ttk.Label(config_frame, text="Checker").grid(row=2, column=0, sticky="w", padx=4, pady=4)
        ttk.Entry(config_frame, textvariable=self.checker_var, width=26).grid(
            row=2, column=1, sticky="w", padx=4, pady=4
        )
        ttk.Label(config_frame, text="Date (YYYY-MM-DD)").grid(row=2, column=1, sticky="e", padx=4, pady=4)
        ttk.Entry(config_frame, textvariable=self.date_var, width=14).grid(
            row=2, column=2, sticky="w", padx=4, pady=4
        )

        ttk.Label(config_frame, text="Grade").grid(row=3, column=0, sticky="w", padx=4, pady=4)
        grade_box = ttk.Combobox(config_frame, textvariable=self.grade_var, values=["6", "7", "8"], width=6, state="readonly")
        grade_box.grid(row=3, column=1, sticky="w", padx=4, pady=4)
        ttk.Button(config_frame, text="Load Roster", command=self._load_roster).grid(
            row=3, column=2, sticky="e", padx=4, pady=4
        )

        config_frame.columnconfigure(1, weight=1)

        student_frame = ttk.LabelFrame(container, text="Student", padding=10)
        student_frame.pack(fill="x", pady=(10, 0))
        ttk.Label(student_frame, textvariable=self.student_var, font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.student_picker = ttk.Combobox(
            student_frame,
            textvariable=self.student_picker_var,
            state="disabled",
            width=48,
        )
        self.student_picker.pack(anchor="w", pady=(6, 0))
        self.student_picker.bind("<<ComboboxSelected>>", self._on_student_selected)

        rubric_frame = ttk.LabelFrame(container, text=APP_DISPLAY_NAME, padding=10)
        rubric_frame.pack(fill="both", expand=True, pady=(10, 0))

        ttk.Label(rubric_frame, text="Notebook score (0-10)").grid(row=0, column=0, sticky="w", padx=4, pady=6)
        self.notebook_entry = ttk.Entry(rubric_frame, textvariable=self.notebook_score_var, width=10)
        self.notebook_entry.grid(row=0, column=1, sticky="w", padx=4, pady=6)

        ttk.Separator(rubric_frame, orient="horizontal").grid(row=1, column=0, columnspan=3, sticky="we", pady=(2, 8))

        self.agenda_present_check = ttk.Checkbutton(
            rubric_frame,
            text="Agenda present (2 pts)",
            variable=self.agenda_present_var,
            command=self._on_agenda_present_toggle,
        )
        self.agenda_present_check.grid(row=2, column=0, sticky="w", padx=4, pady=4)

        self.entry_written_check = ttk.Checkbutton(
            rubric_frame, text="Entry written today (3 pts)", variable=self.entry_written_var, command=self._update_scores
        )
        self.entry_written_check.grid(row=3, column=0, sticky="w", padx=28, pady=4)

        self.all_subjects_check = ttk.Checkbutton(
            rubric_frame,
            text="All subjects filled (3 pts)",
            variable=self.all_subjects_var,
            command=self._update_scores,
        )
        self.all_subjects_check.grid(row=4, column=0, sticky="w", padx=28, pady=4)

        self.organized_check = ttk.Checkbutton(
            rubric_frame, text="Legible/organized (2 pts)", variable=self.organized_var, command=self._update_scores
        )
        self.organized_check.grid(row=5, column=0, sticky="w", padx=28, pady=4)

        ttk.Label(rubric_frame, text="Flag (manual, ignored on save)").grid(row=6, column=0, sticky="w", padx=4, pady=(10, 4))
        self.flag_box = ttk.Combobox(
            rubric_frame,
            textvariable=self.flag_var,
            values=ISSUE_FLAG_OPTIONS,
            state="readonly",
            width=28,
        )
        self.flag_box.grid(row=6, column=1, sticky="w", padx=4, pady=(10, 4))
        ttk.Label(
            rubric_frame,
            text="Auto-computed flag is always saved. Manual selection is ignored.",
        ).grid(row=7, column=0, columnspan=3, sticky="w", padx=4, pady=(0, 4))
        ttk.Label(rubric_frame, text="Auto flag now:", font=("Segoe UI", 9, "bold")).grid(
            row=8,
            column=0,
            sticky="w",
            padx=4,
            pady=(0, 2),
        )
        ttk.Label(rubric_frame, textvariable=self.auto_flag_var).grid(
            row=8,
            column=1,
            columnspan=2,
            sticky="w",
            padx=4,
            pady=(0, 2),
        )

        score_frame = ttk.Frame(rubric_frame)
        score_frame.grid(row=9, column=0, columnspan=3, sticky="we", padx=4, pady=(12, 4))
        ttk.Label(score_frame, text="Agenda Score:", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(score_frame, textvariable=self.agenda_score_var, width=8).grid(row=0, column=1, sticky="w")
        ttk.Label(score_frame, text="Gradebook Score (/10):", font=("Segoe UI", 10, "bold")).grid(row=0, column=2, sticky="w", padx=(20, 0))
        ttk.Label(score_frame, textvariable=self.gradebook_score_var, width=8).grid(row=0, column=3, sticky="w")

        actions = ttk.Frame(container)
        actions.pack(fill="x", pady=(10, 0))
        self.save_button = ttk.Button(actions, text="Save + Next", command=self._save_and_next)
        self.save_button.pack(side="left")
        self.reset_button = ttk.Button(actions, text="Reset Inputs", command=self._reset_inputs)
        self.reset_button.pack(side="left", padx=(8, 0))
        ttk.Label(actions, textvariable=self.status_var).pack(side="right")

    def _bind_events(self) -> None:
        self.notebook_score_var.trace_add("write", lambda *_: self._update_scores())
        self.agenda_present_var.trace_add("write", lambda *_: self._update_scores())
        self.entry_written_var.trace_add("write", lambda *_: self._update_scores())
        self.all_subjects_var.trace_add("write", lambda *_: self._update_scores())
        self.organized_var.trace_add("write", lambda *_: self._update_scores())

    def _set_scoring_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        widgets = [
            self.notebook_entry,
            self.agenda_present_check,
            self.entry_written_check,
            self.all_subjects_check,
            self.organized_check,
            self.flag_box,
            self.save_button,
            self.reset_button,
        ]
        for widget in widgets:
            if widget is None:
                continue
            widget.configure(state=state)
        if self.student_picker is not None:
            self.student_picker.configure(state="readonly" if enabled else "disabled")
        if enabled:
            self._on_agenda_present_toggle()

    def _load_roster(self) -> None:
        checker = self.checker_var.get().strip()
        if not checker:
            messagebox.showerror("Missing checker", "Enter checker name before loading roster.")
            return

        try:
            grade = int(self.grade_var.get())
        except ValueError:
            messagebox.showerror("Invalid grade", "Grade must be a number.")
            return

        if not DEFAULT_STUDENTS_FILE.exists():
            messagebox.showerror("Missing students file", f"Students file not found: {DEFAULT_STUDENTS_FILE}")
            return

        try:
            students = load_students(DEFAULT_STUDENTS_FILE)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Roster error", str(exc))
            return

        roster = filter_students(students, grade=grade)
        if not roster:
            messagebox.showwarning("No students", f"No students found for grade {grade}.")
            return

        self.roster = roster
        self.current_index = 0
        self._set_scoring_enabled(True)
        self._sync_student_picker()
        self._reset_inputs()
        self._render_student()
        self.status_var.set(f"Loaded {len(roster)} students for Grade {grade}.")

    def _sync_student_picker(self) -> None:
        if self.student_picker is None:
            return
        values = [f"{student.last_name}, {student.first_name}" for student in self.roster]
        self.student_picker["values"] = values
        if values:
            self.student_picker.current(self.current_index)
            self.student_picker_var.set(values[self.current_index])
        else:
            self.student_picker_var.set("")

    def _on_student_selected(self, _event: tk.Event) -> None:
        if not self.roster or self.student_picker is None:
            return
        selected_index = self.student_picker.current()
        if selected_index < 0 or selected_index >= len(self.roster):
            return
        self.current_index = selected_index
        self._reset_inputs()
        self._render_student()
        self.status_var.set(f"Ready for {self.roster[self.current_index].full_name}.")

    def _render_student(self) -> None:
        if not self.roster:
            self.student_var.set("No roster loaded.")
            self.student_picker_var.set("")
            return
        student = self.roster[self.current_index]
        self.student_var.set(
            f"{self.current_index + 1}/{len(self.roster)}  {student.last_name}, {student.first_name} ({student.student_id})"
        )
        if self.student_picker is not None:
            self.student_picker.current(self.current_index)

    def _on_agenda_present_toggle(self) -> None:
        if self.entry_written_check is None or self.all_subjects_check is None or self.organized_check is None:
            return
        if self.agenda_present_var.get():
            self.entry_written_check.configure(state="normal")
            self.all_subjects_check.configure(state="normal")
            self.organized_check.configure(state="normal")
        else:
            self.entry_written_var.set(False)
            self.all_subjects_var.set(False)
            self.organized_var.set(False)
            self.entry_written_check.configure(state="disabled")
            self.all_subjects_check.configure(state="disabled")
            self.organized_check.configure(state="disabled")
        self._update_scores()

    def _parse_notebook_score(self) -> float:
        raw = self.notebook_score_var.get().strip()
        try:
            score = float(raw)
        except ValueError as exc:
            raise ValueError("Notebook score must be a number from 0 to 10.") from exc
        if score < 0 or score > 10:
            raise ValueError("Notebook score must be between 0 and 10.")
        return round(score, 2)

    def _agenda_input(self) -> AgendaInput:
        if not self.agenda_present_var.get():
            return AgendaInput(agenda_present=False)
        return AgendaInput(
            agenda_present=True,
            entry_written=self.entry_written_var.get(),
            all_subjects_filled=self.all_subjects_var.get(),
            organized=self.organized_var.get(),
        )

    def _update_scores(self) -> None:
        agenda_result = compute_agenda_score(self._agenda_input())
        try:
            notebook_score = self._parse_notebook_score()
        except ValueError:
            notebook_score = 0.0
            self.gradebook_score_var.set("--")
        else:
            gradebook = compute_gradebook_score(notebook_score, agenda_result.agenda_score)
            self.gradebook_score_var.set(str(gradebook))

        self.auto_flag_var.set(
            compute_issue_flag(
                notebook_score=notebook_score,
                agenda_present=agenda_result.agenda_present,
                entry_written=agenda_result.entry_written,
                all_subjects_filled=agenda_result.all_subjects_filled,
                organized=agenda_result.organized,
            )
        )
        self.agenda_score_var.set(str(agenda_result.agenda_score))

    def _reset_inputs(self) -> None:
        self.notebook_score_var.set("10")
        self.agenda_present_var.set(True)
        self.entry_written_var.set(True)
        self.all_subjects_var.set(True)
        self.organized_var.set(True)
        self.flag_var.set(NO_ISSUE_FLAG)
        self._on_agenda_present_toggle()
        self._update_scores()

    def _save_and_next(self) -> None:
        if not self.roster:
            messagebox.showerror("No roster", "Load a roster first.")
            return
        try:
            notebook_score = self._parse_notebook_score()
        except ValueError as exc:
            messagebox.showerror("Invalid notebook score", str(exc))
            return

        agenda_result = compute_agenda_score(self._agenda_input())
        gradebook_score = compute_gradebook_score(notebook_score, agenda_result.agenda_score)
        student = self.roster[self.current_index]
        manual_flag = (self.flag_var.get() or "").strip() or NO_ISSUE_FLAG
        auto_flag = compute_issue_flag(
            notebook_score=notebook_score,
            agenda_present=agenda_result.agenda_present,
            entry_written=agenda_result.entry_written,
            all_subjects_filled=agenda_result.all_subjects_filled,
            organized=agenda_result.organized,
        )
        if manual_flag != auto_flag:
            messagebox.showwarning(
                "Flag ignored",
                f"Manual flag '{manual_flag}' was ignored.\nSaved auto-computed flag '{auto_flag}'.",
            )

        row = {
            "StudentID": student.student_id,
            "StudentName": student.full_name,
            "Grade": student.grade,
            "CheckMode": "both",
            "Date": self.date_var.get().strip(),
            "Checker": self.checker_var.get().strip(),
            "NotebookScore": notebook_score,
            "AgendaPresent": agenda_result.agenda_present,
            "EntryWritten": agenda_result.entry_written,
            "AllSubjectsFilled": agenda_result.all_subjects_filled,
            "Organized": agenda_result.organized,
            "AgendaScore": agenda_result.agenda_score,
            "GradebookScore": gradebook_score,
            "Flag": auto_flag,
            "Comments": "",
        }

        try:
            append_row(DEFAULT_OUTPUT_FILE, row)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Save error", str(exc))
            return

        if self.current_index + 1 >= len(self.roster):
            self.status_var.set(f"Saved final student. Results at {DEFAULT_OUTPUT_FILE}")
            messagebox.showinfo("Done", f"All students saved.\n\nOutput: {DEFAULT_OUTPUT_FILE}")
            self._set_scoring_enabled(False)
            return

        self.current_index += 1
        self._render_student()
        self._reset_inputs()
        if manual_flag != auto_flag:
            self.status_var.set(f"Saved {student.full_name}. Manual flag ignored; saved '{auto_flag}'.")
        else:
            self.status_var.set(f"Saved {student.full_name}.")


def main() -> None:
    print(
        "Notice: app.gui is maintenance-only and deprecated. "
        "Use `python -m app.nicegui_app` for the supported workflow."
    )
    app = NotebookAgendaGui()
    app.mainloop()


if __name__ == "__main__":
    main()
