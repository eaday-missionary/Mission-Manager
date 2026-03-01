import tkinter as tk
from types import SimpleNamespace

import pytest

from mission_manager.ui.detail_view import DetailView


def test_detail_view_entry_binds_mouse_wheel_scroll_events(monkeypatch) -> None:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display not available in test environment.")
        return

    root.geometry("520x220")
    view = DetailView(root)
    view.pack(fill="both", expand=True)
    root.update_idletasks()

    entry = next(iter(view.entries.values()))
    assert entry.bind("<MouseWheel>")
    assert entry.bind("<Button-4>")
    assert entry.bind("<Button-5>")

    # Verify wheel handler scrolls the canvas as expected.
    calls: list[tuple[int, str]] = []

    def _fake_scroll(units: int, mode: str) -> None:
        calls.append((units, mode))

    monkeypatch.setattr(view.canvas, "yview_scroll", _fake_scroll)
    result = view._on_mouse_wheel(SimpleNamespace(delta=-120))
    assert result == "break"
    assert calls == [(1, "units")]

    root.destroy()


def test_detail_view_switches_between_add_and_apply_modes() -> None:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display not available in test environment.")
        return

    view = DetailView(root)
    add_calls = {"count": 0}
    apply_calls = {"count": 0}

    def _on_add(_patch: dict[str, str]) -> None:
        add_calls["count"] += 1

    def _on_apply(_person_id: str, _patch: dict[str, str]) -> None:
        apply_calls["count"] += 1

    view.on_add = _on_add
    view.on_apply = _on_apply

    view.enter_add_mode()
    assert view.primary_btn.cget("text") == "Add"
    view._submit()
    assert add_calls["count"] == 1
    assert apply_calls["count"] == 0

    person = SimpleNamespace(id="person-1", **{field: None for field in view.entries})
    person.first_name = "Jane"
    person.last_name = "Smith"
    view.enter_edit_mode(person)
    assert view.primary_btn.cget("text") == "Apply"
    view._submit()
    assert apply_calls["count"] == 1
    root.destroy()


def test_detail_view_title_field_is_editable_and_dash_maps_to_blank() -> None:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display not available in test environment.")
        return

    view = DetailView(root)
    assert "title" in view.entries

    title_entry = view.entries["title"]
    title_entry.delete(0, "end")
    title_entry.insert(0, "-")
    patch = view._build_patch()
    assert patch["title"] == ""

    title_entry.delete(0, "end")
    title_entry.insert(0, "E")
    patch = view._build_patch()
    assert patch["title"] == "E"
    root.destroy()
