from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace

import pytest

from app.nicegui_app.pages import na_check_dashboard as dashboard_module
from app.nicegui_app.pages.na_check_dashboard import NACheckDashboard


class _FakeSlotContext:
    def __enter__(self) -> _FakeSlotContext:
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


@dataclass
class _FakeInput:
    label: str
    value: str
    context_stack: list[object]
    props_calls: list[str] = field(default_factory=list)
    classes_calls: list[str] = field(default_factory=list)
    handlers: dict[str, object] = field(default_factory=dict)
    slots: list[str] = field(default_factory=list)

    def props(self, value: str) -> _FakeInput:
        self.props_calls.append(value)
        return self

    def classes(self, value: str) -> _FakeInput:
        self.classes_calls.append(value)
        return self

    def on(self, event: str, handler) -> _FakeInput:
        self.handlers[event] = handler
        return self

    def add_slot(self, name: str) -> _FakeSlotContext:
        self.slots.append(name)
        return _FakeSlotContext()

    def __enter__(self) -> _FakeInput:
        self.context_stack.append(self)
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        assert self.context_stack and self.context_stack[-1] is self
        self.context_stack.pop()
        return False


@dataclass
class _FakeMenu:
    parent: object | None
    props_calls: list[str] = field(default_factory=list)
    open_calls: int = 0
    close_calls: int = 0

    def props(self, value: str) -> _FakeMenu:
        self.props_calls.append(value)
        return self

    def open(self) -> None:
        self.open_calls += 1

    def close(self) -> None:
        self.close_calls += 1

    def __enter__(self) -> _FakeMenu:
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


@dataclass
class _FakeDate:
    value: str
    on_change: object | None = None
    props_calls: list[str] = field(default_factory=list)
    bound_to: object | None = None

    def props(self, value: str) -> _FakeDate:
        self.props_calls.append(value)
        return self

    def bind_value(self, target: object) -> _FakeDate:
        self.bound_to = target
        return self

    def emit_change(self) -> None:
        if self.on_change is not None:
            self.on_change(SimpleNamespace(value=self.value))


@dataclass
class _FakeIcon:
    name: str
    classes_calls: list[str] = field(default_factory=list)
    handlers: dict[str, object] = field(default_factory=dict)

    def classes(self, value: str) -> _FakeIcon:
        self.classes_calls.append(value)
        return self

    def on(self, event: str, handler) -> _FakeIcon:
        self.handlers[event] = handler
        return self


@pytest.fixture
def patched_date_ui(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    context_stack: list[object] = []
    created: dict[str, object] = {}

    def fake_input(*, label: str, value: str):
        instance = _FakeInput(label=label, value=value, context_stack=context_stack)
        created["input"] = instance
        return instance

    def fake_menu():
        parent = context_stack[-1] if context_stack else None
        instance = _FakeMenu(parent=parent)
        created["menu"] = instance
        return instance

    def fake_date(*, value: str, on_change=None):
        instance = _FakeDate(value=value, on_change=on_change)
        created["date"] = instance
        return instance

    def fake_icon(name: str):
        instance = _FakeIcon(name=name)
        created["icon"] = instance
        return instance

    monkeypatch.setattr(dashboard_module.ui, "input", fake_input)
    monkeypatch.setattr(dashboard_module.ui, "menu", fake_menu)
    monkeypatch.setattr(dashboard_module.ui, "date", fake_date)
    monkeypatch.setattr(dashboard_module.ui, "icon", fake_icon)
    return created


def test_build_date_control_anchors_menu_and_binds_date(patched_date_ui: dict[str, object]) -> None:
    dashboard = NACheckDashboard()

    dashboard._build_date_control(default_date="02/28/2026")

    date_input = patched_date_ui["input"]
    date_menu = patched_date_ui["menu"]
    date_picker = patched_date_ui["date"]
    assert dashboard.date_input is date_input
    assert date_menu.parent is date_input
    assert date_menu.props_calls == ['no-parent-event anchor="bottom right" self="top right"']
    assert date_picker.props_calls == ["mask=MM/DD/YYYY"]
    assert date_picker.bound_to is date_input
    assert date_input.slots == ["append"]
    assert date_input.value == "02/28/2026"


def test_build_date_control_opens_menu_from_input_and_icon(patched_date_ui: dict[str, object]) -> None:
    dashboard = NACheckDashboard()

    dashboard._build_date_control(default_date="02/28/2026")

    date_input = patched_date_ui["input"]
    date_menu = patched_date_ui["menu"]
    icon = patched_date_ui["icon"]
    assert "click" in date_input.handlers
    assert "click" in icon.handlers

    date_input.handlers["click"]()
    icon.handlers["click"]()

    assert date_menu.open_calls == 2


def test_build_date_control_closes_menu_after_picker_change(patched_date_ui: dict[str, object]) -> None:
    dashboard = NACheckDashboard()

    dashboard._build_date_control(default_date="02/28/2026")

    date_menu = patched_date_ui["menu"]
    date_picker = patched_date_ui["date"]
    date_picker.emit_change()

    assert date_menu.close_calls == 1


def test_build_date_control_preserves_date_change_handler(patched_date_ui: dict[str, object]) -> None:
    dashboard = NACheckDashboard()

    dashboard._build_date_control(default_date="02/28/2026")

    date_input = patched_date_ui["input"]
    assert "change" in date_input.handlers
    handler = date_input.handlers["change"]
    assert getattr(handler, "__self__", None) is dashboard
    assert getattr(handler, "__func__", None) is NACheckDashboard._on_date_change
