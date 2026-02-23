import tkinter as tk
from types import SimpleNamespace

import pytest

from mission_manager.constants import PERSON_FIELDS
from mission_manager.models import ConflictAnchor, DatasetState, ScheduleBlock, ScheduleConflict
from mission_manager.ui.app import MissionManagerApp
from mission_manager.ui.transfer_editor_view import TransferEditorView


def _person_row(person_id: str, first_name: str, last_name: str) -> SimpleNamespace:
    payload = {field: None for field in PERSON_FIELDS}
    payload.update(
        {
            "id": person_id,
            "first_name": first_name,
            "last_name": last_name,
            "current_zone": "Zone A",
            "current_area": "Area 1",
            "departure_time": "08:00",
            "arrival_time": "10:00",
            "staying": True,
            "second_leg": False,
        }
    )
    return SimpleNamespace(**payload)


class _FakeService:
    def __init__(self) -> None:
        self.people = []

    def load_local_dataset(self) -> DatasetState:
        return DatasetState(
            record_count=len(self.people),
            schema_version=1,
            last_imported_at=None,
            source_file_name=None,
            recovery_notice=None,
        )

    def list_people(self, filters=None, sort=None, search=None):
        return list(self.people)

    def get_schedule_document(self):
        return []

    def list_schedule_conflicts(self):
        return []

    def get_person(self, person_id: str):
        for person in self.people:
            if person.id == person_id:
                return person
        return None

    def create_person(self, patch):
        created = _person_row(
            f"row-{len(self.people) + 1}",
            patch.get("first_name") or "New",
            patch.get("last_name") or "Person",
        )
        self.people.append(created)
        return created, []

    def update_person(self, person_id, patch):
        return self.get_person(person_id), []

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
    assert app.dashboard_view.on_add_new is not None
    assert app.dashboard_view.y_scroll.cget("style") == "App.Vertical.TScrollbar"
    assert app.dashboard_view.x_scroll.cget("style") == "App.Horizontal.TScrollbar"
    assert app.transfer_view.conflict_list.cget("selectbackground") == "#F59E0B"

    root.destroy()


def test_transfer_view_renders_card_text_and_styles() -> None:
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
    widget = view._block_text_widgets["block-1"]

    assert widget.cget("bg") == "#131923"
    assert widget.cget("fg") == "#F8FAFC"
    assert view.conflict_list.cget("bg") == "#131923"
    assert view.conflict_list.cget("fg") == "#F8FAFC"
    assert widget.tag_cget("search_match_all", "background") == "#87CEFA"
    assert widget.tag_cget("search_match_active", "background") == "#40E0D0"
    root.destroy()


def test_transfer_view_binds_scroll_on_card_containers() -> None:
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
        raw_text="Alpha Seoul route\n-----------------------------------",
    )
    view.set_schedule([block], [])
    card = view._block_frames["block-1"]
    title, body = card.winfo_children()

    assert view.cards_canvas.bind("<MouseWheel>")
    assert view.cards_frame.bind("<MouseWheel>")
    assert card.bind("<MouseWheel>")
    assert title.bind("<MouseWheel>")
    assert body.bind("<MouseWheel>")
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
    widget = view._block_text_widgets["block-1"]

    view._search_query.set("seoul")
    view._refresh_search_matches()
    assert view._search_status_var.get() == "1/2"
    assert len(widget.tag_ranges("search_match_all")) == 4
    assert len(widget.tag_ranges("search_match_active")) == 2

    view._goto_next_match()
    assert view._search_status_var.get() == "2/2"
    view._goto_next_match()
    assert view._search_status_var.get() == "1/2"
    view._goto_previous_match()
    assert view._search_status_var.get() == "2/2"

    view._search_query.set("")
    view._refresh_search_matches()
    assert view._search_status_var.get() == "0 matches"
    assert len(widget.tag_ranges("search_match_all")) == 0
    assert len(widget.tag_ranges("search_match_active")) == 0
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
    widget = view._block_text_widgets["block-1"]
    view._search_query.set("seoul")
    view._refresh_search_matches()
    active_before = tuple(str(i) for i in widget.tag_ranges("search_match_active"))
    assert active_before

    view.conflict_list.selection_set(0)
    view._on_conflict_selected(None)
    active_after = tuple(str(i) for i in widget.tag_ranges("search_match_active"))
    assert active_after == active_before
    root.destroy()


def test_transfer_card_double_click_opens_person_callback() -> None:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display not available in test environment.")
        return

    view = TransferEditorView(root)
    block = ScheduleBlock(
        block_id="block-1",
        person_id="person-99",
        person_display_name="Alpha One",
        current_zone="Zone A",
        starting_companionship_key="alpha+beta",
        render_order=1,
        raw_text="Alpha Seoul route\n-----------------------------------",
    )
    calls = {"id": None}
    view.on_open_person = lambda person_id: calls.update(id=person_id)
    view.set_schedule([block], [])
    view._open_person("person-99")
    assert calls["id"] == "person-99"
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


def test_onboarding_add_new_opens_detail_add_mode(monkeypatch) -> None:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display not available in test environment.")
        return

    fake_service = _FakeService()
    monkeypatch.setattr("mission_manager.ui.app.DashboardService", lambda: fake_service)
    app = MissionManagerApp(root)
    app.start_add_person()

    assert app.notebook.select() == str(app.detail_view)
    assert app.detail_view.primary_btn.cget("text") == "Add"
    root.destroy()


def test_add_detail_returns_to_dashboard_and_selects_new_row(monkeypatch) -> None:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display not available in test environment.")
        return

    fake_service = _FakeService()
    monkeypatch.setattr("mission_manager.ui.app.DashboardService", lambda: fake_service)
    app = MissionManagerApp(root)
    app.start_add_person()
    app.add_detail({"first_name": "Mina", "last_name": "Cho"})
    root.update_idletasks()

    assert app.notebook.select() == str(app.dashboard_view)
    selected = app.dashboard_view.tree.selection()
    assert selected
    row_id = selected[0]
    values = app.dashboard_view.tree.item(row_id, "values")
    assert values[0] == "Mina"
    assert values[1] == "Cho"
    root.destroy()


def test_apply_detail_returns_to_transfer_when_opened_from_transfer(monkeypatch) -> None:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display not available in test environment.")
        return

    fake_service = _FakeService()
    fake_service.people = [_person_row("person-1", "Mina", "Cho")]
    monkeypatch.setattr("mission_manager.ui.app.DashboardService", lambda: fake_service)
    app = MissionManagerApp(root)
    root.update_idletasks()

    app.notebook.select(app.transfer_view)
    app.open_detail("person-1")
    app.apply_detail("person-1", {"first_name": "Mina"})

    assert app.notebook.select() == str(app.transfer_view)
    root.destroy()


def test_apply_detail_returns_to_dashboard_when_opened_from_dashboard(monkeypatch) -> None:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display not available in test environment.")
        return

    fake_service = _FakeService()
    fake_service.people = [_person_row("person-1", "Mina", "Cho")]
    monkeypatch.setattr("mission_manager.ui.app.DashboardService", lambda: fake_service)
    app = MissionManagerApp(root)
    root.update_idletasks()

    app.notebook.select(app.dashboard_view)
    app.open_detail("person-1")
    app.apply_detail("person-1", {"first_name": "Mina"})
    root.update_idletasks()

    assert app.notebook.select() == str(app.dashboard_view)
    assert app.dashboard_view.tree.selection() == ("person-1",)
    root.destroy()
