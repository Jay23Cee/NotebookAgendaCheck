<<<<<<< HEAD
# Notebook & Agenda Check

Local tool for **Notebook + Agenda checks** by **grade**.

## Safety

- Student roster is read automatically from `data/mock_students.xlsx`.
- The app **does not push or sync data to Google**.
- The app **does not write any Excel files into a save folder**.
- Check results are auto-saved locally to `records/notebook_agenda_checks.csv`.

## Rubric

Agenda (`/10`):

- `agenda_present`: `4`
- `agenda_filled_today`: `Complete=4`, `Partial=2`, `Blank=0`
- `agenda_readable`: `2`

Notebook (`/10`):

- `notebook_present`: `4`
- `notebook_work_today`: `Complete=4`, `Partial=2`, `Missing=0`
- `notebook_organized`: `2`

Negative comment-tag deductions are applied and capped at `5.0` points:

- `Unreadable`: `-1.0`
- `Difficult_To_Read`: `-0.5`
- `Disorganized`: `-0.5`
- `Missing_Date`: `-0.25`
- `Incomplete_Work`: `-5.0`
- `Missing_Components`: `-5.0`

### Check Modes

- `both`: score both notebook and agenda
- `notebook_only`: score notebook only
- `agenda_only`: score agenda only

### Gradebook Score

- `both`:
  - `internal_total = max(0, agenda_score + notebook_score - capped_deduction)` (`/20`)
  - `gradebook_score = round(internal_total / 2, 2)` (`/10`)
- `notebook_only`:
  - `gradebook_score = round(max(0, notebook_score - capped_deduction), 2)` (`/10`)
  - `internal_total = round(gradebook_score * 2, 2)` (compatibility)
- `agenda_only`:
  - `gradebook_score = round(max(0, agenda_score - capped_deduction), 2)` (`/10`)
  - `internal_total = round(gradebook_score * 2, 2)` (compatibility)

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run Tests

```powershell
pytest -q
```

## Generate Mock Excel Roster

```powershell
python scripts/generate_mock_excel.py
```

## Supported Interfaces

- Supported and actively maintained: `app.nicegui_app`
- Temporary fallback: `app.flet_app`
- Maintenance-only deprecated fallbacks: `app.cli`, `app.gui`

## Run NiceGUI Dashboard (Supported)

```powershell
python -m app.nicegui_app
```

Developer note: UI styling is in `app/nicegui_app/styles/dashboard.css`; layout classes are applied in components.

In the NiceGUI app:

- Desktop baseline is optimized for `1366x768` minimum window size.
- Compact top header is split into:
  - Left: `Grade`
  - Center: `Student` selector + `Student X of Y`
  - Right: `User` mode + conditional student checker + `Date`
- After grade is loaded, a check-mode chooser appears:
  - `Notebook check only`
  - `Notebook + Agenda check`
  - `Agenda check only`
- Once selected, mode collapses into a compact row and locks after first save.
- Main body uses cards:
  - `Agenda` (hidden when notebook-only)
  - `Notebook` (hidden when agenda-only)
  - `Status + Tags`
- History panel includes:
  - `Start date` / `End date` filters
  - `With comments` / `Without comments` toggles
  - Last 50 filtered rows with mode-aware columns
- Sticky footer command bar always shows:
  - `Agenda /10` (or `--` when inactive)
  - `Notebook /10` (or `--` when inactive)
  - `Internal /20`
  - `Gradebook /10` (largest emphasis)
- Actions:
  - `Save + Next`
  - `Undo Last`
- Keyboard shortcuts:
  - `Enter = Save + Next`
  - `U = Undo Last`
- Lock overlay appears until grade/roster context is available.

Roster source and output CSV:

- Roster source: `data/mock_students.xlsx`
- Output CSV: `records/notebook_agenda_checks.csv`

## UI QA Checklist

Verify at `1366x768`:

- No critical layout break in default dashboard view.
- Sticky topbar and sticky footer remain visible.
- Student strip appears under the topbar.
- Cards render as 3-column in `both` mode and 2-column in single modes.
- History panel renders below cards and table remains readable.

Verify at `1024px` width:

- Cards stack to a single column.
- Footer summary/actions remain visible and usable.
- Chip rows and history filters wrap cleanly.
- Keyboard focus states are visible on fields, chips, and buttons.

## Application Flowchart

For architecture and runtime flow, see `docs/flowchart.md`.

## Output Fields

Each saved row includes:

- `StudentID`
- `StudentName`
- `Grade`
- `CheckMode` (`both`, `notebook_only`, `agenda_only`)
- `Date`
- `Checker`
- `NotebookScore`
- `AgendaPresent`
- `EntryWritten`
- `AllSubjectsFilled`
- `Organized`
- `AgendaScore`
- `GradebookScore` (`/10`)
- `AgendaFilledToday`
- `AgendaReadable`
- `NotebookPresentDetail`
- `NotebookWorkToday`
- `NotebookOrganized`
- `CommentTags`
- `CommentDeduction`
- `InternalScore` (`/20`)
- `ScoreModel` (`internal20_gradebook10_v1` for new rows)
- `Flag` (auto-computed compatibility label)
- `Comments`

Notes:

- Existing historical rows are not rewritten in place.
- Existing CSV files missing newer rubric columns are auto-upgraded on next save.
- Legacy rows with `Period` still load for backward compatibility.
- For legacy rows missing `ScoreModel`, history infers display scale:
  - `GradebookScore > 10` is treated as legacy internal `/20` and shown as `/10` by dividing by 2.
  - `GradebookScore <= 10` is treated as legacy `/10` and internal is inferred as `x2`.
=======
# NotebookAgendaCheck
>>>>>>> cdf865dda87f6eca6cfc11edb01d4d0ac163e8c8
