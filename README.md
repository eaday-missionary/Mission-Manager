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

## 4) Build a Windows `.exe`

This repo includes a PyInstaller spec plus a helper script for building a clickable Windows app.

```powershell
# from the repository root
python -m venv .venv
.\.venv\Scripts\Activate.ps1
.\scripts\build_exe.ps1
```

The built executable will be here:

```powershell
dist\MissionManager\MissionManager.exe
```

To build a single-file executable instead:

```powershell
.\scripts\build_exe.ps1 -OneFile
```

That build will be here:

```powershell
dist\MissionManager.exe
```

## 5) Publish the `.exe` on GitHub

This repo includes a GitHub Actions workflow at `.github/workflows/build-windows-exe.yml`.

- Running the workflow manually creates a Windows build artifact in GitHub Actions.
- Publishing a GitHub Release builds the Windows app and attaches `MissionManager-win.zip` to the release automatically.

Typical release flow:

```powershell
git tag v0.1.0
git push origin v0.1.0
```

Then create or publish the matching GitHub Release for that tag in the GitHub UI.

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
