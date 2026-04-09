from __future__ import annotations

import os
import sys
from pathlib import Path


def _configure_tcl_runtime() -> None:
    base = Path(sys.base_prefix)
    tcl_root = base / "tcl"
    tcl_library = tcl_root / "tcl8.6"
    tk_library = tcl_root / "tk8.6"
    if tcl_library.exists():
        os.environ.setdefault("TCL_LIBRARY", str(tcl_library))
    if tk_library.exists():
        os.environ.setdefault("TK_LIBRARY", str(tk_library))


_configure_tcl_runtime()
