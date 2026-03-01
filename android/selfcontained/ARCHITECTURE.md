# Architecture: Self-Contained Android Runtime

## Goal

Run NotebookAgendaCheck fully offline inside one Android app package without external Termux dependency.

## Planned Runtime Flow

1. Android app launches.
2. `BackendService` starts in-process local backend bootstrap.
3. `PythonBootstrap` initializes embedded Python (Chaquopy target).
4. Backend binds to loopback (`127.0.0.1`) with app-managed port.
5. WebView loads local loopback URL and checks `/_nach/health`.

## Storage Mapping

Desktop-relative paths migrate into Android app-private storage:

- `records/notebook_agenda_checks.csv` -> `<app-files>/records/notebook_agenda_checks.csv`
- `records/na_check_error_log.csv` -> `<app-files>/records/na_check_error_log.csv`
- `records/roster/current_roster.csv` -> `<app-files>/records/roster/current_roster.csv`
- `records/ui_preferences.json` -> `<app-files>/records/ui_preferences.json`

## Service / UI Boundaries

- `MainActivity`: UI, state rendering, and WebView lifecycle.
- `BackendService`: process-lifetime backend service management.
- `PythonBootstrap`: Python runtime initialization and module entrypoint call.

## Networking

- Loopback only (`127.0.0.1`).
- No external host dependency.
- WebView allows only local origin routes.

## Migration Checklist (Termux -> Self-Contained)

1. Parameterize backend file roots so app-private Android paths can be injected.
2. Add startup adapter to run NiceGUI app from embedded Python entrypoint.
3. Replace Termux startup scripts with native `BackendService` lifecycle.
4. Add in-app backup/export UX for operator data portability.
5. Re-run grading regression suite against embedded runtime behavior.
