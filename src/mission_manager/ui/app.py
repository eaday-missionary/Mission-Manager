"""Main Tkinter application wiring for dashboard epic."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from mission_manager.services import DashboardService

from .dashboard_view import DashboardView
from .data_mgmt_view import DataManagementView
from .detail_view import DetailView
from .dialogs import ask_confirm, pick_excel_file, show_error
from .schedule_text_view import ScheduleTextView
from .transfer_editor_view import TransferEditorView


class MissionManagerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Mission Manager")
        self.root.geometry("1100x680")
        self.root.minsize(1100, 680)
        self._refresh_after_id: str | None = None
        self._detail_return_tab: str | None = None

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
        import_buttons = ttk.Frame(self.import_frame, style="Card.TFrame")
        import_buttons.pack()
        ttk.Button(import_buttons, text="Import Excel File", command=self.import_initial).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(import_buttons, text="Add New", command=self.start_add_person).pack(side="left")

        self.main_frame = ttk.Frame(root)
        notebook = ttk.Notebook(self.main_frame)
        notebook.pack(fill="both", expand=True)

        self.dashboard_view = DashboardView(notebook)
        # Force default dashboard table mode on startup.
        self.dashboard_view.set_view_mode("full")
        self.detail_view = DetailView(notebook)
        self.data_view = DataManagementView(notebook)
        self.transfer_view = TransferEditorView(notebook)
        self.schedule_text_view = ScheduleTextView(notebook)

        notebook.add(self.dashboard_view, text="Dashboard")
        notebook.add(self.detail_view, text="Person Detail")
        notebook.add(self.data_view, text="Data Management")
        notebook.add(self.transfer_view, text="Transfer Editor")
        notebook.add(self.schedule_text_view, text="Schedule Text")

        self.dashboard_view.on_open_detail = self.open_detail
        self.dashboard_view.on_add_new = self.start_add_person
        self.dashboard_view.on_create_schedule = self.create_schedule
        self.dashboard_view.bind_query_events(self.request_refresh)
        self.detail_view.on_apply = self.apply_detail
        self.detail_view.on_add = self.add_detail
        self.detail_view.on_cancel = lambda: notebook.select(self.dashboard_view)
        self.transfer_view.on_open_person = self.open_detail

        self.data_view.on_append = self.append_data
        self.data_view.on_replace = self.replace_data
        self.data_view.on_clear = self.clear_data

        self.notebook = notebook
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        self.root.bind("<Control-f>", self._focus_transfer_search)
        self.root.bind("<Control-F>", self._focus_transfer_search)
        self.root.bind("<Destroy>", self._on_root_destroy, add="+")

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
            foreground=[("active", "#FFFFFF"), ("pressed", "#FFFFFF"), ("disabled", "#94A3B8")],
        )
        style.configure(
            "Mode.TButton",
            background=panel,
            foreground=text,
            padding=(10, 6),
            bordercolor=border,
        )
        style.map(
            "Mode.TButton",
            background=[("active", "#2A3342"), ("pressed", "#2A3342")],
            foreground=[("active", text), ("pressed", text)],
        )
        style.configure(
            "ModeActive.TButton",
            background=accent,
            foreground="#FFFFFF",
            padding=(10, 6),
            bordercolor=accent,
        )
        style.map(
            "ModeActive.TButton",
            background=[("active", accent_hover), ("pressed", accent_hover)],
            foreground=[("active", "#FFFFFF"), ("pressed", "#FFFFFF")],
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
        style.map(
            "TNotebook.Tab",
            background=[("selected", card), ("active", panel)],
            foreground=[("selected", text), ("active", text)],
        )
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
        style.configure(
            "App.Vertical.TScrollbar",
            background="#3A4354",
            troughcolor="#1A1E25",
            bordercolor="#1A1E25",
            arrowcolor="#D0D7E2",
            darkcolor="#3A4354",
            lightcolor="#3A4354",
            relief="flat",
            arrowsize=12,
            gripcount=0,
        )
        style.map(
            "App.Vertical.TScrollbar",
            background=[("active", "#4B5A74"), ("pressed", "#5A6B8A")],
            arrowcolor=[("active", "#FFFFFF"), ("pressed", "#FFFFFF")],
        )
        style.configure(
            "App.Horizontal.TScrollbar",
            background="#3A4354",
            troughcolor="#1A1E25",
            bordercolor="#1A1E25",
            arrowcolor="#D0D7E2",
            darkcolor="#3A4354",
            lightcolor="#3A4354",
            relief="flat",
            arrowsize=12,
            gripcount=0,
        )
        style.map(
            "App.Horizontal.TScrollbar",
            background=[("active", "#4B5A74"), ("pressed", "#5A6B8A")],
            arrowcolor=[("active", "#FFFFFF"), ("pressed", "#FFFFFF")],
        )

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
            self.refresh_schedule_outputs()
            self.data_view.set_status(record_count=state.record_count, last_imported_at=state.last_imported_at, source_file_name=state.source_file_name)
        else:
            self.main_frame.pack_forget()
            self.import_frame.pack(fill="both", expand=True)
            self.detail_view.enter_add_mode()

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
        self._auto_regenerate_schedule(mode)
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
        self.refresh_schedule_outputs(note="No schedule available.")
        self.message_var.set("Dataset cleared")
        self.import_frame.pack(fill="both", expand=True)
        self.main_frame.pack_forget()
        self.detail_view.enter_add_mode()
        self.data_view.set_status(record_count=0, last_imported_at=None, source_file_name=None)

    def refresh_people(self) -> None:
        self._refresh_after_id = None
        people = self.service.list_people(
            filters=self.dashboard_view.selected_filters(),
            sort=self.dashboard_view.selected_sort(),
            search=self.dashboard_view.selected_search(),
        )
        self.dashboard_view.set_people(people)
        self.dashboard_view.update_filter_values(people)
        state = self.service.load_local_dataset()
        self.data_view.set_status(
            record_count=state.record_count,
            last_imported_at=state.last_imported_at,
            source_file_name=state.source_file_name,
        )

    def refresh_schedule_outputs(self, note: str | None = None) -> None:
        blocks = self.service.get_schedule_document()
        conflicts = self.service.list_schedule_conflicts()
        people = self.service.list_people()
        self.transfer_view.set_schedule(blocks, conflicts, note=note)
        self.schedule_text_view.set_schedule(blocks, note=note, people=people)

    def refresh_transfer_editor(self, note: str | None = None) -> None:
        # Backward-compatible alias for existing call sites/tests.
        self.refresh_schedule_outputs(note=note)

    def _auto_regenerate_schedule(self, trigger: str) -> bool:
        result = self.service.create_schedule(confirm_overwrite=True)
        if not result.success:
            message = (
                "\n".join(error.message for error in result.errors)
                or "Automatic schedule update failed."
            )
            self.message_var.set(
                f"{trigger.title()} saved, but schedule auto-update failed."
            )
            show_error(
                "Schedule Auto-Update Error",
                "Dashboard data was saved, but automatic schedule update failed.\n\n"
                + message,
            )
            return False
        self.refresh_schedule_outputs(note=f"Schedule auto-updated after {trigger}.")
        return True

    def _focus_transfer_search(self, _event: tk.Event) -> str | None:
        selected_tab = self.notebook.select()
        if selected_tab == str(self.transfer_view):
            self.transfer_view.focus_search()
            return "break"
        if selected_tab == str(self.schedule_text_view):
            self.schedule_text_view.focus_search()
            return "break"
        return None

    def create_schedule(self) -> None:
        warning = (
            "WARNING, this will erase the current schedule in the transfer editor and regenerate a new schedule. "
            "Do you still want to continue?"
        )
        if not ask_confirm("Create Schedule", warning):
            return
        self.transfer_view.show_loading("Creating schedule...")
        self.schedule_text_view.show_loading("Creating schedule text...")
        result = self.service.create_schedule(confirm_overwrite=True)
        if not result.success:
            message = "\n".join(error.message for error in result.errors) or "Schedule creation failed."
            show_error("Create Schedule Error", message)
            self.refresh_schedule_outputs(note="Schedule creation failed.")
            return
        self.message_var.set(
            f"Schedule created: {result.blocks_generated} blocks, {result.conflicts_found} conflicts."
        )
        self.refresh_schedule_outputs(note="Schedule created.")
        self.notebook.select(self.transfer_view)

    def open_detail(self, person_id: str) -> None:
        person = self.service.get_person(person_id)
        if not person:
            show_error("Not Found", "Selected person could not be loaded.")
            return
        current_tab = self.notebook.select()
        if current_tab in {str(self.dashboard_view), str(self.transfer_view)}:
            self._detail_return_tab = current_tab
        elif self._detail_return_tab is None:
            self._detail_return_tab = str(self.dashboard_view)
        self.main_frame.pack(fill="both", expand=True)
        self.import_frame.pack_forget()
        self.detail_view.enter_edit_mode(person)
        self.notebook.select(self.detail_view)

    def start_add_person(self) -> None:
        self.import_frame.pack_forget()
        self.main_frame.pack(fill="both", expand=True)
        self.refresh_people()
        self.refresh_schedule_outputs()
        self.detail_view.enter_add_mode()
        self.notebook.select(self.detail_view)

    def _on_tab_changed(self, _event: tk.Event) -> None:
        if self.notebook.select() == str(self.detail_view) and not self.detail_view.current_person_id:
            self.detail_view.enter_add_mode()

    def _select_dashboard_row(self, person_id: str) -> None:
        if not self.dashboard_view.tree.exists(person_id):
            return
        self.dashboard_view.tree.selection_set(person_id)
        self.dashboard_view.tree.focus(person_id)
        self.dashboard_view.tree.see(person_id)

    def add_detail(self, patch: dict[str, str]) -> None:
        person, errors = self.service.create_person(patch)
        if errors:
            self.detail_view.show_error("; ".join(e.message for e in errors))
            return
        if not person:
            show_error("Add Error", "Failed to add the new record.")
            return
        self.detail_view.show_error("")
        self.detail_view.show_success("")
        self.message_var.set("Person added.")
        self.refresh_people()
        self._auto_regenerate_schedule("add")
        self.notebook.select(self.dashboard_view)
        self._select_dashboard_row(person.id)

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
        self._auto_regenerate_schedule("apply")
        target_tab = self._detail_return_tab
        if target_tab not in self.notebook.tabs():
            target_tab = str(self.dashboard_view)
        self.notebook.select(target_tab)
        if target_tab == str(self.dashboard_view):
            self._select_dashboard_row(person_id)

    def _on_root_destroy(self, event: tk.Event) -> None:
        if event.widget is not self.root:
            return
        if self._refresh_after_id is None:
            return
        try:
            self.root.after_cancel(self._refresh_after_id)
        except tk.TclError:
            pass
        finally:
            self._refresh_after_id = None


def run_app() -> None:
    root = tk.Tk()
    MissionManagerApp(root)
    root.mainloop()
