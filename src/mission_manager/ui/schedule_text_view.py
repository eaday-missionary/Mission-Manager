"""Schedule text aggregation view."""

from __future__ import annotations

import re
import tkinter as tk
from tkinter import ttk
from typing import Literal

from mission_manager.models import PersonRecord, ScheduleBlock


class ScheduleTextView(ttk.Frame):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, padding=12)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        self.status_var = tk.StringVar(value="No schedule loaded.")
        ttk.Label(self, text="Schedule Text", style="Title.TLabel").grid(
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

        text_frame = ttk.Frame(self)
        text_frame.grid(row=2, column=0, columnspan=2, sticky="nsew")
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)

        self.text_widget = tk.Text(
            text_frame,
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
        self.text_widget.grid(row=0, column=0, sticky="nsew")
        self.text_widget.tag_configure("search_match_all", background="#87CEFA", foreground="#0B1220")
        self.text_widget.tag_configure("search_match_active", background="#40E0D0", foreground="#0B1220")

        scroll = ttk.Scrollbar(
            text_frame,
            orient="vertical",
            command=self.text_widget.yview,
            style="App.Vertical.TScrollbar",
        )
        scroll.grid(row=0, column=1, sticky="ns")
        self.text_widget.configure(yscrollcommand=scroll.set)

        mode_controls = ttk.Frame(self)
        mode_controls.grid(row=3, column=0, columnspan=2, sticky="e", pady=(10, 0))
        self.original_names_btn = ttk.Button(
            mode_controls,
            text="Original Names",
            command=lambda: self._set_name_mode("original"),
            style="ModeActive.TButton",
        )
        self.original_names_btn.pack(side="left", padx=(0, 8))
        self.missionary_titles_btn = ttk.Button(
            mode_controls,
            text="Missionary Titles",
            command=lambda: self._set_name_mode("missionary"),
            style="Mode.TButton",
        )
        self.missionary_titles_btn.pack(side="left")

        self._search_matches: list[tuple[str, str]] = []
        self._active_search_match_index: int | None = None
        self._name_mode: Literal["original", "missionary"] = "original"
        self._current_blocks: list[ScheduleBlock] = []
        self._current_people: list[PersonRecord] = []

    def focus_search(self) -> None:
        self.search_entry.focus_set()
        self.search_entry.selection_range(0, "end")
        self.search_entry.icursor("end")

    def show_loading(self, message: str = "Loading schedule text...") -> None:
        self._current_blocks = []
        self._current_people = []
        self.status_var.set(message)
        self._set_text(message)
        self._reset_search_state(clear_query=True)

    def show_error(self, message: str) -> None:
        self._current_blocks = []
        self._current_people = []
        self.status_var.set("Error")
        self._set_text(message)
        self._reset_search_state(clear_query=True)

    def set_schedule(
        self,
        blocks: list[ScheduleBlock],
        note: str | None = None,
        people: list[PersonRecord] | None = None,
    ) -> None:
        if not blocks:
            self._current_blocks = []
            self._current_people = list(people or [])
            self.status_var.set(note or "No schedule available.")
            self._set_text("No schedule text available. Run Create Schedule from Dashboard.")
            self._reset_search_state(clear_query=True)
            return

        self._current_blocks = list(blocks)
        self._current_people = list(people or [])
        self.status_var.set(note or f"{len(self._current_blocks)} schedule blocks")
        self._render_schedule_text()

    def _set_text(self, content: str) -> None:
        self.text_widget.configure(state="normal")
        self.text_widget.delete("1.0", "end")
        self.text_widget.insert("1.0", content)
        self.text_widget.configure(state="disabled")

    def _set_name_mode(self, mode: Literal["original", "missionary"]) -> None:
        if mode == self._name_mode:
            return
        self._name_mode = mode
        self._refresh_name_mode_buttons()
        if self._current_blocks:
            self._render_schedule_text()

    def _refresh_name_mode_buttons(self) -> None:
        if self._name_mode == "original":
            self.original_names_btn.configure(style="ModeActive.TButton")
            self.missionary_titles_btn.configure(style="Mode.TButton")
            return
        self.original_names_btn.configure(style="Mode.TButton")
        self.missionary_titles_btn.configure(style="ModeActive.TButton")

    def _render_schedule_text(self) -> None:
        ordered = sorted(self._current_blocks, key=lambda b: b.render_order)
        replacements: list[tuple[re.Pattern[str], str]] = []
        if self._name_mode == "missionary":
            replacements = self._build_name_replacements(self._current_people)

        rendered_blocks: list[str] = []
        for block in ordered:
            block_text = block.raw_text.rstrip("\n")
            if self._name_mode == "missionary" and block.block_kind == "person":
                block_text = self._replace_full_names(block_text, replacements)
            rendered_blocks.append(block_text)

        combined = "\n".join(rendered_blocks).strip()
        self._set_text(combined)
        self._refresh_search_matches()

    def _build_name_replacements(self, people: list[PersonRecord]) -> list[tuple[re.Pattern[str], str]]:
        if not people:
            return []

        last_name_counts: dict[str, int] = {}
        for person in people:
            last_name = (person.last_name or "").strip()
            if not last_name:
                continue
            key = last_name.casefold()
            last_name_counts[key] = last_name_counts.get(key, 0) + 1

        entries: list[tuple[str, re.Pattern[str], str]] = []
        seen_names: set[str] = set()
        for person in people:
            first_name = (person.first_name or "").strip()
            last_name = (person.last_name or "").strip()
            if not first_name or not last_name:
                continue

            full_name = f"{first_name} {last_name}"
            full_name_key = full_name.casefold()
            if full_name_key in seen_names:
                continue
            seen_names.add(full_name_key)

            title_word = self._title_word(person.title)
            shared_last_name = last_name_counts.get(last_name.casefold(), 0) > 1
            if shared_last_name:
                replacement = f"{title_word} {first_name} {last_name}"
            else:
                replacement = f"{title_word} {last_name}"

            pattern = re.compile(
                rf"(?<!\w){re.escape(full_name)}(?!\w)",
                re.IGNORECASE,
            )
            entries.append((full_name, pattern, replacement))

        entries.sort(key=lambda item: (-len(item[0]), item[0].casefold()))
        return [(pattern, replacement) for _, pattern, replacement in entries]

    def _replace_full_names(self, text: str, replacements: list[tuple[re.Pattern[str], str]]) -> str:
        rendered = text
        for pattern, replacement in replacements:
            rendered = pattern.sub(replacement, rendered)
        return rendered

    def _title_word(self, title: str | None) -> str:
        normalized = (title or "").strip().upper()
        if normalized == "E":
            return "Elder"
        if normalized == "S":
            return "Sister"
        return "BLANK"

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

        self.text_widget.configure(state="normal")
        try:
            query_length = len(query)
            cursor = "1.0"
            while True:
                start_idx = self.text_widget.search(query, cursor, stopindex="end", nocase=True)
                if not start_idx:
                    break
                end_idx = f"{start_idx}+{query_length}c"
                self._search_matches.append((start_idx, end_idx))
                cursor = end_idx
        finally:
            self.text_widget.configure(state="disabled")

        if self._search_matches:
            self._active_search_match_index = 0
            self._apply_search_tags()
            start_idx, _ = self._search_matches[0]
            self.text_widget.see(start_idx)

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
        self.text_widget.see(start_idx)
        self._update_search_status()

    def _apply_search_tags(self) -> None:
        self._clear_search_tags()
        self.text_widget.configure(state="normal")
        try:
            for start_idx, end_idx in self._search_matches:
                self.text_widget.tag_add("search_match_all", start_idx, end_idx)
            self.text_widget.tag_raise("search_match_all")
            if self._active_search_match_index is not None and self._search_matches:
                start_idx, end_idx = self._search_matches[self._active_search_match_index]
                self.text_widget.tag_add("search_match_active", start_idx, end_idx)
                self.text_widget.tag_raise("search_match_active")
        finally:
            self.text_widget.configure(state="disabled")

    def _clear_search_tags(self) -> None:
        self.text_widget.configure(state="normal")
        try:
            self.text_widget.tag_remove("search_match_all", "1.0", "end")
            self.text_widget.tag_remove("search_match_active", "1.0", "end")
        finally:
            self.text_widget.configure(state="disabled")

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
