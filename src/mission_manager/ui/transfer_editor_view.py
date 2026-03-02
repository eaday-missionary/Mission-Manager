"""Transfer editor schedule and conflict review view."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from mission_manager.models import ScheduleBlock, ScheduleConflict


class TransferEditorView(ttk.Frame):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, padding=12)
        self.columnconfigure(0, weight=3)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)
        self.on_open_person = None

        self.status_var = tk.StringVar(value="No schedule loaded.")
        ttk.Label(self, text="Transfer Editor", style="Title.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 8)
        )
        ttk.Label(self, textvariable=self.status_var).grid(
            row=0, column=1, sticky="e", pady=(0, 8)
        )

        search_controls = ttk.Frame(self)
        search_controls.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        search_controls.columnconfigure(1, weight=1)
        ttk.Label(search_controls, text="Search").grid(row=0, column=0, sticky="w", padx=(0, 6))
        self._search_query = tk.StringVar(value="")
        self.search_entry = ttk.Entry(search_controls, textvariable=self._search_query, width=36)
        self.search_entry.grid(row=0, column=1, sticky="ew")
        self._search_status_var = tk.StringVar(value="0 matches")
        ttk.Label(search_controls, textvariable=self._search_status_var).grid(
            row=0, column=2, sticky="e", padx=(8, 0)
        )
        self.search_entry.bind("<KeyRelease>", self._on_search_key_release)
        self.search_entry.bind("<Down>", self._on_search_next)
        self.search_entry.bind("<Up>", self._on_search_previous)
        self.search_entry.bind("<Return>", self._on_search_next)
        self.search_entry.bind("<Shift-Return>", self._on_search_previous)

        left = ttk.Frame(self)
        left.grid(row=2, column=0, sticky="nsew", padx=(0, 8))
        left.rowconfigure(0, weight=1)
        left.columnconfigure(0, weight=1)

        self.cards_canvas = tk.Canvas(
            left,
            bg="#131923",
            highlightthickness=1,
            highlightbackground="#2E3745",
            highlightcolor="#2E3745",
            borderwidth=0,
        )
        self.cards_canvas.grid(row=0, column=0, sticky="nsew")
        cards_scroll = ttk.Scrollbar(
            left,
            orient="vertical",
            command=self.cards_canvas.yview,
            style="App.Vertical.TScrollbar",
        )
        cards_scroll.grid(row=0, column=1, sticky="ns")
        self.cards_canvas.configure(yscrollcommand=cards_scroll.set)

        self.cards_frame = ttk.Frame(self.cards_canvas)
        self._cards_window = self.cards_canvas.create_window((0, 0), window=self.cards_frame, anchor="nw")
        self.cards_frame.bind("<Configure>", self._on_cards_frame_configure)
        self.cards_canvas.bind("<Configure>", self._on_cards_canvas_configure)

        right = ttk.Frame(self)
        right.grid(row=2, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)
        ttk.Label(right, text="Conflicts").grid(row=0, column=0, sticky="w")

        self.conflict_list = tk.Listbox(
            right,
            activestyle="none",
            bg="#131923",
            fg="#F8FAFC",
            selectbackground="#F59E0B",
            selectforeground="#111827",
            relief="flat",
            borderwidth=0,
            highlightthickness=1,
            highlightbackground="#2E3745",
            highlightcolor="#2E3745",
        )
        self.conflict_list.grid(row=1, column=0, sticky="nsew")
        conflict_scroll = ttk.Scrollbar(
            right,
            orient="vertical",
            command=self.conflict_list.yview,
            style="App.Vertical.TScrollbar",
        )
        conflict_scroll.grid(row=1, column=1, sticky="ns")
        self.conflict_list.configure(yscrollcommand=conflict_scroll.set)
        self.conflict_list.bind("<<ListboxSelect>>", self._on_conflict_selected)

        self._conflicts: list[ScheduleConflict] = []
        self._conflict_ranges: dict[int, list[tuple[str, str, str]]] = {}
        self._search_matches: list[tuple[str, str, str]] = []
        self._active_search_match_index: int | None = None
        self._block_text_widgets: dict[str, tk.Text] = {}
        self._block_frames: dict[str, ttk.Frame] = {}
        self._block_person_ids: dict[str, str] = {}
        self._ordered_block_ids: list[str] = []
        self._placeholder_label: ttk.Label | None = None
        self._cards_scrollregion_after_id: str | None = None
        self._top_spacer: tk.Frame | None = None
        self._bottom_spacer: tk.Frame | None = None
        self._centering_spacer_height: int | None = None

        self._create_centering_spacers()

        self._bind_cards_scroll_events_recursive(self.cards_canvas)
        self._bind_cards_scroll_events_recursive(self.cards_frame)

    def show_loading(self, message: str = "Loading transfer schedule...") -> None:
        self.status_var.set(message)
        self._reset_search_state(clear_query=True)
        self._render_placeholder(message)
        self.conflict_list.delete(0, "end")
        self._conflicts = []
        self._conflict_ranges = {}

    def show_error(self, message: str) -> None:
        self.status_var.set("Error")
        self._reset_search_state(clear_query=True)
        self._render_placeholder(message)
        self.conflict_list.delete(0, "end")
        self._conflicts = []
        self._conflict_ranges = {}

    def set_schedule(
        self, blocks: list[ScheduleBlock], conflicts: list[ScheduleConflict], note: str | None = None
    ) -> None:
        if not blocks:
            self.status_var.set(note or "No schedule available.")
            self._reset_search_state(clear_query=True)
            self._render_placeholder("No schedule exists yet. Run Create Schedule from the Dashboard.")
            self.conflict_list.delete(0, "end")
            self._conflicts = []
            self._conflict_ranges = {}
            return

        self.status_var.set(note or f"{len(blocks)} schedule blocks")
        self._conflicts = conflicts
        self._render_document(blocks)
        self._render_conflicts(conflicts)
        self._apply_conflict_tags(conflicts)
        self._refresh_search_matches()

    def focus_search(self) -> None:
        self.search_entry.focus_set()
        self.search_entry.selection_range(0, "end")
        self.search_entry.icursor("end")

    def _render_placeholder(self, text: str) -> None:
        self._clear_cards()
        self._placeholder_label = ttk.Label(self.cards_frame, text=text, wraplength=760)
        self._placeholder_label.grid(row=1, column=0, sticky="w")
        if self._bottom_spacer:
            self._bottom_spacer.grid(row=2, column=0, sticky="ew")
        self.cards_frame.columnconfigure(0, weight=1)
        self._bind_cards_scroll_events_recursive(self._placeholder_label)
        self._schedule_cards_scrollregion_update()

    def _clear_cards(self) -> None:
        for child in self.cards_frame.winfo_children():
            child.destroy()
        self._create_centering_spacers()
        self._block_text_widgets = {}
        self._block_frames = {}
        self._block_person_ids = {}
        self._ordered_block_ids = []
        self._placeholder_label = None

    def _render_document(self, blocks: list[ScheduleBlock]) -> None:
        self._clear_cards()
        self.cards_frame.columnconfigure(0, weight=1)

        row = 1
        for block in sorted(blocks, key=lambda b: b.render_order):
            if block.block_kind == "zone_header":
                zone_label = ttk.Label(
                    self.cards_frame,
                    text=block.raw_text,
                    foreground="#9CC0FF",
                )
                zone_label.grid(row=row, column=0, sticky="w", pady=(0, 6))
                self._bind_cards_scroll_events_recursive(zone_label)
                row += 1
                continue

            if block.block_kind == "area_header":
                area_label = ttk.Label(
                    self.cards_frame,
                    text=block.raw_text,
                    foreground="#CFE2FF",
                )
                area_label.grid(row=row, column=0, sticky="w", pady=(0, 6))
                self._bind_cards_scroll_events_recursive(area_label)
                row += 1
                continue

            card = ttk.Frame(self.cards_frame, style="Card.TFrame", padding=8)
            card.grid(row=row, column=0, sticky="ew", pady=(0, 8))
            card.columnconfigure(0, weight=1)

            title = ttk.Label(card, text=block.person_display_name or "-", style="Info.TLabel")
            title.grid(row=0, column=0, sticky="w", pady=(0, 4))

            block_text = block.raw_text.rstrip("\n")
            text_widget = tk.Text(
                card,
                wrap="word",
                state="normal",
                bg="#131923",
                fg="#F8FAFC",
                insertbackground="#F8FAFC",
                selectbackground="#334155",
                selectforeground="#F8FAFC",
                relief="flat",
                borderwidth=0,
                highlightthickness=1,
                highlightbackground="#2E3745",
                highlightcolor="#2E3745",
                height=max(4, block_text.count("\n") + 1),
            )
            text_widget.grid(row=1, column=0, sticky="ew")
            text_widget.insert("1.0", block_text)
            self._configure_text_tags(text_widget)
            text_widget.configure(state="disabled")

            card.bind(
                "<Double-1>",
                lambda _e, person_id=block.person_id: self._open_person(person_id),
            )
            title.bind(
                "<Double-1>",
                lambda _e, person_id=block.person_id: self._open_person(person_id),
            )
            text_widget.bind(
                "<Double-1>",
                lambda _e, person_id=block.person_id: self._open_person(person_id),
            )
            self._bind_cards_scroll_events_recursive(card)

            self._block_frames[block.block_id] = card
            self._block_text_widgets[block.block_id] = text_widget
            if block.person_id:
                self._block_person_ids[block.block_id] = block.person_id
            self._ordered_block_ids.append(block.block_id)
            row += 1

        if self._bottom_spacer:
            self._bottom_spacer.grid(row=row, column=0, sticky="ew")
        self._schedule_cards_scrollregion_update()

    def _configure_text_tags(self, widget: tk.Text) -> None:
        widget.tag_configure("conflict_red", background="#4A1F1F", foreground="#FFD9D9")
        widget.tag_configure("conflict_yellow", background="#4D4214", foreground="#FFF6C2")
        widget.tag_configure("conflict_active", background="#F59E0B", foreground="#111827")
        widget.tag_configure("search_match_all", background="#87CEFA", foreground="#0B1220")
        widget.tag_configure("search_match_active", background="#40E0D0", foreground="#0B1220")

    def _render_conflicts(self, conflicts: list[ScheduleConflict]) -> None:
        self.conflict_list.delete(0, "end")
        self._conflict_ranges = {}
        if not conflicts:
            self.conflict_list.insert("end", "No conflicts detected.")
            self.conflict_list.itemconfig(0, fg="#94A3B8")
            return

        for idx, conflict in enumerate(conflicts):
            label = f"[{conflict.conflict_type}] {conflict.message}"
            self.conflict_list.insert("end", label)
            color = "#F87171" if conflict.severity == "red" else "#FACC15"
            self.conflict_list.itemconfig(idx, fg=color)

    def _apply_conflict_tags(self, conflicts: list[ScheduleConflict]) -> None:
        for widget in self._block_text_widgets.values():
            widget.tag_remove("conflict_red", "1.0", "end")
            widget.tag_remove("conflict_yellow", "1.0", "end")
            widget.tag_remove("conflict_active", "1.0", "end")

        self._conflict_ranges = {}
        for idx, conflict in enumerate(conflicts):
            tag = "conflict_red" if conflict.severity == "red" else "conflict_yellow"
            ranges: list[tuple[str, str, str]] = []
            for anchor in conflict.anchors:
                widget = self._block_text_widgets.get(anchor.block_id)
                if not widget:
                    continue
                start_line = max(anchor.line_start, 1)
                end_line = max(anchor.line_end, start_line)
                start_idx = f"{start_line}.0"
                end_idx = f"{end_line}.end"
                widget.tag_add(tag, start_idx, end_idx)
                ranges.append((anchor.block_id, start_idx, end_idx))
            self._conflict_ranges[idx] = ranges

        self._apply_search_tags()

    def _on_conflict_selected(self, _event: tk.Event | None = None) -> None:
        selection = self.conflict_list.curselection()
        if not selection:
            return
        idx = selection[0]
        if idx >= len(self._conflicts):
            return

        for widget in self._block_text_widgets.values():
            widget.tag_remove("conflict_active", "1.0", "end")

        ranges = self._conflict_ranges.get(idx) or []
        if ranges:
            first_block_id, first_start, _ = ranges[0]
            for block_id, start_idx, end_idx in ranges:
                widget = self._block_text_widgets.get(block_id)
                if not widget:
                    continue
                widget.tag_add("conflict_active", start_idx, end_idx)
            self._scroll_to_block(first_block_id, first_start)

        self._apply_search_tags()

    def _on_search_key_release(self, event: tk.Event) -> None:
        if event.keysym in {"Up", "Down", "Return"}:
            return
        self._refresh_search_matches()

    def _on_search_next(self, _event: tk.Event) -> str:
        self._goto_next_match()
        return "break"

    def _on_search_previous(self, _event: tk.Event) -> str:
        self._goto_previous_match()
        return "break"

    def _refresh_search_matches(self) -> None:
        query = self._search_query.get().strip()
        self._search_matches = []
        self._active_search_match_index = None
        self._clear_search_tags()

        if not query:
            self._update_search_status()
            return

        query_length = len(query)
        for block_id in self._ordered_block_ids:
            widget = self._block_text_widgets.get(block_id)
            if not widget:
                continue
            cursor = "1.0"
            while True:
                start_idx = widget.search(query, cursor, stopindex="end", nocase=True)
                if not start_idx:
                    break
                end_idx = f"{start_idx}+{query_length}c"
                self._search_matches.append((block_id, start_idx, end_idx))
                cursor = end_idx

        if self._search_matches:
            self._active_search_match_index = 0
            self._apply_search_tags()
            block_id, start_idx, _ = self._search_matches[0]
            self._scroll_to_block(block_id, start_idx)

        self._update_search_status()

    def _goto_next_match(self) -> None:
        if not self._search_matches:
            return
        if self._active_search_match_index is None:
            self._set_active_search_match(0)
            return
        next_idx = (self._active_search_match_index + 1) % len(self._search_matches)
        self._set_active_search_match(next_idx)

    def _goto_previous_match(self) -> None:
        if not self._search_matches:
            return
        if self._active_search_match_index is None:
            self._set_active_search_match(len(self._search_matches) - 1)
            return
        prev_idx = (self._active_search_match_index - 1) % len(self._search_matches)
        self._set_active_search_match(prev_idx)

    def _set_active_search_match(self, index: int) -> None:
        if not self._search_matches:
            return
        self._active_search_match_index = index
        self._apply_search_tags()
        block_id, start_idx, _ = self._search_matches[index]
        self._scroll_to_block(block_id, start_idx)
        self._update_search_status()

    def _apply_search_tags(self) -> None:
        self._clear_search_tags()
        for block_id, start_idx, end_idx in self._search_matches:
            widget = self._block_text_widgets.get(block_id)
            if not widget:
                continue
            widget.tag_add("search_match_all", start_idx, end_idx)
            widget.tag_raise("search_match_all")
        if self._active_search_match_index is not None and self._search_matches:
            block_id, start_idx, end_idx = self._search_matches[self._active_search_match_index]
            widget = self._block_text_widgets.get(block_id)
            if widget:
                widget.tag_add("search_match_active", start_idx, end_idx)
                widget.tag_raise("search_match_active")

    def _clear_search_tags(self) -> None:
        for widget in self._block_text_widgets.values():
            widget.tag_remove("search_match_all", "1.0", "end")
            widget.tag_remove("search_match_active", "1.0", "end")

    def _reset_search_state(self, *, clear_query: bool) -> None:
        if clear_query:
            self._search_query.set("")
        self._search_matches = []
        self._active_search_match_index = None
        self._clear_search_tags()
        self._update_search_status()

    def _update_search_status(self) -> None:
        total = len(self._search_matches)
        if total == 0:
            self._search_status_var.set("0 matches")
            return
        if self._active_search_match_index is None:
            self._search_status_var.set(f"{total} matches")
            return
        self._search_status_var.set(f"{self._active_search_match_index + 1}/{total}")

    def _scroll_to_block(self, block_id: str, text_index: str | None = None) -> None:
        frame = self._block_frames.get(block_id)
        widget = self._block_text_widgets.get(block_id)
        if not frame:
            return
        self._ensure_cards_geometry_ready()
        if widget and text_index:
            widget.see(text_index)
            widget.update_idletasks()
        anchor_y = self._resolve_anchor_canvas_y(frame, widget, text_index)
        if anchor_y is None:
            return
        self._center_anchor_in_view(anchor_y)
        self._ensure_cards_geometry_ready()
        if widget and text_index:
            widget.see(text_index)
            widget.update_idletasks()
        corrected_anchor_y = self._resolve_anchor_canvas_y(frame, widget, text_index)
        if corrected_anchor_y is None:
            return
        viewport_height = max(self.cards_canvas.winfo_height(), 1)
        canvas_top = self.cards_canvas.canvasy(0)
        viewport_mid = canvas_top + (viewport_height / 2)
        error = corrected_anchor_y - viewport_mid
        if abs(error) > 2.0:
            self._move_canvas_top_to(canvas_top + error)
            self._ensure_cards_geometry_ready()

    def _open_person(self, person_id: str) -> None:
        if self.on_open_person:
            self.on_open_person(person_id)

    def _on_cards_frame_configure(self, _event: tk.Event | None) -> None:
        self._schedule_cards_scrollregion_update()

    def _on_cards_canvas_configure(self, event: tk.Event) -> None:
        self.cards_canvas.itemconfigure(self._cards_window, width=event.width)
        self._update_centering_spacers(event.height)
        self._schedule_cards_scrollregion_update()

    def _on_cards_mouse_wheel(self, event: tk.Event) -> str:
        if event.delta:
            self.cards_canvas.yview_scroll(int(-event.delta / 120), "units")
        return "break"

    def _on_cards_mouse_wheel_linux(self, event: tk.Event) -> str:
        if event.num == 4:
            self.cards_canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.cards_canvas.yview_scroll(1, "units")
        return "break"

    def _bind_cards_scroll_events_recursive(self, widget: tk.Misc) -> None:
        widget.bind("<MouseWheel>", self._on_cards_mouse_wheel)
        widget.bind("<Button-4>", self._on_cards_mouse_wheel_linux)
        widget.bind("<Button-5>", self._on_cards_mouse_wheel_linux)
        for child in widget.winfo_children():
            self._bind_cards_scroll_events_recursive(child)

    def _schedule_cards_scrollregion_update(self) -> None:
        if self._cards_scrollregion_after_id is not None:
            return
        self._cards_scrollregion_after_id = self.cards_canvas.after_idle(
            self._refresh_cards_scrollregion
        )

    def _refresh_cards_scrollregion(self) -> None:
        self._cards_scrollregion_after_id = None
        self.cards_canvas.configure(scrollregion=self.cards_canvas.bbox("all"))

    def _ensure_cards_geometry_ready(self) -> None:
        if self._cards_scrollregion_after_id is not None:
            self.cards_canvas.after_cancel(self._cards_scrollregion_after_id)
            self._cards_scrollregion_after_id = None
        self.cards_canvas.update_idletasks()
        self.cards_frame.update_idletasks()
        self._update_centering_spacers()
        self._refresh_cards_scrollregion()
        self.cards_canvas.update_idletasks()
        self.cards_frame.update_idletasks()

    def _create_centering_spacers(self) -> None:
        self.cards_frame.columnconfigure(0, weight=1)
        self._top_spacer = tk.Frame(
            self.cards_frame,
            bg="#131923",
            borderwidth=0,
            highlightthickness=0,
        )
        self._bottom_spacer = tk.Frame(
            self.cards_frame,
            bg="#131923",
            borderwidth=0,
            highlightthickness=0,
        )
        self._top_spacer.grid(row=0, column=0, sticky="ew")
        self._bottom_spacer.grid(row=1, column=0, sticky="ew")
        self._centering_spacer_height = None
        self._update_centering_spacers()

    def _update_centering_spacers(self, viewport_height: int | None = None) -> None:
        if not self._top_spacer or not self._bottom_spacer:
            return
        if viewport_height is None:
            viewport_height = max(self.cards_canvas.winfo_height(), 0)
        spacer_height = max(int(viewport_height / 2), 0)
        if spacer_height == self._centering_spacer_height:
            return
        self._centering_spacer_height = spacer_height
        self._top_spacer.configure(height=spacer_height)
        self._bottom_spacer.configure(height=spacer_height)

    def _resolve_anchor_canvas_y(
        self,
        frame: ttk.Frame,
        widget: tk.Text | None,
        text_index: str | None,
    ) -> float | None:
        coords = self.cards_canvas.coords(self._cards_window)
        cards_window_y = coords[1] if len(coords) >= 2 else 0.0
        frame_top = frame.winfo_y()
        if widget and text_index:
            try:
                line_info = widget.dlineinfo(text_index)
            except tk.TclError:
                line_info = None
            if line_info:
                return (
                    cards_window_y
                    + frame_top
                    + widget.winfo_y()
                    + line_info[1]
                    + (line_info[3] / 2)
                )
        frame_height = max(frame.winfo_height(), 1)
        return cards_window_y + frame_top + (frame_height / 2)

    def _center_anchor_in_view(self, anchor_canvas_y: float) -> None:
        viewport_height = max(self.cards_canvas.winfo_height(), 1)
        target_top = anchor_canvas_y - (viewport_height / 2)
        self._move_canvas_top_to(target_top)

    def _move_canvas_top_to(self, target_top: float) -> None:
        region = self.cards_canvas.bbox("all")
        if not region:
            return
        region_top = region[1]
        total_height = region[3] - region[1]
        if total_height <= 0:
            return
        fraction = min(max((target_top - region_top) / total_height, 0.0), 1.0)
        self.cards_canvas.yview_moveto(fraction)

    def _is_anchor_centered(self, anchor_canvas_y: float, tolerance: float = 2.0) -> bool:
        viewport_height = max(self.cards_canvas.winfo_height(), 1)
        viewport_mid = self.cards_canvas.canvasy(0) + (viewport_height / 2)
        return abs(anchor_canvas_y - viewport_mid) <= tolerance
