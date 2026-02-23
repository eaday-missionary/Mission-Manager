from pathlib import Path

from mission_manager.services import DashboardService
from mission_manager.storage import StorageRepository


def _record(first: str, last: str, current_comp: str | None, dep_time: str, updated_at: str | None = None) -> dict:
    return {
        "first_name": first,
        "last_name": last,
        "current_companion": current_comp,
        "new_companion": None,
        "current_zone": "Zone A",
        "current_area": "Area 1",
        "new_zone": "Zone B",
        "new_area": "Area 2",
        "staying": False,
        "pre_travel": None,
        "departure_terminal": "Seoul",
        "departure_time": dep_time,
        "arrival_terminal": "Busan",
        "arrival_time": "10:00",
        "second_leg": False,
        "second_departure_terminal": None,
        "second_departure_time": None,
        "second_arrival_terminal": None,
        "second_arrival_time": None,
        "source_file_name": "sample.xlsx",
        "source_row_number": 2,
        "updated_at": updated_at,
    }


def test_transfer_service_create_requires_confirmation(tmp_path: Path) -> None:
    repo = StorageRepository(tmp_path / "svc_transfer.sqlite3")
    svc = DashboardService(repo)
    result = svc.create_schedule(confirm_overwrite=False)
    assert not result.success
    assert result.errors
    assert result.errors[0].code == "CONFIRMATION_REQUIRED"


def test_transfer_service_create_and_read(tmp_path: Path) -> None:
    repo = StorageRepository(tmp_path / "svc_transfer.sqlite3")
    svc = DashboardService(repo)
    repo.replace_people(
        [
            _record("John", "Doe", "Jane Roe", "08:00"),
            _record("Jane", "Roe", "John Doe", "08:00"),
        ],
        source_file_name="sample.xlsx",
        processed=2,
        skipped=0,
    )
    result = svc.create_schedule(confirm_overwrite=True)
    assert result.success
    assert result.blocks_generated == 2
    assert svc.get_schedule_document()


def test_transfer_service_fix_without_prior_schedule_autocreates(tmp_path: Path) -> None:
    repo = StorageRepository(tmp_path / "svc_transfer.sqlite3")
    svc = DashboardService(repo)
    repo.replace_people(
        [
            _record("John", "Doe", "Jane Roe", "08:00"),
            _record("Jane", "Roe", "John Doe", "08:00"),
        ],
        source_file_name="sample.xlsx",
        processed=2,
        skipped=0,
    )
    result = svc.fix_schedule()
    assert result.success
    assert result.blocks_rebuilt >= 2
    assert svc.get_schedule_document()


def test_transfer_service_fix_delta_rebuilds_after_edit(tmp_path: Path) -> None:
    repo = StorageRepository(tmp_path / "svc_transfer.sqlite3")
    svc = DashboardService(repo)
    repo.replace_people(
        [
            _record("John", "Doe", "Jane Roe", "08:00"),
            _record("Jane", "Roe", "John Doe", "08:00"),
        ],
        source_file_name="sample.xlsx",
        processed=2,
        skipped=0,
    )
    created = svc.create_schedule(confirm_overwrite=True)
    assert created.success
    person = svc.list_people()[0]
    updated, errors = svc.update_person(person.id, {"departure_time": "07:00"})
    assert updated is not None
    assert not errors

    fixed = svc.fix_schedule()
    assert fixed.success
    assert fixed.blocks_rebuilt > 0
    assert fixed.schedule_version is not None
    assert created.schedule_version is not None
    assert fixed.schedule_version > created.schedule_version
