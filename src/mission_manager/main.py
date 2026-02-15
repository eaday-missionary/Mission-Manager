import tkinter as tk
from tkinter import ttk


def greet() -> str:
    return "Hello from Mission Manager!"


def on_upload_click() -> None:
    # Placeholder for future Excel import behavior.
    print("Upload button clicked")


def main() -> None:
    root = tk.Tk()
    root.title("Mission Manager")
    root.geometry("420x220")
    root.resizable(False, False)

    container = ttk.Frame(root, padding=24)
    container.pack(fill="both", expand=True)

    title_label = ttk.Label(
        container,
        text="Mission Manager",
        font=("Segoe UI", 16, "bold"),
    )
    title_label.pack(pady=(0, 10))

    subtitle_label = ttk.Label(
        container,
        text="Upload a Microsoft Excel file to begin.",
        font=("Segoe UI", 10),
    )
    subtitle_label.pack(pady=(0, 20))

    upload_button = ttk.Button(
        container,
        text="Upload Excel File",
        command=on_upload_click,
    )
    upload_button.pack()

    root.mainloop()


if __name__ == "__main__":
    main()