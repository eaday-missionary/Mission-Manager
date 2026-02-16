from mission_manager.main import greet


def test_greet() -> None:
    assert greet() == "Hello from Mission Manager!"
