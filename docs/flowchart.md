# Application Flowchart

This document maps the active NiceGUI runtime flow to code-level methods and supporting persistence/scoring modules.

## Overview

### Diagram A - End-to-End Overview

```mermaid
flowchart TD
    A["python -m app.nicegui_app\nmain.run()"] --> B["check_page.build()\nCreate shell + header + cards + footer"]
    B --> C["NAWorkflowController\nInitialize ViewState + computed scores"]

    C --> D["Header events\nset_grade / set_check_mode / set_checker_mode / set_checker_student / set_date"]
    D --> E["_reload_class_context()\nLoad roster + checker options"]

    E -->|success| F["session.locked=False\nStudent roster active"]
    E -->|failure| G["session.locked=True\nLock overlay + status error"]

    F --> H["Card events\nset_* form controls + toggle tags\n(mode-aware controls)"]
    H --> I["ScoringService.compute()\nAgenda + Notebook + deductions + flag"]

    I --> J["Save + Next\nworkflow_controller.save_next()"]
    J --> K["CheckRecord.from_student()"]
    K --> L["append_record()\nCSV append + header auto-upgrade"]
    L --> M["Advance student index + reset form"]

    I --> N["Undo Last\nworkflow_controller.undo_last()"]
    N --> O["remove_last_record()"]
    O --> P["Restore prior student/form state"]

    Q["Keyboard events\nEnter / U"] --> R["KeyboardShortcutService.handle_key()"]
    R --> J
    R --> N
```

## UI State Machine

### Diagram B - UI Lifecycle and State Transitions

```mermaid
stateDiagram-v2
    [*] --> Locked : initial page build

    Locked --> LoadingRoster : set_grade
    LoadingRoster --> Active : _reload_class_context success
    LoadingRoster --> Locked : _reload_class_context failure

    Active --> Active : form edits -> recompute scores
    Active --> Active : save_next() for non-final student
    Active --> Complete : current_index >= len(roster)
    Active --> Active : undo_last() success

    Complete --> Active : undo_last() success
    Complete --> LoadingRoster : change grade

    note right of Locked
      Lock overlay displays:
      "Select Grade to begin"
    end note
```

## Scoring + Persistence

### Diagram C - Scoring, Save, and Undo Pipeline

```mermaid
flowchart TD
    A["Form controls + tag chips"] --> B["ScoringService.normalize_form()"]
    B --> C["compute_agenda_score_v2()"]
    B --> D["compute_notebook_score_v2()"]
    B --> E["compute_comment_deduction()"]
    C --> F["compute_mode_totals(check_mode)"]
    D --> F
    E --> F
    F --> G["both: internal/2\nsingle-mode: active /10"]
    G --> H["compute_issue_flag()"]

    H --> I["workflow_controller.save_next()"]
    I --> J["CheckRecord.from_student(...score_model=v1)"]
    J --> K["append_record()"]
    K --> L["_ensure_output_headers()"]

    M["workflow_controller.undo_last()"] --> N["remove_last_record()"]
    N --> O["_load_record_into_form()"]
```

### Diagram D - Data Model and CSV Compatibility

```mermaid
flowchart LR
    A["CheckRecord.to_csv_row()"] --> B["records/notebook_agenda_checks.csv"]
    B --> C["load_records_with_warnings()"]
    C --> D["CheckRecord.from_csv_row()"]

    D --> E["ScoreModel v1 + CheckMode\nuse InternalScore + GradebookScore"]
    D --> F["Legacy row without ScoreModel"]
    F --> G["GradebookScore > 10 => legacy /20"]
    F --> H["GradebookScore <= 10 => legacy /10"]

    I["history_service.resolve_scores()"] --> J["UI history rows\n(date range + comment filters)"]
```

## UI QA Checklist

Verify at `1366x768`:

- No vertical page overflow in the default dashboard view.
- Sticky topbar and sticky footer remain visible.
- Student strip appears as a separate rounded row under the topbar.
- `both` mode shows 3 cards; single modes show 2 cards with equal heights.
- Card bottom score strips stay pinned and chips wrap cleanly.

Verify at `1024px` width:

- Cards stack to a single column.
- Footer summary/actions remain visible and usable.
- Chip rows continue to wrap cleanly.
- Keyboard focus states are visible on fields, chips, and buttons.
