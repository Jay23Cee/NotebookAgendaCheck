from pathlib import Path


APP_DISPLAY_NAME = "Notebook & Agenda Check"
APP_DASHBOARD_SUBTITLE = "Notebook & Agenda dashboard"

_PACKAGE_ROOT = Path(__file__).resolve().parent
_PACKAGED_DATA_DIR = _PACKAGE_ROOT / "data"

DEFAULT_STUDENTS_FILE = _PACKAGED_DATA_DIR / "mock_students.xlsx"
DEFAULT_OUTPUT_FILE = Path("records/notebook_agenda_checks.csv")
DEFAULT_UI_PREFERENCES_FILE = Path("records/ui_preferences.json")
DEFAULT_NA_CHECK_ERROR_LOG_FILE = Path("records/na_check_error_log.csv")
DEFAULT_NA_CHECK_QUARANTINE_DIR = Path("records/quarantine")
