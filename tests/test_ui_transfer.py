import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk
from types import SimpleNamespace

import pytest

from mission_manager.constants import PERSON_FIELDS
from mission_manager.models import ConflictAnchor, DatasetState, ScheduleBlock, ScheduleConflict
from mission_manager.ui.app import MissionManagerApp
from mission_manager.ui.schedule_text_view import ScheduleTextView
from mission_manager.ui.transfer_editor_view import TransferEditorView


def _person_row(
    person_id: str,
    first_name: str,
    last_name: str,
    *,
    title: str | None = None,
) -> SimpleNamespace:
    payload = {field: None for field in PERSON_FIELDS}
    payload.update(
        {
            "id": person_id,
            "first_name": first_name,
            "last_name": last_name,
            "title": title,
            "current_zone": "Zone A",
            "current_area": "Area 1",
            "departure_time": "08:00",
            "arrival_time": "10:00",
            "staying": True,
            "second_leg": False,
        }
    )
    return SimpleNamespace(**payload)


def _canvas_anchor_for(view: TransferEditorView, block_id: str, text_index: str | None) -> float:
    frame = view._block_frames[block_id]
    widget = view._block_text_widgets.get(block_id)
    anchor = view._resolve_anchor_canvas_y(frame, widget, text_index)
    assert anchor is not None
    return anchor


class _FakeService:
    def __init__(self) -> None:
        self.people = []
        self.schedule_blocks: list[ScheduleBlock] = []
        self.schedule_conflicts: list[ScheduleConflict] = []
        self.schedule_build_calls = 0
        self.replace_should_fail = False
        self.auto_schedule_should_fail = False

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
        return list(self.schedule_blocks)

    def list_schedule_conflicts(self):
        return list(self.schedule_conflicts)

    def get_person(self, person_id: str):
        for person in self.people:
            if person.id == person_id:
                return person
        return None

    def _refresh_schedule_projection(self) -> None:
        self.schedule_blocks = [
            _block(
                f"auto-{person.id}",
                person.id,
                f"{person.first_name} {person.last_name}\n-----------------------------------",
                index + 1,
            )
            for index, person in enumerate(self.people)
        ]
        self.schedule_conflicts = []

    def create_person(self, patch):
        created = _person_row(
            f"row-{len(self.people) + 1}",
            patch.get("first_name") or "New",
            patch.get("last_name") or "Person",
        )
        self.people.append(created)
        return created, []

    def update_person(self, person_id, patch):
        person = self.get_person(person_id)
        if not person:
            return None, []
        for field, value in patch.items():
            if hasattr(person, field):
                setattr(person, field, value)
        return person, []

    def import_excel(self, file_path: str):
        self.people = [_person_row("import-1", "Import", "One")]
        return SimpleNamespace(
            success=True,
            records_processed=1,
            records_inserted=1,
            records_updated=0,
            records_skipped=0,
            errors=[],
            warnings=[],
        )

    def append_excel(self, file_path: str):
        next_idx = len(self.people) + 1
        self.people.append(_person_row(f"append-{next_idx}", "Append", str(next_idx)))
        return SimpleNamespace(
            success=True,
            records_processed=1,
            records_inserted=1,
            records_updated=0,
            records_skipped=0,
            errors=[],
            warnings=[],
        )

    def replace_excel(self, file_path: str):
        if self.replace_should_fail:
            return SimpleNamespace(
                success=False,
                records_processed=1,
                records_skipped=0,
                errors=[SimpleNamespace(message="Replace failed", row_number=None)],
                warnings=[],
            )
        self.people = [_person_row("replace-1", "Replace", "One")]
        return SimpleNamespace(
            success=True,
            records_processed=1,
            records_inserted=1,
            records_updated=0,
            records_skipped=0,
            errors=[],
            warnings=[],
        )

    def create_schedule(self, confirm_overwrite: bool):
        if not confirm_overwrite:
            return SimpleNamespace(
                success=False,
                errors=[SimpleNamespace(message="Confirmation required")],
                warnings=[],
                blocks_generated=0,
                conflicts_found=0,
            )
        self.schedule_build_calls += 1
        if self.auto_schedule_should_fail:
            return SimpleNamespace(
                success=False,
                errors=[SimpleNamespace(message="Auto schedule failed")],
                warnings=[],
                blocks_generated=0,
                conflicts_found=0,
            )
        self._refresh_schedule_projection()
        return SimpleNamespace(
            success=True,
            errors=[],
            warnings=[],
            blocks_generated=len(self.schedule_blocks),
            conflicts_found=0,
        )

    def clear_dataset(self, confirm: bool) -> None:
        if not confirm:
            return
        self.people = []
        self.schedule_blocks = []
        self.schedule_conflicts = []


def _block(block_id: str, person_id: str, raw_text: str, order: int) -> ScheduleBlock:
    return ScheduleBlock(
        block_id=block_id,
        person_id=person_id,
        person_display_name=f"Person {person_id}",
        current_zone="Zone A",
        starting_companionship_key=f"key-{person_id}",
        render_order=order,
        raw_text=raw_text,
    )


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
    assert "Schedule Text" in tab_titles
    assert app.dashboard_view.on_create_schedule is not None
    assert app.dashboard_view.on_add_new is not None
    assert app.dashboard_view.y_scroll.cget("style") == "App.Vertical.TScrollbar"
    assert app.dashboard_view.x_scroll.cget("style") == "App.Horizontal.TScrollbar"
    assert app.transfer_view.conflict_list.cget("selectbackground") == "#F59E0B"
    assert app.dashboard_view.view_mode == "full"
    assert app.dashboard_view.full_btn.cget("style") == "ModeActive.TButton"
    assert root.title() == "Mission Manager"

    root.destroy()


def test_app_theme_uses_clam_and_readable_tab_button_colors(monkeypatch) -> None:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display not available in test environment.")
        return

    monkeypatch.setattr("mission_manager.ui.app.DashboardService", lambda: _FakeService())
    app = MissionManagerApp(root)
    style = ttk.Style(root)

    assert style.theme_use() == "clam"
    assert style.lookup("TButton", "foreground") == "#FFFFFF"
    assert style.lookup("TButton", "background") == "#3B82F6"
    assert style.lookup("TNotebook.Tab", "foreground") == "#E8ECF1"
    assert style.lookup("TNotebook.Tab", "background") == "#202632"
    assert style.lookup("Title.TLabel", "foreground") == "#E8ECF1"
    assert tkfont.Font(font=app.schedule_text_view.text_widget.cget("font")).actual("family") == "Batang"
    assert tkfont.Font(font=app.transfer_view.conflict_list.cget("font")).actual("family") == "Batang"
    root.destroy()


def test_schedule_text_view_combines_blocks_in_render_order() -> None:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display not available in test environment.")
        return

    view = ScheduleTextView(root)
    view.set_schedule(
        [
            _block("b2", "2", "SECOND\n-----------------------------------", 2),
            _block("b1", "1", "FIRST\n-----------------------------------", 1),
        ]
    )
    rendered = view.text_widget.get("1.0", "end-1c")
    assert "FIRST" in rendered
    assert "SECOND" in rendered
    assert rendered.index("FIRST") < rendered.index("SECOND")
    root.destroy()


def test_schedule_text_view_sanitizes_legacy_hh_mm_ss_text() -> None:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display not available in test environment.")
        return

    view = ScheduleTextView(root)
    view.set_schedule(
        [
            _block(
                "b1",
                "1",
                "Departure Time: 08:30:00\nArrival Time: 09:45:59\n---------------",
                1,
            ),
        ]
    )
    rendered = view.text_widget.get("1.0", "end-1c")
    assert "08:30:00" not in rendered
    assert "09:45:59" not in rendered
    assert "Departure Time: 08:30" in rendered
    assert "Arrival Time: 09:45" in rendered
    root.destroy()


def test_schedule_text_view_live_search_highlight_and_wrap() -> None:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display not available in test environment.")
        return

    view = ScheduleTextView(root)
    view.set_schedule(
        [
            _block("b1", "1", "Alpha Seoul route\n---------------", 1),
            _block("b2", "2", "Secondary SEOUL route\n---------------", 2),
        ]
    )

    view._search_query.set("seoul")
    view._refresh_search_matches()
    assert view._search_status_var.get() == "1/2"
    assert len(view.text_widget.tag_ranges("search_match_all")) == 4
    assert len(view.text_widget.tag_ranges("search_match_active")) == 2

    view._goto_next_match()
    assert view._search_status_var.get() == "2/2"
    view._goto_next_match()
    assert view._search_status_var.get() == "1/2"
    view._goto_previous_match()
    assert view._search_status_var.get() == "2/2"

    view._search_query.set("")
    view._refresh_search_matches()
    assert view._search_status_var.get() == "0 matches"
    assert len(view.text_widget.tag_ranges("search_match_all")) == 0
    assert len(view.text_widget.tag_ranges("search_match_active")) == 0
    root.destroy()


def test_schedule_text_mode_defaults_to_original_names() -> None:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display not available in test environment.")
        return

    view = ScheduleTextView(root)
    assert view._name_mode == "original"
    assert view.original_names_btn.cget("style") == "ModeActive.TButton"
    assert view.missionary_titles_btn.cget("style") == "Mode.TButton"
    root.destroy()


def test_schedule_text_missionary_mode_replaces_unique_last_name_as_title_last_name() -> None:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display not available in test environment.")
        return

    view = ScheduleTextView(root)
    person = _person_row("person-1", "John", "Kim", title="E")
    view.set_schedule(
        [
            _block("b1", "person-1", "John Kim\nMeet John Kim at gate.\n---------------", 1),
        ],
        people=[person],
    )

    view._set_name_mode("missionary")
    rendered = view.text_widget.get("1.0", "end-1c")
    assert "Elder Kim" in rendered
    assert "John Kim" not in rendered
    root.destroy()


def test_schedule_text_missionary_mode_keeps_first_name_when_last_name_is_shared() -> None:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display not available in test environment.")
        return

    view = ScheduleTextView(root)
    people = [
        _person_row("person-1", "John", "Kim", title="E"),
        _person_row("person-2", "Mina", "Kim", title="S"),
    ]
    view.set_schedule(
        [
            _block("b1", "person-1", "John Kim meets Mina Kim.\n---------------", 1),
        ],
        people=people,
    )

    view._set_name_mode("missionary")
    rendered = view.text_widget.get("1.0", "end-1c")
    assert "Elder John Kim meets Sister Mina Kim." in rendered
    assert "Elder Kim" not in rendered
    assert "Sister Kim" not in rendered
    root.destroy()


def test_schedule_text_missionary_mode_blank_and_invalid_title_map_to_blank() -> None:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display not available in test environment.")
        return

    view = ScheduleTextView(root)
    people = [
        _person_row("person-1", "John", "Park", title="-"),
        _person_row("person-2", "Mina", "Lee", title="X"),
    ]
    view.set_schedule(
        [
            _block("b1", "person-1", "John Park then Mina Lee.\n---------------", 1),
        ],
        people=people,
    )

    view._set_name_mode("missionary")
    rendered = view.text_widget.get("1.0", "end-1c")
    assert "BLANK Park then BLANK Lee." in rendered
    assert "John Park" not in rendered
    assert "Mina Lee" not in rendered
    root.destroy()


def test_schedule_text_toggle_preserves_search_query_and_recomputes_matches() -> None:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display not available in test environment.")
        return

    view = ScheduleTextView(root)
    person = _person_row("person-1", "John", "Kim", title="E")
    view.set_schedule(
        [
            _block("b1", "person-1", "John Kim\n---------------", 1),
        ],
        people=[person],
    )
    view._search_query.set("elder")
    view._refresh_search_matches()
    assert view._search_status_var.get() == "0 matches"

    view._set_name_mode("missionary")
    assert view._search_query.get() == "elder"
    assert view._search_status_var.get() == "1/1"
    assert view.original_names_btn.cget("style") == "Mode.TButton"
    assert view.missionary_titles_btn.cget("style") == "ModeActive.TButton"
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


def test_transfer_view_sanitizes_legacy_hh_mm_ss_text() -> None:
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
        raw_text="Departure Time: 08:30:00\nArrival Time: 09:45:59\n-----------------------------------",
    )
    view.set_schedule([block], [])
    widget = view._block_text_widgets["block-1"]
    rendered = widget.get("1.0", "end-1c")

    assert "08:30:00" not in rendered
    assert "09:45:59" not in rendered
    assert "Departure Time: 08:30" in rendered
    assert "Arrival Time: 09:45" in rendered
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


def test_transfer_center_anchor_in_view_uses_centered_fraction_math(monkeypatch) -> None:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display not available in test environment.")
        return

    view = TransferEditorView(root)
    calls: list[float] = []
    monkeypatch.setattr(view.cards_canvas, "bbox", lambda _tag: (0, 0, 800, 2000))
    monkeypatch.setattr(view.cards_canvas, "winfo_height", lambda: 400)
    monkeypatch.setattr(view.cards_canvas, "yview_moveto", lambda fraction: calls.append(fraction))

    view._center_anchor_in_view(680)

    assert calls
    assert calls[0] == pytest.approx((680 - 200) / 2000)
    root.destroy()


def test_transfer_scroll_to_block_has_no_drift_with_canvas_fraction_mapping(monkeypatch) -> None:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display not available in test environment.")
        return

    view = TransferEditorView(root)
    anchors = {
        "block-1": 700.0,
        "block-2": 1450.0,
        "block-3": 2300.0,
        "block-4": 3150.0,
        "block-5": 4000.0,
        "block-6": 4750.0,
    }
    view._block_frames = {block_id: object() for block_id in anchors}
    view._block_text_widgets = {}

    region_top = 100.0
    total_height = 5000.0
    viewport_height = 600.0
    state = {"top": region_top}

    monkeypatch.setattr(
        view.cards_canvas,
        "bbox",
        lambda _tag: (0.0, region_top, 900.0, region_top + total_height),
    )
    monkeypatch.setattr(view.cards_canvas, "winfo_height", lambda: viewport_height)
    monkeypatch.setattr(view.cards_canvas, "canvasy", lambda _y: state["top"])

    def _set_yview(fraction: float) -> None:
        state["top"] = region_top + (fraction * total_height)

    monkeypatch.setattr(view.cards_canvas, "yview_moveto", _set_yview)
    monkeypatch.setattr(view, "_ensure_cards_geometry_ready", lambda: None)
    monkeypatch.setattr(
        view,
        "_resolve_anchor_canvas_y",
        lambda _frame, _widget, _text_index: anchors[_frame],  # type: ignore[index]
    )

    # Re-map block id lookups to anchor keys while preserving _scroll_to_block call shape.
    view._block_frames = {block_id: block_id for block_id in anchors}

    errors: list[float] = []
    for _ in range(3):
        for block_id, anchor in anchors.items():
            view._scroll_to_block(block_id, None)
            viewport_mid = state["top"] + (viewport_height / 2)
            errors.append(abs(anchor - viewport_mid))

    assert max(errors) <= 2.0
    root.destroy()


def test_transfer_search_jump_centers_target_card(monkeypatch) -> None:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display not available in test environment.")
        return

    view = TransferEditorView(root)
    blocks = [
        ScheduleBlock(
            block_id=f"block-{i}",
            person_id=f"person-{i}",
            person_display_name=f"Person {i}",
            current_zone="Zone A",
            starting_companionship_key=f"key-{i}",
            render_order=i,
            raw_text=("match target" if i == 4 else "no target") + "\n-----------------------------------",
        )
        for i in range(1, 7)
    ]
    view.set_schedule(blocks, [])
    root.update_idletasks()

    y_calls: list[float] = []
    original_yview_moveto = view.cards_canvas.yview_moveto

    def _capture_yview(fraction: float) -> None:
        y_calls.append(fraction)
        original_yview_moveto(fraction)
        root.update_idletasks()

    monkeypatch.setattr(view.cards_canvas, "yview_moveto", _capture_yview)
    view._search_query.set("match target")
    view._refresh_search_matches()

    assert y_calls
    assert view._active_search_match_index is not None
    block_id, start_idx, _ = view._search_matches[view._active_search_match_index]
    anchor = _canvas_anchor_for(view, block_id, start_idx)
    canvas_top = view.cards_canvas.canvasy(0)
    canvas_mid = canvas_top + (view.cards_canvas.winfo_height() / 2)
    assert abs(canvas_mid - anchor) <= 4
    root.destroy()


def test_transfer_conflict_jump_centers_target_card(monkeypatch) -> None:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display not available in test environment.")
        return

    view = TransferEditorView(root)
    blocks = [
        ScheduleBlock(
            block_id=f"block-{i}",
            person_id=f"person-{i}",
            person_display_name=f"Person {i}",
            current_zone="Zone A",
            starting_companionship_key=f"key-{i}",
            render_order=i,
            raw_text=f"Card {i}\n-----------------------------------",
        )
        for i in range(1, 7)
    ]
    conflict = ScheduleConflict(
        conflict_id="conflict-1",
        conflict_type="TIME_CONFLICT",
        severity="red",
        message="Target conflict",
        anchors=[ConflictAnchor(block_id="block-5", line_start=1, line_end=1)],
    )
    view.set_schedule(blocks, [conflict])
    root.update_idletasks()

    y_calls: list[float] = []
    original_yview_moveto = view.cards_canvas.yview_moveto

    def _capture_yview(fraction: float) -> None:
        y_calls.append(fraction)
        original_yview_moveto(fraction)
        root.update_idletasks()

    monkeypatch.setattr(view.cards_canvas, "yview_moveto", _capture_yview)
    view.conflict_list.selection_set(0)
    view._on_conflict_selected(None)

    assert y_calls
    anchor = _canvas_anchor_for(view, "block-5", "1.0")
    canvas_top = view.cards_canvas.canvasy(0)
    canvas_mid = canvas_top + (view.cards_canvas.winfo_height() / 2)
    assert abs(canvas_mid - anchor) <= 4
    root.destroy()


def test_transfer_first_and_last_blocks_center_with_gutters() -> None:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display not available in test environment.")
        return

    view = TransferEditorView(root)
    blocks = [
        ScheduleBlock(
            block_id=f"block-{i}",
            person_id=f"person-{i}",
            person_display_name=f"Person {i}",
            current_zone="Zone A",
            starting_companionship_key=f"key-{i}",
            render_order=i,
            raw_text=f"Card {i}\n-----------------------------------",
        )
        for i in range(1, 9)
    ]
    view.set_schedule(blocks, [])
    root.update_idletasks()

    for block_id in ("block-1", "block-8"):
        view._scroll_to_block(block_id, "1.0")
        root.update_idletasks()
        anchor = _canvas_anchor_for(view, block_id, "1.0")
        canvas_mid = view.cards_canvas.canvasy(0) + (view.cards_canvas.winfo_height() / 2)
        assert abs(canvas_mid - anchor) <= 4
    root.destroy()


def test_transfer_repeated_search_navigation_does_not_drift_from_center() -> None:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display not available in test environment.")
        return

    view = TransferEditorView(root)
    blocks = [
        ScheduleBlock(
            block_id=f"block-{i}",
            person_id=f"person-{i}",
            person_display_name=f"Person {i}",
            current_zone="Zone A",
            starting_companionship_key=f"key-{i}",
            render_order=i,
            raw_text="target keyword\n-----------------------------------",
        )
        for i in range(1, 10)
    ]
    view.set_schedule(blocks, [])
    view._search_query.set("target")
    view._refresh_search_matches()
    root.update_idletasks()

    errors: list[float] = []
    for _ in range(20):
        view._goto_next_match()
        root.update_idletasks()
        assert view._active_search_match_index is not None
        block_id, start_idx, _ = view._search_matches[view._active_search_match_index]
        anchor = _canvas_anchor_for(view, block_id, start_idx)
        canvas_mid = view.cards_canvas.canvasy(0) + (view.cards_canvas.winfo_height() / 2)
        errors.append(abs(canvas_mid - anchor))
    for _ in range(20):
        view._goto_previous_match()
        root.update_idletasks()
        assert view._active_search_match_index is not None
        block_id, start_idx, _ = view._search_matches[view._active_search_match_index]
        anchor = _canvas_anchor_for(view, block_id, start_idx)
        canvas_mid = view.cards_canvas.canvasy(0) + (view.cards_canvas.winfo_height() / 2)
        errors.append(abs(canvas_mid - anchor))

    assert max(errors) <= 4
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


def test_app_ctrl_f_focuses_search_on_active_schedule_tab(monkeypatch) -> None:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display not available in test environment.")
        return

    monkeypatch.setattr("mission_manager.ui.app.DashboardService", lambda: _FakeService())
    app = MissionManagerApp(root)
    root.update_idletasks()
    focus_calls = {"transfer": 0, "schedule": 0}

    def _mark_transfer_focus() -> None:
        focus_calls["transfer"] += 1

    def _mark_schedule_focus() -> None:
        focus_calls["schedule"] += 1

    monkeypatch.setattr(app.transfer_view, "focus_search", _mark_transfer_focus)
    monkeypatch.setattr(app.schedule_text_view, "focus_search", _mark_schedule_focus)

    app.notebook.select(app.transfer_view)
    handled = app._focus_transfer_search(None)  # type: ignore[arg-type]
    assert handled == "break"
    assert focus_calls["transfer"] == 1
    assert focus_calls["schedule"] == 0

    app.notebook.select(app.schedule_text_view)
    handled = app._focus_transfer_search(None)  # type: ignore[arg-type]
    assert handled == "break"
    assert focus_calls["transfer"] == 1
    assert focus_calls["schedule"] == 1

    app.notebook.select(app.dashboard_view)
    handled = app._focus_transfer_search(None)  # type: ignore[arg-type]
    assert handled is None
    assert focus_calls["transfer"] == 1
    assert focus_calls["schedule"] == 1
    root.destroy()


def test_app_refresh_schedule_outputs_passes_people_to_schedule_text_view(monkeypatch) -> None:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display not available in test environment.")
        return

    fake_service = _FakeService()
    fake_service.people = [_person_row("person-1", "Mina", "Cho", title="S")]
    fake_service.schedule_blocks = [
        _block("block-1", "person-1", "Mina Cho\n---------------", 1)
    ]
    monkeypatch.setattr("mission_manager.ui.app.DashboardService", lambda: fake_service)
    app = MissionManagerApp(root)
    captured: dict[str, list | None] = {"people": None}

    original_set_schedule = app.schedule_text_view.set_schedule

    def _capture_set_schedule(blocks, note=None, people=None):
        captured["people"] = people
        return original_set_schedule(blocks, note=note, people=people)

    monkeypatch.setattr(app.schedule_text_view, "set_schedule", _capture_set_schedule)
    app.refresh_schedule_outputs()
    assert captured["people"] == fake_service.people
    root.destroy()


def test_schedule_text_missionary_mode_does_not_change_transfer_editor_cards(monkeypatch) -> None:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display not available in test environment.")
        return

    fake_service = _FakeService()
    fake_service.people = [_person_row("person-1", "John", "Kim", title="E")]
    fake_service.schedule_blocks = [
        _block("block-1", "person-1", "John Kim\n---------------", 1)
    ]
    monkeypatch.setattr("mission_manager.ui.app.DashboardService", lambda: fake_service)
    app = MissionManagerApp(root)
    root.update_idletasks()

    app.schedule_text_view._set_name_mode("missionary")
    schedule_rendered = app.schedule_text_view.text_widget.get("1.0", "end-1c")
    assert "Elder Kim" in schedule_rendered

    assert app.transfer_view._ordered_block_ids
    first_block_id = app.transfer_view._ordered_block_ids[0]
    transfer_text = app.transfer_view._block_text_widgets[first_block_id].get("1.0", "end-1c")
    assert "John Kim" in transfer_text
    assert "Elder Kim" not in transfer_text
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
    assert fake_service.schedule_build_calls == 1
    assert "Mina Cho" in app.schedule_text_view.text_widget.get("1.0", "end-1c")
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
    assert fake_service.schedule_build_calls == 1
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


def test_clear_data_clears_transfer_and_schedule_text(monkeypatch) -> None:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display not available in test environment.")
        return

    fake_service = _FakeService()
    fake_service.people = [_person_row("person-1", "Mina", "Cho")]
    fake_service.schedule_blocks = [_block("block-1", "person-1", "ALPHA\n-----------------------------------", 1)]
    monkeypatch.setattr("mission_manager.ui.app.DashboardService", lambda: fake_service)
    monkeypatch.setattr("mission_manager.ui.app.ask_confirm", lambda *_args, **_kwargs: True)
    app = MissionManagerApp(root)
    root.update_idletasks()

    assert app.transfer_view._ordered_block_ids
    assert "ALPHA" in app.schedule_text_view.text_widget.get("1.0", "end-1c")

    app.clear_data()
    root.update_idletasks()

    assert not app.transfer_view._ordered_block_ids
    assert "No schedule text available." in app.schedule_text_view.text_widget.get("1.0", "end-1c")
    root.destroy()


def test_replace_data_success_auto_regenerates_transfer_and_schedule_text(monkeypatch) -> None:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display not available in test environment.")
        return

    fake_service = _FakeService()
    fake_service.people = [_person_row("person-1", "Mina", "Cho")]
    fake_service.schedule_blocks = [_block("block-1", "person-1", "ALPHA\n-----------------------------------", 1)]
    monkeypatch.setattr("mission_manager.ui.app.DashboardService", lambda: fake_service)
    monkeypatch.setattr("mission_manager.ui.app.ask_confirm", lambda *_args, **_kwargs: True)
    monkeypatch.setattr("mission_manager.ui.app.pick_excel_file", lambda: "fake.xlsx")
    app = MissionManagerApp(root)
    root.update_idletasks()

    assert app.transfer_view._ordered_block_ids
    assert "ALPHA" in app.schedule_text_view.text_widget.get("1.0", "end-1c")

    app.replace_data()
    root.update_idletasks()

    assert app.transfer_view._ordered_block_ids
    assert "Replace One" in app.schedule_text_view.text_widget.get("1.0", "end-1c")
    assert "ALPHA" not in app.schedule_text_view.text_widget.get("1.0", "end-1c")
    assert fake_service.schedule_build_calls == 1
    root.destroy()


def test_replace_data_failure_keeps_existing_transfer_outputs(monkeypatch) -> None:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display not available in test environment.")
        return

    fake_service = _FakeService()
    fake_service.people = [_person_row("person-1", "Mina", "Cho")]
    fake_service.schedule_blocks = [_block("block-1", "person-1", "ALPHA\n-----------------------------------", 1)]
    fake_service.replace_should_fail = True
    monkeypatch.setattr("mission_manager.ui.app.DashboardService", lambda: fake_service)
    monkeypatch.setattr("mission_manager.ui.app.ask_confirm", lambda *_args, **_kwargs: True)
    monkeypatch.setattr("mission_manager.ui.app.pick_excel_file", lambda: "fake.xlsx")
    monkeypatch.setattr("mission_manager.ui.app.show_error", lambda *_args, **_kwargs: None)
    app = MissionManagerApp(root)
    root.update_idletasks()

    before_text = app.schedule_text_view.text_widget.get("1.0", "end-1c")
    before_blocks = list(app.transfer_view._ordered_block_ids)

    app.replace_data()
    root.update_idletasks()

    after_text = app.schedule_text_view.text_widget.get("1.0", "end-1c")
    assert before_blocks == app.transfer_view._ordered_block_ids
    assert before_text == after_text
    root.destroy()


def test_import_and_append_auto_regenerate_schedule_outputs(monkeypatch) -> None:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display not available in test environment.")
        return

    fake_service = _FakeService()
    monkeypatch.setattr("mission_manager.ui.app.DashboardService", lambda: fake_service)
    monkeypatch.setattr("mission_manager.ui.app.pick_excel_file", lambda: "fake.xlsx")
    app = MissionManagerApp(root)
    root.update_idletasks()

    app.import_initial()
    root.update_idletasks()
    assert fake_service.schedule_build_calls == 1
    assert "Import One" in app.schedule_text_view.text_widget.get("1.0", "end-1c")

    app.append_data()
    root.update_idletasks()
    assert fake_service.schedule_build_calls == 2
    rendered = app.schedule_text_view.text_widget.get("1.0", "end-1c")
    assert "Import One" in rendered
    assert "Append 2" in rendered
    root.destroy()


def test_auto_regen_failure_after_apply_preserves_existing_schedule_outputs(monkeypatch) -> None:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter display not available in test environment.")
        return

    fake_service = _FakeService()
    fake_service.people = [_person_row("person-1", "Mina", "Cho")]
    fake_service.schedule_blocks = [_block("block-1", "person-1", "LEGACY\n-----------------------------------", 1)]
    fake_service.auto_schedule_should_fail = True
    monkeypatch.setattr("mission_manager.ui.app.DashboardService", lambda: fake_service)
    monkeypatch.setattr("mission_manager.ui.app.show_error", lambda *_args, **_kwargs: None)
    app = MissionManagerApp(root)
    root.update_idletasks()

    before_blocks = list(app.transfer_view._ordered_block_ids)
    before_text = app.schedule_text_view.text_widget.get("1.0", "end-1c")
    app.open_detail("person-1")
    app.apply_detail("person-1", {"first_name": "Updated"})
    root.update_idletasks()

    assert fake_service.get_person("person-1").first_name == "Updated"
    assert before_blocks == app.transfer_view._ordered_block_ids
    assert before_text == app.schedule_text_view.text_widget.get("1.0", "end-1c")
    assert fake_service.schedule_build_calls == 1
    root.destroy()
