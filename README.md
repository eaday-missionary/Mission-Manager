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
pytest
```

## Project structure

- `src/mission_manager/`: application code
- `tests/`: test files
- `pyproject.toml`: package/config metadata
- `requirements.txt`: quick install dependencies