"""Allow `python -m mission_manager` execution."""

try:
    from .main import main
except ImportError:  # pragma: no cover - fallback for packaged/script execution
    from mission_manager.main import main

if __name__ == "__main__":
    main()
