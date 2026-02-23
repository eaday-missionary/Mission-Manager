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


def test_dashboard_full_view_shows_horizontal_scroll_when_overflow() -> None:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display not available in test environment.")
        return

    root.geometry("900x500")
    view = DashboardView(root)
    view.pack(fill="both", expand=True)
    view.set_people([_sample_person()])
    root.update_idletasks()
    view.set_view_mode("full")
    root.update_idletasks()

    assert view.x_scroll.winfo_ismapped() == 1
    root.destroy()


def test_dashboard_full_view_hides_horizontal_scroll_when_fit() -> None:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display not available in test environment.")
        return

    root.geometry("2200x800")
    view = DashboardView(root)
    view.pack(fill="both", expand=True)
    view.set_people([_sample_person()])
    root.update_idletasks()
    view.set_view_mode("full")
    root.update_idletasks()

    assert view.x_scroll.winfo_ismapped() == 0
    root.destroy()
