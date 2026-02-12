from mission_manager.main import greet


def test_greet():
    assert greet() == "Hello from Mission Manager!"
