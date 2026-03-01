# Application Flowchart

This document maps the active NiceGUI runtime flow to `na_check_dashboard`.

## Overview

### Diagram A - End-to-End Runtime

```mermaid
flowchart TD
    A["python -m app.nicegui_app\nmain.run()"] --> B["build_na_check_dashboard()"]
    B --> C["NACheckDashboard.build()"]
    C --> D["_initialize_selectors()"]
    D --> E["load roster + subject filters + student options"]
    E --> F["_render_batch_cards()"]

    F --> G["Card edits\nagenda/notebook/tags/comments"]
    G --> H["score_form() + apply_auto_rules()"]

    H --> I["Save\n_save_student() / _save_selected_students()"]
    I --> J["_save_students()"]
    J --> K["CsvStore.append_rows()"]
    K --> L["saved_keys + transactions + card effects"]

    M["Undo\n_undo_last_saved()"] --> N["CsvStore.undo_last_saved_rows()"]
    N --> O["restore draft state + card effects"]

    P["Only Remaining"] --> Q["_replace_saved_selected_cards()"]
    Q --> R["_find_next_remaining_candidate()"]
```

## UI State

### Diagram B - Dashboard States

```mermaid
stateDiagram-v2
    [*] --> Boot
    Boot --> Ready : roster loaded
    Boot --> StartupError : roster load fails

    Ready --> Editing : select grade/class/students
    Editing --> Saving : save action
    Saving --> Editing : write success
    Saving --> WriteFailed : write exception

    Editing --> Undoing : undo action
    Undoing --> Editing : undo success
    Undoing --> WriteFailed : undo exception

    WriteFailed --> Editing : next successful action
```

## Persistence + Compatibility

### Diagram C - Save Pipeline

```mermaid
flowchart TD
    A["Draft form state"] --> B["apply_auto_rules()"]
    B --> C["score_form()"]
    C --> D["row payload (/10 gradebook + /20 internal)"]
    D --> E["CsvStore.append_rows()"]
    E --> F["records/notebook_agenda_checks.csv"]
```

Notes:

- `CheckMode` is written as `both`.
- Score model is written as `internal20_gradebook10_v1`.
- Legacy `Period` compatibility is retained in output and history handling.
