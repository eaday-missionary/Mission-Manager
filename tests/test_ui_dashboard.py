import tkinter as tk
from types import SimpleNamespace

import pytest

from mission_manager.constants import PERSON_FIELDS
from mission_manager.ui.dashboard_view import DashboardView


def _sample_person() -> SimpleNamespace:
    payload = {field: None for field in PERSON_FIELDS}
    payload.update(
        {
            "id": "row-1",
            "first_name": "Jane",
            "last_name": "Smith",
            "current_zone": "Zone A",
            "current_area": "Area 1",
            "departure_time": "08:00",
            "arrival_time": "10:00",
            "staying": True,
            "second_leg": False,
        }
    )
    return SimpleNamespace(**payload)


def test_dashboard_full_view_shows_horizontal_scroll_when_overflow(monkeypatch) -> None:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display not available in test environment.")
        return

    view = DashboardView(root)
    view.pack(fill="both", expand=True)
    view.set_people([_sample_person()])
    calls = {"grid": 0, "remove": 0}
    monkeypatch.setattr(
        view.x_scroll, "grid", lambda *args, **kwargs: calls.__setitem__("grid", calls["grid"] + 1)
    )
    monkeypatch.setattr(
        view.x_scroll,
        "grid_remove",
        lambda *args, **kwargs: calls.__setitem__("remove", calls["remove"] + 1),
    )
    monkeypatch.setattr(view, "_set_full_widths", lambda: True)
    view.set_view_mode("full")
    assert calls["grid"] >= 1
    assert calls["remove"] == 0
    root.destroy()


def test_dashboard_full_view_hides_horizontal_scroll_when_fit(monkeypatch) -> None:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display not available in test environment.")
        return

    view = DashboardView(root)
    view.pack(fill="both", expand=True)
    view.set_people([_sample_person()])
    calls = {"grid": 0, "remove": 0}
    monkeypatch.setattr(
        view.x_scroll, "grid", lambda *args, **kwargs: calls.__setitem__("grid", calls["grid"] + 1)
    )
    monkeypatch.setattr(
        view.x_scroll,
        "grid_remove",
        lambda *args, **kwargs: calls.__setitem__("remove", calls["remove"] + 1),
    )
    monkeypatch.setattr(view, "_set_full_widths", lambda: False)
    view.set_view_mode("full")
    assert calls["remove"] >= 1
    root.destroy()


def test_dashboard_defaults_to_full_view() -> None:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display not available in test environment.")
        return

    view = DashboardView(root)
    assert view.view_mode == "full"
    assert view.full_btn.cget("style") == "ModeActive.TButton"
    assert view.compact_btn.cget("style") == "Mode.TButton"
    root.destroy()


def test_dashboard_shift_mousewheel_accelerates_small_trackpad_delta(monkeypatch) -> None:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display not available in test environment.")
        return

    view = DashboardView(root)
    calls: list[tuple[int, str]] = []
    monkeypatch.setattr(view.tree, "xview_scroll", lambda units, kind: calls.append((units, kind)))

    handled = view._on_table_shift_mouse_wheel(SimpleNamespace(delta=15))
    assert handled == "break"
    assert calls == [(-3, "units")]

    root.destroy()


def test_dashboard_shift_mousewheel_standard_delta_uses_multiplier(monkeypatch) -> None:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display not available in test environment.")
        return

    view = DashboardView(root)
    calls: list[tuple[int, str]] = []
    monkeypatch.setattr(view.tree, "xview_scroll", lambda units, kind: calls.append((units, kind)))

    view._on_table_shift_mouse_wheel(SimpleNamespace(delta=120))
    view._on_table_shift_mouse_wheel(SimpleNamespace(delta=-240))
    assert calls == [(-3, "units"), (6, "units")]

    root.destroy()


def test_dashboard_shift_scroll_bindings_exist() -> None:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display not available in test environment.")
        return

    view = DashboardView(root)
    for widget in (view.tree, view.table_container, view.x_scroll):
        assert widget.bind("<Shift-MouseWheel>")
        assert widget.bind("<Shift-Button-4>")
        assert widget.bind("<Shift-Button-5>")
    root.destroy()


def test_dashboard_add_new_callback_invoked() -> None:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display not available in test environment.")
        return

    view = DashboardView(root)
    calls = {"count": 0}

    def _mark() -> None:
        calls["count"] += 1

    view.on_add_new = _mark
    view._handle_add_new()
    assert calls["count"] == 1
    root.destroy()


def test_dashboard_includes_title_column_and_dash_display_for_blank_title() -> None:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display not available in test environment.")
        return

    view = DashboardView(root)
    person = _sample_person()
    view.set_people([person])

    assert "title" in view.tree.cget("columns")
    row_values = view.tree.item("row-1", "values")
    assert row_values[PERSON_FIELDS.index("title")] == "-"
    root.destroy()
