import tkinter as tk
from tkinter import ttk

from .ui.app import run_app


def greet() -> str:
    return "Hello from Mission Manager!"


def on_upload_click() -> None:
    # Legacy callback retained for compatibility in earlier tests.
    print("Upload button clicked")


def main() -> None:
    run_app()


if __name__ == "__main__":
    main()
