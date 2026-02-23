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
