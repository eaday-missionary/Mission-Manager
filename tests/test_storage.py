from pathlib import Path

from mission_manager.storage import StorageRepository


def _sample_record(first_name: str, last_name: str, current_area: str, zone: str) -> dict:
    return {
        "first_name": first_name,
        "last_name": last_name,
        "current_companion": None,
        "new_companion": None,
        "current_zone": zone,
        "current_area": current_area,
        "new_zone": None,
        "new_area": None,
        "staying": True,
        "pre_travel": None,
        "departure_terminal": None,
        "departure_time": "08:00",
        "arrival_terminal": None,
        "arrival_time": "09:00",
        "second_leg": False,
        "second_departure_terminal": None,
        "second_departure_time": None,
        "second_arrival_terminal": None,
        "second_arrival_time": None,
        "source_file_name": "sample.xlsx",
        "source_row_number": 2,
    }


def test_storage_replace_and_list_sort(tmp_path: Path) -> None:
    repo = StorageRepository(tmp_path / "test.sqlite3")
    records = [
        _sample_record("John", "Doe", "Area1", "B Zone"),
        _sample_record("Adam", "Zed", "Area2", "A Zone"),
    ]
    repo.replace_people(records, source_file_name="sample.xlsx", processed=2, skipped=0)

    people = repo.list_people()
    assert len(people) == 2
    assert people[0].current_zone == "A Zone"


def test_storage_append_updates_on_composite_key(tmp_path: Path) -> None:
    repo = StorageRepository(tmp_path / "test.sqlite3")
    repo.replace_people([_sample_record("John", "Doe", "Area1", "Zone1")], source_file_name="a.xlsx", processed=1, skipped=0)
    repo.append_people([_sample_record("John", "Doe", "Area1", "Zone2")], source_file_name="b.xlsx", processed=1, skipped=0)
    people = repo.list_people()
    assert len(people) == 1
    assert people[0].current_zone == "Zone2"


def test_storage_global_search_contains_and_boolean_text(tmp_path: Path) -> None:
    repo = StorageRepository(tmp_path / "test.sqlite3")
    repo.replace_people(
        [
            {**_sample_record("Alice", "Rivera", "Area1", "North"), "staying": False},
            {**_sample_record("Bob", "Stone", "Area2", "South"), "staying": False},
        ],
        source_file_name="sample.xlsx",
        processed=2,
        skipped=0,
    )
    # Ensure second leg text search works from boolean storage.
    repo.append_people(
        [
            {
                **_sample_record("Clara", "Moon", "Area3", "East"),
                "second_leg": True,
                "departure_terminal": "Incheon T1",
            }
        ],
        source_file_name="sample2.xlsx",
        processed=1,
        skipped=0,
    )

    by_name = repo.list_people(search_query="ali")
    assert len(by_name) == 1
    assert by_name[0].first_name == "Alice"

    by_terminal_case_insensitive = repo.list_people(search_query="INCHEON")
    assert len(by_terminal_case_insensitive) == 1
    assert by_terminal_case_insensitive[0].first_name == "Clara"

    by_boolean_text = repo.list_people(search_query="yes")
    assert len(by_boolean_text) == 1
    assert by_boolean_text[0].first_name == "Clara"


def test_storage_create_person_updates_record_count(tmp_path: Path) -> None:
    repo = StorageRepository(tmp_path / "test.sqlite3")
    created = repo.create_person(
        {
            "first_name": "Nina",
            "last_name": "Park",
            "current_zone": "West",
            "current_area": "Area 5",
            "staying": True,
            "second_leg": False,
            "departure_time": "09:00",
            "arrival_time": "10:30",
        }
    )
    assert created.first_name == "Nina"
    assert created.last_name == "Park"
    state = repo.dataset_state()
    assert state.record_count == 1
