"""Main Tkinter application wiring for dashboard epic."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from mission_manager.services import DashboardService

from .dashboard_view import DashboardView
from .data_mgmt_view import DataManagementView
from .detail_view import DetailView
from .dialogs import ask_confirm, pick_excel_file, show_error


class MissionManagerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Mission Manager")
        self.root.geometry("1100x680")
        self.root.minsize(1100, 680)
        self._refresh_after_id: str | None = None

        self.service = DashboardService()
        self._apply_dark_theme()

        self.message_var = tk.StringVar(value="")
        top = ttk.Frame(root, padding=10, style="Card.TFrame")
        top.pack(fill="x")
        ttk.Label(
            top, text="Mission Manager Dashboard", style="Title.TLabel"
        ).pack(side="left")
        ttk.Label(top, textvariable=self.message_var, style="Info.TLabel").pack(
            side="right"
        )

        self.import_frame = ttk.Frame(root, padding=16, style="Card.TFrame")
        self.import_frame.pack(fill="both", expand=True)
        ttk.Label(self.import_frame, text="Import Spreadsheet", style="Title.TLabel").pack(
            pady=(20, 10)
        )
        ttk.Label(
            self.import_frame,
            text="Upload a canonical Excel file (.xlsx, .xlsm, .xls) to begin.",
        ).pack(pady=(0, 12))
        ttk.Button(self.import_frame, text="Import Excel File", command=self.import_initial).pack()

        self.main_frame = ttk.Frame(root)
        notebook = ttk.Notebook(self.main_frame)
        notebook.pack(fill="both", expand=True)

        self.dashboard_view = DashboardView(notebook)
        self.detail_view = DetailView(notebook)
        self.data_view = DataManagementView(notebook)

        notebook.add(self.dashboard_view, text="Dashboard")
        notebook.add(self.detail_view, text="Person Detail")
        notebook.add(self.data_view, text="Data Management")

        self.dashboard_view.on_open_detail = self.open_detail
        self.dashboard_view.bind_query_events(self.request_refresh)
        self.detail_view.on_apply = self.apply_detail
        self.detail_view.on_cancel = lambda: notebook.select(self.dashboard_view)

        self.data_view.on_append = self.append_data
        self.data_view.on_replace = self.replace_data
        self.data_view.on_clear = self.clear_data

        self.notebook = notebook

        self._sync_startup_state()

    def _apply_dark_theme(self) -> None:
        self.root.configure(background="#0F1115")
        style = ttk.Style(self.root)
        style.theme_use("clam")

        bg = "#0F1115"
        card = "#1A1E25"
        panel = "#202632"
        text = "#E8ECF1"
        subtext = "#9FA8B3"
        accent = "#3B82F6"
        accent_hover = "#5A98F8"
        border = "#2E3745"
        select_bg = "#2D6CDF"

        style.configure(".", background=bg, foreground=text, fieldbackground=panel)
        style.configure("TFrame", background=bg)
        style.configure("Card.TFrame", background=card, borderwidth=1, relief="solid")
        style.configure("TLabel", background=bg, foreground=text)
        style.configure("Title.TLabel", background=card, foreground=text, font=("Segoe UI", 14, "bold"))
        style.configure("Info.TLabel", background=card, foreground=subtext)
        style.configure(
            "TButton",
            background=accent,
            foreground="#FFFFFF",
            padding=(10, 6),
            bordercolor=accent,
            focusthickness=1,
            focuscolor=accent,
        )
        style.map(
            "TButton",
            background=[("active", accent_hover), ("pressed", accent_hover), ("disabled", "#334155")],
            foreground=[("disabled", "#94A3B8")],
        )
        style.configure(
            "TEntry",
            fieldbackground=panel,
            foreground=text,
            insertcolor=text,
            bordercolor=border,
            padding=(8, 6),
        )
        style.configure(
            "TCombobox",
            fieldbackground=panel,
            foreground=text,
            arrowcolor=text,
            bordercolor=border,
            padding=(8, 6),
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", panel)],
            foreground=[("readonly", text)],
            selectbackground=[("readonly", panel)],
            selectforeground=[("readonly", text)],
        )
        style.configure("TNotebook", background=bg, borderwidth=0)
        style.configure("TNotebook.Tab", background=panel, foreground=text, padding=(12, 8))
        style.map("TNotebook.Tab", background=[("selected", card), ("active", panel)])
        style.configure(
            "Treeview",
            background=panel,
            foreground=text,
            fieldbackground=panel,
            bordercolor=border,
            rowheight=26,
        )
        style.configure("Treeview.Heading", background=card, foreground=text)
        style.map("Treeview", background=[("selected", select_bg)], foreground=[("selected", "#FFFFFF")])

    def request_refresh(self, *, debounce: bool = False) -> None:
        if debounce:
            if self._refresh_after_id:
                self.root.after_cancel(self._refresh_after_id)
            self._refresh_after_id = self.root.after(150, self.refresh_people)
            return
        if self._refresh_after_id:
            self.root.after_cancel(self._refresh_after_id)
            self._refresh_after_id = None
        self.refresh_people()

    def _sync_startup_state(self) -> None:
        state = self.service.load_local_dataset()
        if state.recovery_notice:
            self.message_var.set(state.recovery_notice)
        if state.record_count > 0:
            self.import_frame.pack_forget()
            self.main_frame.pack(fill="both", expand=True)
            self.refresh_people()
            self.data_view.set_status(record_count=state.record_count, last_imported_at=state.last_imported_at, source_file_name=state.source_file_name)
        else:
            self.main_frame.pack_forget()
            self.import_frame.pack(fill="both", expand=True)

    def _run_import(self, mode: str) -> None:
        file_path = pick_excel_file()
        if not file_path:
            return

        if mode == "import":
            result = self.service.import_excel(file_path)
        elif mode == "append":
            result = self.service.append_excel(file_path)
        else:
            result = self.service.replace_excel(file_path)

        if not result.success:
            msg = "\n".join([e.message + (f" (row {e.row_number})" if e.row_number else "") for e in result.errors])
            show_error("Import Error", msg or "Import failed")
            return

        warn = "\n".join(result.warnings)
        if warn:
            self.message_var.set(warn)
        else:
            self.message_var.set(f"{mode.title()} completed")

        self.import_frame.pack_forget()
        self.main_frame.pack(fill="both", expand=True)
        self.refresh_people()
        state = self.service.load_local_dataset()
        self.data_view.set_status(record_count=state.record_count, last_imported_at=state.last_imported_at, source_file_name=state.source_file_name)

    def import_initial(self) -> None:
        self._run_import("import")

    def append_data(self) -> None:
        self._run_import("append")

    def replace_data(self) -> None:
        if not ask_confirm("Replace Dataset", "This will replace all existing records. Continue?"):
            return
        self._run_import("replace")

    def clear_data(self) -> None:
        if not ask_confirm("Clear Dataset", "Erase all local records?"):
            return
        self.service.clear_dataset(confirm=True)
        self.message_var.set("Dataset cleared")
        self.import_frame.pack(fill="both", expand=True)
        self.main_frame.pack_forget()

    def refresh_people(self) -> None:
        self._refresh_after_id = None
        people = self.service.list_people(
            filters=self.dashboard_view.selected_filters(),
            sort=self.dashboard_view.selected_sort(),
            search=self.dashboard_view.selected_search(),
        )
        self.dashboard_view.set_people(people)
        self.dashboard_view.update_filter_values(people)

    def open_detail(self, person_id: str) -> None:
        person = self.service.get_person(person_id)
        if not person:
            show_error("Not Found", "Selected person could not be loaded.")
            return
        self.detail_view.load_person(person)
        self.notebook.select(self.detail_view)

    def apply_detail(self, person_id: str, patch: dict[str, str]) -> None:
        person, errors = self.service.update_person(person_id, patch)
        if errors:
            self.detail_view.show_error("; ".join(e.message for e in errors))
            return
        if not person:
            show_error("Apply Error", "Failed to apply changes to the selected record.")
            return
        self.detail_view.show_error("")
        self.detail_view.show_success("Changes applied.")
        self.message_var.set("Changes applied.")
        self.refresh_people()
        self.open_detail(person_id)
        self.detail_view.show_success("Changes applied.")


def run_app() -> None:
    root = tk.Tk()
    MissionManagerApp(root)
    root.mainloop()
