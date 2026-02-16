from pathlib import Path

from mission_manager.models import ParsedDataset
from mission_manager.services import DashboardService
from mission_manager.storage import StorageRepository


def test_service_import_replace_flow(monkeypatch, tmp_path: Path) -> None:
    repo = StorageRepository(tmp_path / "svc.sqlite3")
    svc = DashboardService(repo)

    dataset = ParsedDataset(
        records=[
            {
                "first_name": "Jane",
                "last_name": "Smith",
                "current_companion": None,
                "new_companion": None,
                "current_zone": "Z1",
                "current_area": "A1",
                "new_zone": None,
                "new_area": None,
                "staying": True,
                "pre_travel": None,
                "departure_terminal": None,
                "departure_time": "10:00",
                "arrival_terminal": None,
                "arrival_time": "11:00",
                "second_leg": False,
                "second_departure_terminal": None,
                "second_departure_time": None,
                "second_arrival_terminal": None,
                "second_arrival_time": None,
                "source_file_name": "x.xlsx",
                "source_row_number": 2,
            }
        ],
        records_processed=1,
        records_skipped=0,
        errors=[],
        warnings=[],
    )

    monkeypatch.setattr("mission_manager.services.parse_excel_file", lambda _p: dataset)
    result = svc.import_excel("fake.xlsx")
    assert result.success
    assert result.records_inserted == 1
    assert len(svc.list_people()) == 1


def test_service_update_validation(tmp_path: Path) -> None:
    repo = StorageRepository(tmp_path / "svc.sqlite3")
    svc = DashboardService(repo)
    repo.replace_people(
        [
            {
                "first_name": "Jane",
                "last_name": "Smith",
                "current_companion": None,
                "new_companion": None,
                "current_zone": "Z1",
                "current_area": "A1",
                "new_zone": None,
                "new_area": None,
                "staying": True,
                "pre_travel": None,
                "departure_terminal": None,
                "departure_time": "10:00",
                "arrival_terminal": None,
                "arrival_time": "11:00",
                "second_leg": False,
                "second_departure_terminal": None,
                "second_departure_time": None,
                "second_arrival_terminal": None,
                "second_arrival_time": None,
                "source_file_name": "x.xlsx",
                "source_row_number": 2,
            }
        ],
        source_file_name="x.xlsx",
        processed=1,
        skipped=0,
    )
    person = svc.list_people()[0]
    _, errors = svc.update_person(person.id, {"departure_time": "bad"})
    assert errors


def test_service_update_normalizes_detail_payload(tmp_path: Path) -> None:
    repo = StorageRepository(tmp_path / "svc.sqlite3")
    svc = DashboardService(repo)
    repo.replace_people(
        [
            {
                "first_name": "Jane",
                "last_name": "Smith",
                "current_companion": "Comp A",
                "new_companion": None,
                "current_zone": "Z1",
                "current_area": "A1",
                "new_zone": None,
                "new_area": None,
                "staying": True,
                "pre_travel": None,
                "departure_terminal": "T1",
                "departure_time": "10:00",
                "arrival_terminal": "T2",
                "arrival_time": "11:00",
                "second_leg": False,
                "second_departure_terminal": None,
                "second_departure_time": None,
                "second_arrival_terminal": None,
                "second_arrival_time": None,
                "source_file_name": "x.xlsx",
                "source_row_number": 2,
            }
        ],
        source_file_name="x.xlsx",
        processed=1,
        skipped=0,
    )
    person = svc.list_people()[0]
    updated, errors = svc.update_person(
        person.id,
        {
            "staying": "no",
            "second_leg": "yes",
            "current_companion": "",
            "departure_time": "0945",
            "second_departure_time": "",
        },
    )
    assert not errors
    assert updated is not None
    assert updated.staying is False
    assert updated.second_leg is True
    assert updated.current_companion is None
    assert updated.departure_time == "09:45"
    assert updated.second_departure_time is None
