# Mission Manager

A Python application to help manage mission-related tasks.

## 1) First-time setup (PowerShell)

```powershell
# from the repository root
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 2) Run the app

```powershell
# option A: run as a module
python -m mission_manager

# option B: run the installed CLI command
mission-manager
```

## 3) Run tests

```powershell
python -m pytest -q
```

If Tk-based UI tests skip because Tcl/Tk is not initializing on Windows, verify the base Python install includes a working `tcl\tcl8.6` and `tcl\tk8.6` runtime.

## Local dashboard data

- Runtime dependencies now include `openpyxl` (for `.xlsx`/`.xlsm`) and `xlrd` (for `.xls`).
- Local dashboard persistence uses SQLite in the user app-data directory:
  - Windows: `%LOCALAPPDATA%\MissionManager\dashboard.sqlite3`
  - Linux/macOS fallback: `~/.local/share/MissionManager/dashboard.sqlite3`

## Project structure

- `src/mission_manager/`: application code
- `tests/`: test files
- `pyproject.toml`: package/config metadata
- `requirements.txt`: quick install dependencies
