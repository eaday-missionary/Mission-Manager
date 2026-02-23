import tkinter as tk

import pytest

from mission_manager.models import ConflictAnchor, DatasetState, ScheduleBlock, ScheduleConflict
from mission_manager.ui.app import MissionManagerApp
from mission_manager.ui.transfer_editor_view import TransferEditorView


class _FakeService:
    def load_local_dataset(self) -> DatasetState:
        return DatasetState(
            record_count=0,
            schema_version=1,
            last_imported_at=None,
            source_file_name=None,
            recovery_notice=None,
        )

    def list_people(self, filters=None, sort=None, search=None):
        return []

    def get_schedule_document(self):
        return []

    def list_schedule_conflicts(self):
        return []

    def import_excel(self, file_path: str):  # pragma: no cover - not used in this test
        raise NotImplementedError

    def append_excel(self, file_path: str):  # pragma: no cover - not used in this test
        raise NotImplementedError

    def replace_excel(self, file_path: str):  # pragma: no cover - not used in this test
        raise NotImplementedError

    def clear_dataset(self, confirm: bool) -> None:  # pragma: no cover - not used in this test
        return None


def test_app_wires_transfer_editor_tab(monkeypatch) -> None:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display not available in test environment.")
        return

    monkeypatch.setattr("mission_manager.ui.app.DashboardService", lambda: _FakeService())
    app = MissionManagerApp(root)
    tab_titles = [app.notebook.tab(tab_id, "text") for tab_id in app.notebook.tabs()]

    assert "Transfer Editor" in tab_titles
    assert app.dashboard_view.on_create_schedule is not None
    assert app.dashboard_view.on_fix_schedule is not None
    assert app.dashboard_view.y_scroll.cget("style") == "App.Vertical.TScrollbar"
    assert app.dashboard_view.x_scroll.cget("style") == "App.Horizontal.TScrollbar"
    assert app.transfer_view.conflict_list.cget("selectbackground") == "#F59E0B"

    root.destroy()


def test_transfer_view_active_selection_uses_orange_styles() -> None:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display not available in test environment.")
        return

    view = TransferEditorView(root)
    assert view.conflict_list.cget("selectbackground") == "#F59E0B"
    assert view.conflict_list.cget("selectforeground") == "#111827"
    assert view.schedule_text.cget("bg") == "#131923"
    assert view.schedule_text.cget("fg") == "#F8FAFC"
    assert view.conflict_list.cget("bg") == "#131923"
    assert view.conflict_list.cget("fg") == "#F8FAFC"
    assert view.schedule_text.tag_cget("conflict_active", "background") == "#F59E0B"
    assert view.schedule_text.tag_cget("conflict_active", "foreground") == "#111827"
    root.destroy()


def test_transfer_view_live_search_highlight_and_wrap() -> None:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display not available in test environment.")
        return

    view = TransferEditorView(root)
    block = ScheduleBlock(
        block_id="block-1",
        person_id="person-1",
        person_display_name="Alpha One",
        current_zone="Zone A",
        starting_companionship_key="alpha+beta",
        render_order=1,
        raw_text="Alpha Seoul route\nSecondary SEOUL route\n-----------------------------------",
    )
    view.set_schedule([block], [])

    view._search_query.set("seoul")
    view._refresh_search_matches()
    assert view._search_status_var.get() == "1/2"
    assert len(view.schedule_text.tag_ranges("search_match_all")) == 4
    assert len(view.schedule_text.tag_ranges("search_match_active")) == 2
    assert view.schedule_text.tag_cget("search_match_all", "background") == "#87CEFA"
    assert view.schedule_text.tag_cget("search_match_active", "background") == "#40E0D0"

    view._goto_next_match()
    assert view._search_status_var.get() == "2/2"
    view._goto_next_match()
    assert view._search_status_var.get() == "1/2"
    view._goto_previous_match()
    assert view._search_status_var.get() == "2/2"

    view._search_query.set("")
    view._refresh_search_matches()
    assert view._search_status_var.get() == "0 matches"
    assert len(view.schedule_text.tag_ranges("search_match_all")) == 0
    assert len(view.schedule_text.tag_ranges("search_match_active")) == 0
    root.destroy()


def test_transfer_search_reapplies_after_conflict_selection() -> None:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display not available in test environment.")
        return

    view = TransferEditorView(root)
    block = ScheduleBlock(
        block_id="block-1",
        person_id="person-1",
        person_display_name="Alpha One",
        current_zone="Zone A",
        starting_companionship_key="alpha+beta",
        render_order=1,
        raw_text="Alpha Seoul route\nSecondary line\n-----------------------------------",
    )
    conflict = ScheduleConflict(
        conflict_id="conflict-1",
        conflict_type="TIME_CONFLICT",
        severity="red",
        message="Alpha has a timing issue",
        anchors=[ConflictAnchor(block_id="block-1", line_start=1, line_end=1)],
    )
    view.set_schedule([block], [conflict])
    view._search_query.set("seoul")
    view._refresh_search_matches()
    active_before = tuple(str(i) for i in view.schedule_text.tag_ranges("search_match_active"))
    assert active_before

    view.conflict_list.selection_set(0)
    view._on_conflict_selected(None)
    active_after = tuple(str(i) for i in view.schedule_text.tag_ranges("search_match_active"))
    assert active_after == active_before
    root.destroy()


def test_app_ctrl_f_focuses_transfer_search_only_on_transfer_tab(monkeypatch) -> None:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display not available in test environment.")
        return

    monkeypatch.setattr("mission_manager.ui.app.DashboardService", lambda: _FakeService())
    app = MissionManagerApp(root)
    root.update_idletasks()
    focus_calls = {"count": 0}

    def _mark_focus() -> None:
        focus_calls["count"] += 1

    monkeypatch.setattr(app.transfer_view, "focus_search", _mark_focus)

    app.notebook.select(app.transfer_view)
    handled = app._focus_transfer_search(None)  # type: ignore[arg-type]
    assert handled == "break"
    assert focus_calls["count"] == 1

    app.notebook.select(app.dashboard_view)
    handled = app._focus_transfer_search(None)  # type: ignore[arg-type]
    assert handled is None
    assert focus_calls["count"] == 1
    root.destroy()
