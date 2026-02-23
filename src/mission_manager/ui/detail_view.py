"""Person detail and edit form view."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from mission_manager.constants import FIELD_TO_HEADER, PERSON_FIELDS


class DetailView(ttk.Frame):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, padding=12)
        self.on_apply = None
        self.on_cancel = None
        self.current_person_id = None

        self.entries: dict[str, ttk.Entry] = {}

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        title = ttk.Label(self, text="Person Detail", font=("Segoe UI", 12, "bold"))
        title.grid(row=0, column=0, sticky="w", pady=(0, 8))

        main = ttk.Frame(self)
        main.grid(row=1, column=0, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(0, weight=1)

        content_frame = ttk.Frame(main)
        content_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        content_frame.columnconfigure(0, weight=1)
        content_frame.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(content_frame, highlightthickness=0, borderwidth=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar = ttk.Scrollbar(
            content_frame,
            orient="vertical",
            command=self.canvas.yview,
            style="App.Vertical.TScrollbar",
        )
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.form_frame = ttk.Frame(self.canvas)
        self._form_window = self.canvas.create_window(
            (0, 0), window=self.form_frame, anchor="nw"
        )
        self.form_frame.bind("<Configure>", self._on_form_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        for i, field in enumerate(PERSON_FIELDS):
            r = i
            ttk.Label(self.form_frame, text=FIELD_TO_HEADER[field]).grid(
                row=r, column=0, sticky="w", padx=(0, 8), pady=3
            )
            entry = ttk.Entry(self.form_frame, width=40)
            entry.grid(row=r, column=1, sticky="ew", pady=3)
            self.entries[field] = entry
        self.form_frame.columnconfigure(1, weight=1)

        action_frame = ttk.Frame(main)
        action_frame.grid(row=0, column=1, sticky="ns")
        action_frame.columnconfigure(0, weight=1)

        ttk.Button(action_frame, text="Apply", command=self._apply).grid(
            row=0, column=0, sticky="ew", pady=(0, 8)
        )
        ttk.Button(action_frame, text="Cancel", command=self._cancel).grid(
            row=1, column=0, sticky="ew", pady=(0, 12)
        )

        self.error_var = tk.StringVar(value="")
        ttk.Label(
            action_frame, textvariable=self.error_var, foreground="red", wraplength=220
        ).grid(row=2, column=0, sticky="w")
        self.success_var = tk.StringVar(value="")
        ttk.Label(
            action_frame,
            textvariable=self.success_var,
            foreground="#34D399",
            wraplength=220,
        ).grid(row=3, column=0, sticky="w", pady=(6, 0))

        self._bind_scroll_events_recursive(self.canvas)
        self._bind_scroll_events_recursive(self.form_frame)

    def load_person(self, person) -> None:
        self.current_person_id = person.id
        for field, entry in self.entries.items():
            value = getattr(person, field)
            if field in ("staying", "second_leg"):
                if value is True:
                    text = "yes"
                elif value is False:
                    text = "no"
                else:
                    text = "-"
            else:
                text = value if value else "-"
            entry.delete(0, "end")
            entry.insert(0, text)
        self.error_var.set("")
        self.success_var.set("")

    def _apply(self) -> None:
        if not self.on_apply or not self.current_person_id:
            return
        patch = {}
        for field, entry in self.entries.items():
            val = entry.get().strip()
            patch[field] = "" if val == "-" else val
        self.on_apply(self.current_person_id, patch)

    def _cancel(self) -> None:
        if self.on_cancel:
            self.on_cancel()

    def show_error(self, message: str) -> None:
        self.error_var.set(message)
        if message:
            self.success_var.set("")

    def show_success(self, message: str) -> None:
        self.success_var.set(message)
        if message:
            self.error_var.set("")

    def _on_form_configure(self, _event: tk.Event) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event: tk.Event) -> None:
        self.canvas.itemconfigure(self._form_window, width=event.width)

    def _bind_scroll_events_recursive(self, widget: tk.Misc) -> None:
        widget.bind("<MouseWheel>", self._on_mouse_wheel, add="+")
        widget.bind("<Button-4>", self._on_mouse_wheel_linux, add="+")
        widget.bind("<Button-5>", self._on_mouse_wheel_linux, add="+")
        for child in widget.winfo_children():
            self._bind_scroll_events_recursive(child)

    def _on_mouse_wheel(self, event: tk.Event) -> str:
        # Windows/macOS wheel events.
        if event.delta:
            self.canvas.yview_scroll(int(-event.delta / 120), "units")
            return "break"
        return ""

    def _on_mouse_wheel_linux(self, event: tk.Event) -> str:
        # Linux wheel events.
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
            return "break"
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")
            return "break"
        return ""
