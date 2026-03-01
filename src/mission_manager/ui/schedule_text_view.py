"""Schedule text aggregation view."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from mission_manager.models import ScheduleBlock


class ScheduleTextView(ttk.Frame):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, padding=12)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self.status_var = tk.StringVar(value="No schedule loaded.")
        ttk.Label(self, text="Schedule Text", style="Title.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 8)
        )
        ttk.Label(self, textvariable=self.status_var).grid(
            row=0, column=1, sticky="e", pady=(0, 8)
        )

        text_frame = ttk.Frame(self)
        text_frame.grid(row=1, column=0, columnspan=2, sticky="nsew")
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

        scroll = ttk.Scrollbar(
            text_frame,
            orient="vertical",
            command=self.text_widget.yview,
            style="App.Vertical.TScrollbar",
        )
        scroll.grid(row=0, column=1, sticky="ns")
        self.text_widget.configure(yscrollcommand=scroll.set)

    def show_loading(self, message: str = "Loading schedule text...") -> None:
        self.status_var.set(message)
        self._set_text(message)

    def show_error(self, message: str) -> None:
        self.status_var.set("Error")
        self._set_text(message)

    def set_schedule(self, blocks: list[ScheduleBlock], note: str | None = None) -> None:
        if not blocks:
            self.status_var.set(note or "No schedule available.")
            self._set_text("No schedule text available. Run Create Schedule from Dashboard.")
            return

        ordered = sorted(blocks, key=lambda b: b.render_order)
        self.status_var.set(note or f"{len(ordered)} schedule blocks")
        combined = "\n".join(block.raw_text.rstrip("\n") for block in ordered).strip()
        self._set_text(combined)

    def _set_text(self, content: str) -> None:
        self.text_widget.configure(state="normal")
        self.text_widget.delete("1.0", "end")
        self.text_widget.insert("1.0", content)
        self.text_widget.configure(state="disabled")

