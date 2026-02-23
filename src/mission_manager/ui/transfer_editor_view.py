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

        self.schedule_text = tk.Text(
            left,
            wrap="word",
            state="disabled",
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
        )
        self.schedule_text.grid(row=0, column=0, sticky="nsew")
        y_scroll = ttk.Scrollbar(
            left,
            orient="vertical",
            command=self.schedule_text.yview,
            style="App.Vertical.TScrollbar",
        )
        y_scroll.grid(row=0, column=1, sticky="ns")
        self.schedule_text.configure(yscrollcommand=y_scroll.set)

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

        self.schedule_text.tag_configure("conflict_red", background="#4A1F1F", foreground="#FFD9D9")
        self.schedule_text.tag_configure("conflict_yellow", background="#4D4214", foreground="#FFF6C2")
        self.schedule_text.tag_configure(
            "conflict_active",
            background="#F59E0B",
            foreground="#111827",
        )
        self.schedule_text.tag_configure(
            "search_match_all",
            background="#87CEFA",
            foreground="#0B1220",
        )
        self.schedule_text.tag_configure(
            "search_match_active",
            background="#40E0D0",
            foreground="#0B1220",
        )
        self.schedule_text.tag_configure("zone_header", foreground="#9CC0FF")

        self._conflicts: list[ScheduleConflict] = []
        self._block_line_offsets: dict[str, int] = {}
        self._conflict_ranges: dict[int, list[tuple[str, str]]] = {}
        self._search_matches: list[tuple[str, str]] = []
        self._active_search_match_index: int | None = None

    def show_loading(self, message: str = "Loading transfer schedule...") -> None:
        self.status_var.set(message)
        self._reset_search_state(clear_query=True)
        self._set_text(message)
        self.conflict_list.delete(0, "end")
        self._conflicts = []
        self._conflict_ranges = {}

    def show_error(self, message: str) -> None:
        self.status_var.set("Error")
        self._reset_search_state(clear_query=True)
        self._set_text(message)
        self.conflict_list.delete(0, "end")
        self._conflicts = []
        self._conflict_ranges = {}

    def set_schedule(
        self, blocks: list[ScheduleBlock], conflicts: list[ScheduleConflict], note: str | None = None
    ) -> None:
        if not blocks:
            self.status_var.set(note or "No schedule available.")
            self._reset_search_state(clear_query=True)
            self._set_text("No schedule exists yet. Run Create Schedule from the Dashboard.")
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

    def _set_text(self, text: str) -> None:
        self.schedule_text.configure(state="normal")
        self.schedule_text.delete("1.0", "end")
        self.schedule_text.insert("1.0", text)
        self.schedule_text.configure(state="disabled")

    def _render_document(self, blocks: list[ScheduleBlock]) -> None:
        self.schedule_text.configure(state="normal")
        self.schedule_text.delete("1.0", "end")
        self._block_line_offsets = {}

        current_zone: str | None = None
        line_cursor = 1
        for block in sorted(blocks, key=lambda b: b.render_order):
            zone = (block.current_zone or "-").strip() or "-"
            if zone != current_zone:
                zone_header = f"==={zone}===\n"
                self.schedule_text.insert("end", zone_header, ("zone_header",))
                self.schedule_text.insert("end", "\n")
                line_cursor += zone_header.count("\n") + 1
                current_zone = zone

            self._block_line_offsets[block.block_id] = line_cursor
            block_text = block.raw_text.rstrip("\n")
            self.schedule_text.insert("end", block_text + "\n\n")
            line_cursor += block_text.count("\n") + 2

        self.schedule_text.configure(state="disabled")

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
        self.schedule_text.configure(state="normal")
        self.schedule_text.tag_remove("conflict_red", "1.0", "end")
        self.schedule_text.tag_remove("conflict_yellow", "1.0", "end")
        self.schedule_text.tag_remove("conflict_active", "1.0", "end")
        self._conflict_ranges = {}

        for idx, conflict in enumerate(conflicts):
            tag = "conflict_red" if conflict.severity == "red" else "conflict_yellow"
            ranges: list[tuple[str, str]] = []
            for anchor in conflict.anchors:
                block_start = self._block_line_offsets.get(anchor.block_id)
                if not block_start:
                    continue
                start_line = block_start + max(anchor.line_start - 1, 0)
                end_line = block_start + max(anchor.line_end - 1, 0)
                start_idx = f"{start_line}.0"
                end_idx = f"{end_line}.end"
                self.schedule_text.tag_add(tag, start_idx, end_idx)
                ranges.append((start_idx, end_idx))
            self._conflict_ranges[idx] = ranges

        self._apply_search_tags()
        self.schedule_text.configure(state="disabled")

    def _on_conflict_selected(self, _event: tk.Event | None = None) -> None:
        selection = self.conflict_list.curselection()
        if not selection:
            return
        idx = selection[0]
        if idx >= len(self._conflicts):
            return

        self.schedule_text.configure(state="normal")
        self.schedule_text.tag_remove("conflict_active", "1.0", "end")
        ranges = self._conflict_ranges.get(idx) or []
        if ranges:
            first_start, _ = ranges[0]
            for start_idx, end_idx in ranges:
                self.schedule_text.tag_add("conflict_active", start_idx, end_idx)
            self.schedule_text.see(first_start)
        self._apply_search_tags()
        self.schedule_text.configure(state="disabled")

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
        self.schedule_text.configure(state="normal")
        self.schedule_text.tag_remove("search_match_all", "1.0", "end")
        self.schedule_text.tag_remove("search_match_active", "1.0", "end")
        self.schedule_text.configure(state="disabled")

        if not query:
            self._update_search_status()
            return

        cursor = "1.0"
        query_length = len(query)
        while True:
            start_idx = self.schedule_text.search(query, cursor, stopindex="end", nocase=True)
            if not start_idx:
                break
            end_idx = f"{start_idx}+{query_length}c"
            self._search_matches.append((start_idx, end_idx))
            cursor = end_idx

        if self._search_matches:
            self._active_search_match_index = 0
            self._apply_search_tags()
            first_start, _ = self._search_matches[0]
            self.schedule_text.see(first_start)

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
        start_idx, _ = self._search_matches[index]
        self.schedule_text.see(start_idx)
        self._update_search_status()

    def _apply_search_tags(self) -> None:
        self.schedule_text.configure(state="normal")
        self.schedule_text.tag_remove("search_match_all", "1.0", "end")
        self.schedule_text.tag_remove("search_match_active", "1.0", "end")
        for start_idx, end_idx in self._search_matches:
            self.schedule_text.tag_add("search_match_all", start_idx, end_idx)
        if self._active_search_match_index is not None and self._search_matches:
            start_idx, end_idx = self._search_matches[self._active_search_match_index]
            self.schedule_text.tag_add("search_match_active", start_idx, end_idx)
        self.schedule_text.configure(state="disabled")

    def _reset_search_state(self, *, clear_query: bool) -> None:
        if clear_query:
            self._search_query.set("")
        self._search_matches = []
        self._active_search_match_index = None
        self.schedule_text.configure(state="normal")
        self.schedule_text.tag_remove("search_match_all", "1.0", "end")
        self.schedule_text.tag_remove("search_match_active", "1.0", "end")
        self.schedule_text.configure(state="disabled")
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
