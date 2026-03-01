from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import statistics
import sys
import tempfile
import time

from nicegui import ui

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nicegui_app.na_check.models import RosterStudent
from app.nicegui_app.na_check.storage import CsvStore
from app.nicegui_app.pages.na_check_dashboard import NACheckDashboard

RUNS = 30
OVERHEAD_TARGET_MS = 5.0


@dataclass
class DummyInput:
    value: str

    def update(self) -> None:
        return None


@dataclass
class DummySelect:
    value: object = None
    options: dict[str, str] | None = None

    def __post_init__(self) -> None:
        if self.options is None:
            self.options = {}
        self.enabled = True

    def update(self) -> None:
        return None

    def enable(self) -> None:
        self.enabled = True

    def disable(self) -> None:
        self.enabled = False


@dataclass
class DummySwitch:
    value: object = None

    def __post_init__(self) -> None:
        self.enabled = True

    def update(self) -> None:
        return None

    def enable(self) -> None:
        self.enabled = True

    def disable(self) -> None:
        self.enabled = False


@dataclass
class DummyStickySwitch:
    value: bool

    def update(self) -> None:
        return None


def _students() -> list[RosterStudent]:
    return [
        RosterStudent(grade="6", period="1", subject="Math", student_id="S1", student_name="Student S1"),
        RosterStudent(grade="6", period="2", subject="Math", student_id="S2", student_name="Student S2"),
    ]


def _dashboard(tmp_path: Path, *, force_error: bool) -> NACheckDashboard:
    dashboard = NACheckDashboard()
    dashboard.output_file = tmp_path / "checks.csv"
    dashboard.preferences_file = tmp_path / "prefs.json"
    dashboard.error_logger.log_path = tmp_path / "error_log.csv"
    dashboard.store = CsvStore(
        dashboard.output_file,
        quarantine_dir=tmp_path / "quarantine",
        session_id=dashboard.session_id,
        logger=dashboard.error_logger,
    )
    dashboard.roster = _students()
    dashboard.filtered_students = list(dashboard.roster)
    dashboard.date_input = DummyInput("02/28/2026")  # type: ignore[assignment]
    dashboard.grade_select = DummySelect(value="6", options={"6": "Grade 6"})  # type: ignore[assignment]
    dashboard.class_switch = DummySwitch(value=True)  # type: ignore[assignment]
    dashboard.student_select = DummySelect(  # type: ignore[assignment]
        value=[],
        options={student.student_id: student.student_name for student in dashboard.roster},
    )
    dashboard.sticky_choices_switch = DummyStickySwitch(value=True)  # type: ignore[assignment]

    if force_error:
        def fail_append(_rows: list[dict[str, object]]) -> None:
            raise PermissionError("The process cannot access the file because it is being used by another process")

        dashboard.store.append_rows = fail_append  # type: ignore[method-assign]
    return dashboard


def _measure(*, force_error: bool) -> list[float]:
    samples: list[float] = []
    for _ in range(RUNS):
        with tempfile.TemporaryDirectory() as td:
            dashboard = _dashboard(Path(td), force_error=force_error)
            start = time.perf_counter()
            dashboard._save_students([dashboard.roster[0]])
            elapsed_ms = (time.perf_counter() - start) * 1000
            samples.append(elapsed_ms)
    return samples


def _median(values: list[float]) -> float:
    return statistics.median(values) if values else 0.0


def main() -> None:
    ui.notify = lambda *_args, **_kwargs: None

    normal_samples = _measure(force_error=False)
    error_samples = _measure(force_error=True)

    normal_median = _median(normal_samples)
    error_median = _median(error_samples)
    overhead_ms = error_median - normal_median

    print(f"Runs: {RUNS}")
    print(f"Normal save median: {normal_median:.3f} ms")
    print(f"Save+error+log median: {error_median:.3f} ms")
    print(f"Logging overhead: {overhead_ms:.3f} ms")
    print(f"Target (< {OVERHEAD_TARGET_MS:.1f} ms): {'PASS' if overhead_ms < OVERHEAD_TARGET_MS else 'FAIL'}")
    if overhead_ms >= OVERHEAD_TARGET_MS:
        print("Recommendation: logging overhead exceeded threshold; consider async log queue.")


if __name__ == "__main__":
    main()
