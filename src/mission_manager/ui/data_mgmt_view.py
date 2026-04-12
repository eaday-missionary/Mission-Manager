"""Data management controls view."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class DataManagementView(ttk.Frame):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, padding=12)
        self.on_append = None
        self.on_replace = None
        self.on_clear = None

        ttk.Label(self, text="Data Management", style="Title.TLabel").pack(anchor="w", pady=(0, 8))

        btns = ttk.Frame(self)
        btns.pack(anchor="w", pady=(0, 8))
        ttk.Button(btns, text="Append Spreadsheet", command=self._append).pack(side="left", padx=(0, 8))
        ttk.Button(btns, text="Replace Dataset", command=self._replace).pack(side="left", padx=(0, 8))
        ttk.Button(btns, text="Clear Dataset", command=self._clear).pack(side="left")

        self.status_var = tk.StringVar(value="No dataset loaded")
        ttk.Label(self, textvariable=self.status_var).pack(anchor="w")

    def _append(self) -> None:
        if self.on_append:
            self.on_append()

    def _replace(self) -> None:
        if self.on_replace:
            self.on_replace()

    def _clear(self) -> None:
        if self.on_clear:
            self.on_clear()

    def set_status(self, *, record_count: int, last_imported_at: str | None, source_file_name: str | None) -> None:
        if record_count <= 0:
            self.status_var.set("No dataset loaded")
            return
        self.status_var.set(
            f"Records: {record_count} | Last import: {last_imported_at or '-'} | Source: {source_file_name or '-'}"
        )
