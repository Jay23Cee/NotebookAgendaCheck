# Phase 2 TODO

## Android Runtime

- [ ] Add complete Android app module (`settings.gradle.kts`, root `build.gradle.kts`, manifest, resources).
- [ ] Implement `BackendService` foreground/background behavior and lifecycle telemetry.
- [ ] Implement WebView startup synchronization against health endpoint.

## Embedded Python (Chaquopy)

- [ ] Add Chaquopy plugin and lock supported Python version.
- [ ] Package `notebookagendacheck` and dependencies (`nicegui`, `openpyxl`) in app build.
- [ ] Define Python entrypoint callable for Android bootstrap.
- [ ] Add robust startup failure reporting from Python layer to Android UI.

## Data Paths

- [ ] Inject app-private data directories into Python configuration.
- [ ] Validate atomic writes and corruption recovery on Android filesystem.
- [ ] Implement export/import UX for backup and restore.

## QA and Release

- [ ] Device test matrix for Android versions and tablet form factors.
- [ ] Startup performance target and watchdog behavior.
- [ ] Play pre-launch report hardening.
