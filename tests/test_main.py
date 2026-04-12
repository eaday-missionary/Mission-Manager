import launcher
from mission_manager.main import greet, main as app_main


def test_greet() -> None:
    assert greet() == "Hello from Mission Manager!"


def test_launcher_imports_main_entrypoint() -> None:
    assert launcher.main is app_main
