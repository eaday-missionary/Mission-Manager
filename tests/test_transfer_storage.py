from pathlib import Path

from mission_manager.models import ConflictAnchor, ScheduleBlock, ScheduleConflict
from mission_manager.storage import StorageRepository


def _sample_record() -> dict:
    return {
        "first_name": "John",
        "last_name": "Doe",
        "current_companion": "Jane Roe",
        "new_companion": "Alice Kim",
        "current_zone": "Zone A",
        "current_area": "Area 1",
        "new_zone": "Zone B",
        "new_area": "Area 2",
        "staying": False,
        "pre_travel": None,
        "departure_terminal": "Seoul",
        "departure_time": "08:00",
        "arrival_terminal": "Busan",
        "arrival_time": "10:00",
        "second_leg": False,
        "second_departure_terminal": None,
        "second_departure_time": None,
        "second_arrival_terminal": None,
        "second_arrival_time": None,
        "source_file_name": "sample.xlsx",
        "source_row_number": 2,
    }


def test_transfer_storage_replace_and_load(tmp_path: Path) -> None:
    repo = StorageRepository(tmp_path / "transfer.sqlite3")
    repo.replace_people([_sample_record()], source_file_name="sample.xlsx", processed=1, skipped=0)
    person = repo.list_people()[0]

    block = ScheduleBlock(
        block_id="b1",
        person_id=person.id,
        person_display_name="John Doe",
        current_zone="Zone A",
        starting_companionship_key="john doe|jane roe",
        render_order=1,
        raw_text="John Doe\n\n-----------------------------------",
        source_person_updated_at=person.updated_at,
    )
    conflict = ScheduleConflict(
        conflict_id="c1",
        conflict_type="TIME_CONFLICT",
        severity="red",
        message="John Doe has a time conflict in their schedule.",
        affected_people=[person.id],
        affected_locations=["Seoul"],
        anchors=[ConflictAnchor(block_id="b1", line_start=1, line_end=1)],
    )

    meta = repo.replace_transfer_schedule(
        blocks=[block],
        conflicts=[conflict],
        generated_by_operation="create",
        source_dataset_version=1,
        source_dataset_last_imported_at=None,
        source_max_person_updated_at=person.updated_at,
        pseudo_code_version_ref="docs/transfer editor/transfer editor-pseudo-code.md",
    )
    assert meta.schedule_version == 1

    loaded_blocks = repo.load_transfer_schedule()
    loaded_conflicts = repo.load_transfer_conflicts()
    loaded_meta = repo.load_latest_transfer_meta()

    assert len(loaded_blocks) == 1
    assert loaded_blocks[0].person_id == person.id
    assert len(loaded_conflicts) == 1
    assert loaded_conflicts[0].conflict_type == "TIME_CONFLICT"
    assert loaded_meta is not None
    assert loaded_meta.conflict_count == 1


def test_transfer_storage_schedule_version_increments(tmp_path: Path) -> None:
    repo = StorageRepository(tmp_path / "transfer.sqlite3")
    repo.replace_people([_sample_record()], source_file_name="sample.xlsx", processed=1, skipped=0)
    person = repo.list_people()[0]

    def publish(block_id: str) -> int:
        block = ScheduleBlock(
            block_id=block_id,
            person_id=person.id,
            person_display_name="John Doe",
            current_zone="Zone A",
            starting_companionship_key="john doe|jane roe",
            render_order=1,
            raw_text="John Doe\n\n-----------------------------------",
            source_person_updated_at=person.updated_at,
        )
        meta = repo.replace_transfer_schedule(
            blocks=[block],
            conflicts=[],
            generated_by_operation="create",
            source_dataset_version=1,
            source_dataset_last_imported_at=None,
            source_max_person_updated_at=person.updated_at,
            pseudo_code_version_ref="docs/transfer editor/transfer editor-pseudo-code.md",
        )
        return meta.schedule_version

    first = publish("b1")
    second = publish("b2")
    assert first == 1
    assert second == 2
