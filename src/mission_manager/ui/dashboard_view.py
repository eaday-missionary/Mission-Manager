"""Main dashboard list/search/filter view."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from mission_manager.constants import FIELD_TO_HEADER, PERSON_FIELDS, SORT_OPTIONS


class DashboardView(ttk.Frame):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, padding=12)
        self.on_open_detail = None
        self.view_mode: str = "compact"

        controls = ttk.Frame(self)
        controls.pack(fill="x", pady=(0, 8))

        ttk.Label(controls, text="Search").grid(row=0, column=0, sticky="w")
        self.search_entry = ttk.Entry(controls, width=36)
        self.search_entry.grid(row=1, column=0, padx=(0, 8))

        ttk.Label(controls, text="Sort").grid(row=0, column=1, sticky="w")
        self.sort_var = tk.StringVar(value="Current Zone (A-Z)")
        self.sort_menu = ttk.Combobox(
            controls,
            values=list(SORT_OPTIONS.keys()),
            textvariable=self.sort_var,
            width=32,
            state="readonly",
        )
        self.sort_menu.grid(row=1, column=1, padx=(0, 8))

        ttk.Button(controls, text="Open Selected", command=self._handle_open_detail).grid(
            row=1, column=2
        )

        filters = ttk.Frame(self)
        filters.pack(fill="x", pady=(0, 8))
        self.current_area = tk.StringVar(value="All")
        self.new_zone = tk.StringVar(value="All")
        self.new_area = tk.StringVar(value="All")
        self.second_leg = tk.StringVar(value="All")

        self.current_area_combo = self._filter_combo(
            filters, "Current Area", self.current_area, 0
        )
        self.new_zone_combo = self._filter_combo(filters, "New Zone", self.new_zone, 1)
        self.new_area_combo = self._filter_combo(filters, "New Area", self.new_area, 2)
        self.second_leg_combo = self._filter_combo(
            filters, "Second Leg?", self.second_leg, 3, values=["All", "No", "Yes"]
        )

        self.table_container = ttk.Frame(self)
        self.table_container.pack(fill="both", expand=True)

        columns = PERSON_FIELDS
        self.tree = ttk.Treeview(
            self.table_container, columns=columns, show="headings", height=16
        )
        for c in columns:
            self.tree.heading(c, text=FIELD_TO_HEADER.get(c, c))
            self.tree.column(c, width=120, anchor="w", minwidth=60, stretch=True)

        self.y_scroll = ttk.Scrollbar(
            self.table_container, orient="vertical", command=self.tree.yview
        )
        self.x_scroll = ttk.Scrollbar(
            self.table_container, orient="horizontal", command=self.tree.xview
        )
        self.tree.configure(yscrollcommand=self.y_scroll.set, xscrollcommand=self.x_scroll.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        self.y_scroll.grid(row=0, column=1, sticky="ns")
        self.x_scroll.grid(row=1, column=0, sticky="ew")
        self.table_container.grid_rowconfigure(0, weight=1)
        self.table_container.grid_columnconfigure(0, weight=1)
        self.tree.bind("<Double-1>", lambda _e: self._handle_open_detail())

        bottom = ttk.Frame(self)
        bottom.pack(fill="x", pady=(6, 0))

        self.count_var = tk.StringVar(value="0 results")
        ttk.Label(bottom, textvariable=self.count_var).pack(side="left")

        mode_buttons = ttk.Frame(bottom)
        mode_buttons.pack(side="right")
        self.full_btn = ttk.Button(
            mode_buttons, text="Full View", command=lambda: self.set_view_mode("full")
        )
        self.compact_btn = ttk.Button(
            mode_buttons, text="Compact", command=lambda: self.set_view_mode("compact")
        )
        self.full_btn.pack(side="left", padx=(0, 8))
        self.compact_btn.pack(side="left")

        self.table_container.bind("<Configure>", self._on_container_resize)
        self.set_view_mode("compact")

    def _filter_combo(
        self, parent: ttk.Frame, label: str, var: tk.StringVar, col: int, values=None
    ) -> ttk.Combobox:
        ttk.Label(parent, text=label).grid(row=0, column=col, sticky="w", padx=(0, 8))
        combo = ttk.Combobox(parent, textvariable=var, state="readonly", width=20)
        combo["values"] = values or ["All"]
        combo.grid(row=1, column=col, padx=(0, 8))
        return combo

    def bind_query_events(self, callback) -> None:
        self.search_entry.bind("<KeyRelease>", lambda _e: callback(debounce=True))
        self.sort_menu.bind("<<ComboboxSelected>>", lambda _e: callback(debounce=False))
        self.current_area_combo.bind(
            "<<ComboboxSelected>>", lambda _e: callback(debounce=False)
        )
        self.new_zone_combo.bind("<<ComboboxSelected>>", lambda _e: callback(debounce=False))
        self.new_area_combo.bind("<<ComboboxSelected>>", lambda _e: callback(debounce=False))
        self.second_leg_combo.bind(
            "<<ComboboxSelected>>", lambda _e: callback(debounce=False)
        )

    def _handle_open_detail(self) -> None:
        if not self.on_open_detail:
            return
        selected = self.tree.selection()
        if not selected:
            return
        self.on_open_detail(selected[0])

    def selected_filters(self) -> dict[str, str]:
        return {
            "current_area": self.current_area.get(),
            "new_zone": self.new_zone.get(),
            "new_area": self.new_area.get(),
            "second_leg": self.second_leg.get(),
        }

    def selected_sort(self) -> tuple[str, str]:
        return SORT_OPTIONS.get(self.sort_var.get(), SORT_OPTIONS["Current Zone (A-Z)"])

    def selected_search(self) -> tuple[str | None, str | None]:
        query = self.search_entry.get().strip()
        if not query:
            return None, None
        return None, query

    def update_filter_values(self, people: list) -> None:
        def options(attr: str) -> list[str]:
            values = sorted({getattr(p, attr) for p in people if getattr(p, attr)})
            return ["All"] + values

        self.current_area_combo["values"] = options("current_area")
        self.new_zone_combo["values"] = options("new_zone")
        self.new_area_combo["values"] = options("new_area")

        if self.current_area.get() not in self.current_area_combo["values"]:
            self.current_area.set("All")
        if self.new_zone.get() not in self.new_zone_combo["values"]:
            self.new_zone.set("All")
        if self.new_area.get() not in self.new_area_combo["values"]:
            self.new_area.set("All")

    def set_people(self, people: list) -> None:
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        for person in people:
            values = []
            for field in PERSON_FIELDS:
                value = getattr(person, field)
                if field in ("staying", "second_leg"):
                    display = (
                        "Yes"
                        if value is True
                        else ("No" if value is False else "-")
                    )
                else:
                    display = value if value else "-"
                values.append(display)
            self.tree.insert("", "end", iid=person.id, values=tuple(values))
        self.count_var.set(f"{len(people)} results")
        self._apply_table_mode()

    def set_view_mode(self, mode: str) -> None:
        self.view_mode = mode
        self._apply_table_mode()

    def _on_container_resize(self, _event) -> None:
        if self.view_mode == "full":
            self._apply_table_mode()

    def _apply_table_mode(self) -> None:
        if self.view_mode == "full":
            self._set_full_widths()
            self.x_scroll.grid_remove()
            self.full_btn.state(["disabled"])
            self.compact_btn.state(["!disabled"])
        else:
            self._set_compact_widths()
            self.x_scroll.grid()
            self.full_btn.state(["!disabled"])
            self.compact_btn.state(["disabled"])

    def _set_compact_widths(self) -> None:
        widths = {
            "first_name": 120,
            "last_name": 120,
            "current_companion": 180,
            "new_companion": 180,
            "current_zone": 120,
            "current_area": 140,
            "new_zone": 120,
            "new_area": 140,
            "staying": 100,
            "pre_travel": 140,
            "departure_terminal": 160,
            "departure_time": 120,
            "arrival_terminal": 160,
            "arrival_time": 120,
            "second_leg": 100,
            "second_departure_terminal": 190,
            "second_departure_time": 150,
            "second_arrival_terminal": 190,
            "second_arrival_time": 150,
        }
        for field in PERSON_FIELDS:
            self.tree.column(
                field, width=widths.get(field, 120), minwidth=70, stretch=False
            )

    def _set_full_widths(self) -> None:
        available = max(self.table_container.winfo_width() - 16, 1140)
        width = max(70, available // len(PERSON_FIELDS))
        for field in PERSON_FIELDS:
            self.tree.column(field, width=width, minwidth=60, stretch=True)
