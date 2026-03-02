import sqlite3
from pathlib import Path

from mission_manager.storage import StorageRepository


def _sample_record(first_name: str, last_name: str, current_area: str, zone: str) -> dict:
    return {
        "first_name": first_name,
        "last_name": last_name,
        "title": None,
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


def test_storage_title_roundtrip_create_update_and_search(tmp_path: Path) -> None:
    repo = StorageRepository(tmp_path / "test.sqlite3")
    created = repo.create_person(
        {
            "first_name": "Mina",
            "last_name": "Cho",
            "title": "E",
            "current_zone": "West",
            "current_area": "Area 3",
            "staying": True,
            "second_leg": False,
            "departure_time": "09:00",
            "arrival_time": "10:00",
        }
    )
    assert created.title == "E"

    updated = repo.update_person(created.id, {"title": "S"})
    assert updated is not None
    assert updated.title == "S"

    found = repo.list_people(search_query="s")
    assert any(person.id == created.id for person in found)


def test_storage_migrates_people_table_to_add_title_column(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy_people.sqlite3"
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE people (
                id TEXT PRIMARY KEY,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                current_companion TEXT,
                new_companion TEXT,
                current_zone TEXT,
                current_area TEXT,
                new_zone TEXT,
                new_area TEXT,
                staying INTEGER,
                pre_travel TEXT,
                departure_terminal TEXT,
                departure_time TEXT,
                arrival_terminal TEXT,
                arrival_time TEXT,
                second_leg INTEGER,
                second_departure_terminal TEXT,
                second_departure_time TEXT,
                second_arrival_terminal TEXT,
                second_arrival_time TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                source_file_name TEXT,
                source_row_number INTEGER,
                dataset_version INTEGER NOT NULL
            );
            CREATE TABLE dataset_meta (key TEXT PRIMARY KEY, value TEXT);
            CREATE TABLE import_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation TEXT NOT NULL,
                source_file_name TEXT,
                created_at TEXT NOT NULL,
                records_processed INTEGER NOT NULL,
                records_inserted INTEGER NOT NULL,
                records_updated INTEGER NOT NULL,
                records_skipped INTEGER NOT NULL,
                success INTEGER NOT NULL,
                notes TEXT
            );
            INSERT INTO dataset_meta(key, value) VALUES('schema_version', '2');
            INSERT INTO dataset_meta(key, value) VALUES('last_imported_at', '');
            INSERT INTO dataset_meta(key, value) VALUES('record_count', '0');
            INSERT INTO dataset_meta(key, value) VALUES('source_file_name', '');
            """
        )

    repo = StorageRepository(db_path)
    assert repo.dataset_state().schema_version == 3

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cols = {row["name"] for row in conn.execute("PRAGMA table_info(people)").fetchall()}
    assert "title" in cols
