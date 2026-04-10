from __future__ import annotations

from pathlib import Path
import re

from mission_manager.importers import parse_excel_file
from mission_manager.services import DashboardService
from mission_manager.storage import StorageRepository


def _workbook_path() -> Path:
    path = Path(__file__).resolve().parents[1] / "Test_excel_files" / "March 2026 Transfer Plan2.xlsm"
    assert path.exists(), f"Expected workbook fixture at {path}"
    return path


def test_march_2026_workbook_parses_and_flags_third_leg_warning() -> None:
    parsed = parse_excel_file(str(_workbook_path()))

    assert not parsed.errors
    assert len(parsed.records) == 112
    assert parsed.records_processed == 112
    assert parsed.records_skipped == 0
    assert any(
        warning == "Unsupported column ignored: Third Leg? (third-leg travel is not supported)."
        for warning in parsed.warnings
    )


def test_march_2026_workbook_import_and_schedule_report_missing_companion(tmp_path: Path) -> None:
    service = DashboardService(StorageRepository(tmp_path / "fixture.sqlite3"))

    result = service.import_excel(str(_workbook_path()))
    assert result.success
    assert result.records_processed == 112
    assert result.records_inserted == 112

    schedule = service.create_schedule(confirm_overwrite=True)
    assert schedule.success
    assert any(
        error.message == "Justin Sherwood (row 113, March 2026 Transfer Plan2.xlsm) references missing current companion 'Xaviah Patch'."
        for error in schedule.errors
    )

    blocks = service.get_schedule_document()
    conflicts = service.list_schedule_conflicts()

    def block_for(name: str):
        return next(
            block
            for block in blocks
            if block.block_kind == "person" and block.person_display_name == name
        )

    abraham = block_for("Abraham Astle")
    brennan = block_for("Brennan Dastrup")
    ty = block_for("Ty Beck")
    evelynn = block_for("Evelynn Fosburg")
    jenna = block_for("Jenna Mahoney")
    michelle = block_for("Michelle Pak")
    sariah = block_for("Sariah Lee")
    justin = block_for("Justin Pugmire")
    tyler = block_for("Tyler Schow")
    anders = block_for("Anders Krantz")
    yewon = block_for("Yewon Jeong")

    assert not any(
        error.message == "Abraham Astle (row 2, March 2026 Transfer Plan2.xlsm) does not have a resolvable current-companion departure anchor; manual review required."
        for error in schedule.errors
    )
    assert "ERROR:" not in abraham.raw_text
    assert "Your new companion, Sariah Jung, will arrive at 12:57." in evelynn.raw_text
    assert "Drop off" not in evelynn.raw_text
    assert "Your new companion, Sariah Jung, will arrive at 12:57." in jenna.raw_text
    assert "Notes: Your companion Ty Beck will be waiting for you." in brennan.raw_text
    assert "Drop off Ethan Talbot at 익산시외버스터미널." in ty.raw_text
    assert "Wait at 익산시외버스터미널 until your new companion, Brennan Dastrup, arrives there at 11:32." in ty.raw_text
    assert "Your new companion, Sariah Lee, will be waiting." in michelle.raw_text
    assert "Your new companion, Michelle Pak, will be waiting." in sariah.raw_text
    assert "Notes: Upon arrival, your companion Tyler Schow will be waiting for you." in justin.raw_text
    assert "Drop off Dallan Owens at Thug it out buddy." in tyler.raw_text
    assert "will be waiting" not in tyler.raw_text
    assert "[New companion is arriving at 전주고속버스터미널]" in tyler.raw_text
    assert "Drop off Jake Matildo at 수원역." in anders.raw_text
    assert "Drop off Deakan Richeson at 수원 버스터미널. Wait at 수원 버스터미널 until your new companion, Cameron Spilker, arrives there at 14:24." in anders.raw_text
    assert "Drop off Zyra Pacaldo at 성남 버스 터미널." in yewon.raw_text
    assert "[New companion is arriving at 죽전역]" in yewon.raw_text
    assert "Please communicate with your new companion to determine a meetup time in advance." in yewon.raw_text
    assert "will be waiting" not in yewon.raw_text
    assert "ERROR:" not in yewon.raw_text
    assert "subway " not in michelle.raw_text.lower()
    assert not any("Both companions are available at the same time." in block.raw_text for block in blocks)
    assert not any("Both companions fell back to 00:00." in block.raw_text for block in blocks)
    assert not any(
        conflict.conflict_type == "TIME_CONFLICT"
        and conflict.message == "Dallin Farr has a time conflict in their schedule."
        for conflict in conflicts
    )
    assert not any(
        conflict.conflict_type == "TIME_CONFLICT"
        and conflict.message == "Aizlyn Owen has a time conflict in their schedule."
        for conflict in conflicts
    )
    assert not any(
        conflict.conflict_type == "TIME_CONFLICT"
        and conflict.message == "Keira Arnold has a time conflict in their schedule."
        for conflict in conflicts
    )
    assert not any(
        conflict.conflict_type == "TIME_CONFLICT"
        and conflict.message == "Ellie Cardiff has a time conflict in their schedule."
        for conflict in conflicts
    )
    assert not any(
        conflict.conflict_type == "TIME_CONFLICT"
        and conflict.message == "Sophie Bowen has a time conflict in their schedule."
        for conflict in conflicts
    )
    assert any(
        conflict.conflict_type == "HANDOFF_REVIEW"
        and "manual inspection required because companions are leaving from different terminals"
        in conflict.message.lower()
        for conflict in conflicts
    )
    assert any(
        conflict.conflict_type == "HANDOFF_REVIEW"
        and "companion pickup error" in conflict.message.lower()
        and "Thug it out buddy" in conflict.affected_locations
        and "전주고속버스터미널" in conflict.affected_locations
        for conflict in conflicts
    )
    assert any(
        conflict.conflict_type == "HANDOFF_REVIEW"
        and "companion pickup error" in conflict.message.lower()
        and "성남 버스 터미널" in conflict.affected_locations
        and "죽전역" in conflict.affected_locations
        for conflict in conflicts
    )
    pickup_conflicts = [
        conflict
        for conflict in conflicts
        if conflict.conflict_type == "HANDOFF_REVIEW" and "companion pickup error" in conflict.message.lower()
    ]
    assert len(pickup_conflicts) == 11
    combined_text = "\n".join(
        block.raw_text.rstrip("\n")
        for block in sorted(blocks, key=lambda block: block.render_order)
    )
    assert not re.search(r"\b\d{2}:\d{2}:\d{2}\b", combined_text)
