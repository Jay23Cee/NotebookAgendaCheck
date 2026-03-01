# Notebook & Agenda Check

Local tool for **Notebook + Agenda checks** by **grade**.

## Safety

- Student roster is read automatically from `data/mock_students.xlsx`.
- Dashboard roster must include a `Subject` column with `Math`/`Science` values.
- The app **does not push or sync data to Google**.
- The app **does not write any Excel files into a save folder**.
- Check results are auto-saved locally to `records/notebook_agenda_checks.csv`.
- Runtime errors are logged to `records/na_check_error_log.csv`.
- Corrupted CSV files are quarantined under `records/quarantine/` before clean-file recreation.

## Rubric

Agenda (`/10`):

- `agenda_present`: `4`
- `agenda_filled_today`: `Complete=4`, `Partial=2`, `Blank=0`
- `agenda_readable`: `2`

Notebook (`/10`):

- `present_prepared`: `Present=1`, `Not present=0`
- `date`: `Correct=1`, `Unclear=0.5`, `Missing=0`
- `title`: `Accurate=1`, `Vague=0.5`, `Missing=0`
- `academic_notes`: `Detailed=3`, `Basic=1.5`, `Minimal=0`
- `organization`: `Structured=2`, `Inconsistent=1`, `Disorganized=0`
- `legibility_effort`: `Neat=2`, `Readable=1`, `Difficult=0`

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
# Recommended: keep virtualenv outside the repo to reduce workspace size
python -m venv ..\NotebookAgendaCheck-venv
..\NotebookAgendaCheck-venv\Scripts\Activate.ps1
pip install -e .[dev]
```

Runtime-only install:

```powershell
pip install -r requirements.txt
```

## Run Tests

```powershell
pytest -q
```

## Reliability Hardening

- Save/undo operations use transactional CSV writes (`temp file -> flush -> fsync -> atomic replace`).
- Error logging uses a resilient sink chain:
  - Primary: `records/na_check_error_log.csv`
  - Fallback: `stderr`
  - Emergency: in-memory ring buffer
- Duplicate identical errors are toast-suppressed in a 5-second window with counter text (`... (xN)`).
- Error log columns:
  - `TimestampUtc`, `SessionID`, `Severity`, `Source`, `Operation`, `Message`, `ExceptionType`, `ExceptionMessage`, `ContextJson`, `Traceback`

Benchmark reliability overhead:

```powershell
python scripts/benchmark_na_reliability.py
```

## Generate Mock Excel Roster

```powershell
python scripts/generate_mock_excel.py
```

## Supported Interfaces

- Supported and actively maintained: `app.nicegui_app`

## Run NiceGUI Dashboard (Supported)

```powershell
python -m app.nicegui_app
```

## Samsung Tab S10 Lite Appliance Deployment (Termux + Debian)

This deployment mode is intended for stable day-to-day tablet operation:

- deterministic runtime configuration
- local-only network exposure by default
- persistent server session via `tmux`
- mirrored backups to shared Android storage

### Runtime env configuration

`app.nicegui_app.main` supports these environment variables:

- `NACH_HOST` (default: `127.0.0.1`)
- `NACH_PORT` (default: `8080`)
- `NACH_SHOW` (default: `false`)
- `NACH_RELOAD` (default: `false`)

Launch command remains:

```bash
python -m app.nicegui_app
```

### Phase 0: Preflight checks in Termux

```bash
uname -m
df -h /data/data/com.termux/files
```

Recommended:

- architecture: `aarch64`
- free space: at least `2G`

### Phase 1: Install Termux base tools

```bash
pkg update && pkg upgrade -y
pkg install -y proot-distro git
termux-setup-storage
```

### Phase 2: Install Debian userspace

```bash
proot-distro install debian
proot-distro login debian
```

### Phase 3: Install Debian runtime dependencies

Inside Debian:

```bash
apt update
apt install -y python3 python3-venv python3-pip git tmux
```

### Phase 4: Install project in Debian

Inside Debian:

```bash
git clone <repo-url> ~/NotebookAgendaCheck
cd ~/NotebookAgendaCheck
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -e ".[dev]"
```

Fallback install:

```bash
pip install -r requirements.txt
```

Build fallback if dependency compilation fails:

```bash
apt install -y build-essential python3-dev pkg-config libffi-dev libssl-dev
apt install -y rustc cargo
```

### Phase 5: Android operator scripts

Scripts are provided in `scripts/android/`:

- `start_na_app.sh`
- `stop_na_app.sh`
- `status_na_app.sh`
- `backup_records.sh`
- `restore_records.sh`

Make scripts executable:

```bash
chmod +x scripts/android/*.sh
```

#### Start service

Recommended from Termux host (for wake lock support):

```bash
scripts/android/start_na_app.sh
```

If your project path differs from the default `/root/NotebookAgendaCheck`, set `PROJECT_DIR` explicitly:

```bash
PROJECT_DIR=/path/to/NotebookAgendaCheck scripts/android/start_na_app.sh
```

You can also run the scripts inside Debian directly; they will skip `proot-distro` wrapping and still manage `tmux`/app state.

Behavior:

- acquires wake lock if available
- logs into Debian
- starts or reuses `tmux` session `na_app`
- runs `python -m app.nicegui_app` with default:
  - `NACH_HOST=127.0.0.1`
  - `NACH_PORT=8080`
  - `NACH_SHOW=false`
  - `NACH_RELOAD=false`

Open app on the tablet:

```text
http://127.0.0.1:8080
```

#### Check service status

```bash
scripts/android/status_na_app.sh
```

Expected healthy output:

- `tmux session: up (na_app)`
- `port listener: up (:8080)`

#### Stop service

```bash
scripts/android/stop_na_app.sh
```

Behavior:

- kills `na_app` session if present
- releases wake lock if available

### LAN mode (optional)

Default mode is local-only (`127.0.0.1`).  
For LAN access on trusted Wi-Fi only:

```bash
NACH_HOST=0.0.0.0 scripts/android/start_na_app.sh
```

Security warning:

- `0.0.0.0` exposes the app to your local network.
- only use on trusted/private networks.

### Phase 6: Data durability and backups

Primary files remain in the project:

- `records/notebook_agenda_checks.csv`
- `records/na_check_error_log.csv`
- `records/quarantine/`

Mirror backup command:

```bash
scripts/android/backup_records.sh
```

Backup destination default:

```text
/sdcard/Documents/App_Backups/NotebookAgendaCheck
```

Each run creates:

- timestamped folder (UTC)
- `latest/` mirror copy

Recommended cadence:

- after each grading session
- daily during active periods

Restore from latest backup:

```bash
scripts/android/restore_records.sh
```

Restore from a specific timestamp folder:

```bash
scripts/android/restore_records.sh 20260301T120000Z
```

### Phase 7: Operational diagnostics

Service status:

```bash
scripts/android/status_na_app.sh
```

Inspect listener inside Debian:

```bash
proot-distro login debian -- ss -ltnp | grep 8080
```

Inspect session logs:

```bash
proot-distro login debian -- tmux attach -t na_app
```

### Phase 8: Reproducible rebuild

After a known-good setup inside Debian:

```bash
pip freeze > requirements.lock.txt
```

Rebuild from lockfile:

```bash
pip install -r requirements.lock.txt
```

Developer notes:

- Global theme styles are in `app/nicegui_app/styles/dashboard.css`.
- Dashboard-specific styles are in `app/nicegui_app/styles/na_check_dashboard.css`.
- Dashboard helper logic is in `app/nicegui_app/pages/dashboard_core/`.

In the NiceGUI app:

- Desktop baseline is optimized for `1366x768` minimum window size.
- Top bar includes `Grade`, `Class` (Math/Science toggle), `Students` multi-select, `Date`, and `Sticky last choices`.
- Student selection is capped at 3 cards at once and highlights saved vs not-checked students.
- Status/action row shows:
  - `Selected`
  - `Remaining`
  - `Unsaved changes`
  - actions: `Save`, `Undo`, `Only Remaining`
- Main body renders one card per selected student with:
  - Agenda controls
  - Notebook controls
  - Status/tags/comments panel
  - per-card actions: `Save`, `Next Not Checked`
- Keyboard shortcut:
  - `Ctrl+Z = Undo last save transaction`

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
