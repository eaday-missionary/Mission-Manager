"""UI dialog wrappers."""

from __future__ import annotations

from tkinter import filedialog, messagebox


def pick_excel_file() -> str:
    return filedialog.askopenfilename(
        title="Select Excel File",
        filetypes=[("Excel Files", "*.xlsx *.xlsm *.xls"), ("All Files", "*.*")],
    )


def show_error(title: str, message: str) -> None:
    messagebox.showerror(title, message)


def show_info(title: str, message: str) -> None:
    messagebox.showinfo(title, message)


def ask_confirm(title: str, message: str) -> bool:
    return messagebox.askyesno(title, message)
