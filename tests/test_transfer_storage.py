import sqlite3
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


def test_replace_people_preserves_existing_transfer_schedule_projection(tmp_path: Path) -> None:
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
    repo.replace_transfer_schedule(
        blocks=[block],
        conflicts=[conflict],
        generated_by_operation="create",
        source_dataset_version=1,
        source_dataset_last_imported_at=None,
        source_max_person_updated_at=person.updated_at,
        pseudo_code_version_ref="docs/transfer editor/transfer editor-pseudo-code.md",
    )

    replacement = _sample_record()
    replacement["first_name"] = "Jane"
    replacement["last_name"] = "Roe"
    repo.replace_people([replacement], source_file_name="replacement.xlsx", processed=1, skipped=0)

    assert len(repo.load_transfer_schedule()) == 1
    assert len(repo.load_transfer_conflicts()) == 1
    assert repo.load_latest_transfer_meta() is not None


def test_clear_dataset_clears_transfer_schedule_projection(tmp_path: Path) -> None:
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
    repo.replace_transfer_schedule(
        blocks=[block],
        conflicts=[],
        generated_by_operation="create",
        source_dataset_version=1,
        source_dataset_last_imported_at=None,
        source_max_person_updated_at=person.updated_at,
        pseudo_code_version_ref="docs/transfer editor/transfer editor-pseudo-code.md",
    )

    repo.clear_dataset()

    assert repo.load_transfer_schedule() == []
    assert repo.load_transfer_conflicts() == []
    assert repo.load_latest_transfer_meta() is None


def test_storage_migrates_legacy_transfer_blocks_schema(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy_transfer.sqlite3"
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE transfer_schedule_blocks (
                block_id TEXT PRIMARY KEY,
                schedule_version INTEGER NOT NULL,
                person_id TEXT NOT NULL,
                person_display_name TEXT NOT NULL,
                current_zone TEXT,
                starting_companionship_key TEXT NOT NULL,
                render_order INTEGER NOT NULL,
                raw_text TEXT NOT NULL,
                source_person_updated_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            INSERT INTO transfer_schedule_blocks(
                block_id, schedule_version, person_id, person_display_name, current_zone,
                starting_companionship_key, render_order, raw_text, source_person_updated_at, created_at, updated_at
            ) VALUES (
                'legacy-b1', 1, 'person-1', 'Legacy Person', 'Zone A',
                'legacy-key', 1, 'Legacy text', NULL, '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z'
            );
            """
        )

    repo = StorageRepository(db_path)
    rows = repo.load_transfer_schedule(schedule_version=1)
    assert len(rows) == 1
    assert rows[0].block_kind == "person"
    assert rows[0].person_id == "person-1"

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        columns = {row["name"]: row for row in conn.execute("PRAGMA table_info(transfer_schedule_blocks)").fetchall()}

    assert "block_kind" in columns
    assert columns["person_id"]["notnull"] == 0
    assert columns["person_display_name"]["notnull"] == 0
    assert columns["starting_companionship_key"]["notnull"] == 0
