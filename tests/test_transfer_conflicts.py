from mission_manager.models import PersonRecord, ScheduleError
from mission_manager.transfer_conflicts import detect_transfer_conflicts
from mission_manager.transfer_engine import render_transfer_schedule


def _person(
    *,
    pid: str,
    first: str,
    last: str,
    current_companion: str | None = None,
    zone: str = "Zone A",
    staying: bool | None = False,
    dep_terminal: str | None = "Seoul",
    dep_time: str | None = "08:00",
    arr_terminal: str | None = "Busan",
    arr_time: str | None = "09:00",
    second_leg: bool | None = False,
    dep2_terminal: str | None = None,
    dep2_time: str | None = None,
) -> PersonRecord:
    return PersonRecord(
        id=pid,
        first_name=first,
        last_name=last,
        current_companion=current_companion,
        new_companion=None,
        current_zone=zone,
        current_area="Area 1",
        new_zone="Zone B",
        new_area="Area 2",
        staying=staying,
        pre_travel=None,
        departure_terminal=dep_terminal,
        departure_time=dep_time,
        arrival_terminal=arr_terminal,
        arrival_time=arr_time,
        second_leg=second_leg,
        second_departure_terminal=dep2_terminal,
        second_departure_time=dep2_time,
        second_arrival_terminal=None,
        second_arrival_time=None,
    )


def test_detect_transfer_conflicts_time_and_location() -> None:
    people = [
        _person(
            pid="1",
            first="John",
            last="Doe",
            current_companion="Jane Roe",
            dep_terminal="Seoul",
            dep_time="07:30",
            arr_terminal="Gwangju",
            arr_time="12:00",
            second_leg=True,
            dep2_terminal="Busan",
            dep2_time="11:45",
        ),
        _person(
            pid="2",
            first="Jane",
            last="Roe",
            current_companion="John Doe",
            dep_terminal="Seoul",
            dep_time="08:00",
            arr_terminal="Daegu",
            arr_time="10:00",
        ),
    ]
    rendered = render_transfer_schedule(people)
    conflicts = detect_transfer_conflicts(people, rendered.blocks, rendered.errors)
    assert any(conflict.conflict_type == "TIME_CONFLICT" for conflict in conflicts)
    assert any(conflict.conflict_type == "LOCATION_CONFLICT" for conflict in conflicts)
    assert all(conflict.anchors for conflict in conflicts)


def test_detect_transfer_conflicts_includes_data_conflicts() -> None:
    people = [
        _person(pid="1", first="A", last="One", current_companion="Missing Person")
    ]
    rendered = render_transfer_schedule(people)
    extra_error = ScheduleError(
        code="DATA_CONFLICT",
        message="Companion row not found.",
        person_id="1",
        field="current_companion",
    )
    conflicts = detect_transfer_conflicts(
        people, rendered.blocks, rendered.errors + [extra_error]
    )
    assert any(conflict.conflict_type == "DATA_CONFLICT" for conflict in conflicts)


def test_detect_transfer_conflicts_handles_reversed_companion_name_lookup() -> None:
    people = [
        _person(
            pid="1",
            first="John",
            last="Doe",
            current_companion="Roe Jane",
            dep_terminal="Seoul",
            dep_time="07:30",
        ),
        _person(
            pid="2",
            first="Jane",
            last="Roe",
            current_companion="John Doe",
            dep_terminal="Seoul",
            dep_time="08:00",
        ),
    ]
    rendered = render_transfer_schedule(people)
    conflicts = detect_transfer_conflicts(people, rendered.blocks, rendered.errors)
    assert any(conflict.conflict_type == "TIME_CONFLICT" for conflict in conflicts)


def test_detect_transfer_conflicts_skips_non_time_departure_tokens() -> None:
    people = [
        _person(
            pid="1",
            first="John",
            last="Doe",
            current_companion="Jane Roe",
            dep_time="yellow",
        ),
        _person(
            pid="2",
            first="Jane",
            last="Roe",
            current_companion="John Doe",
            dep_time="08:00",
        ),
    ]
    rendered = render_transfer_schedule(people)
    conflicts = detect_transfer_conflicts(people, rendered.blocks, rendered.errors)
    assert not any(conflict.conflict_type == "TIME_CONFLICT" for conflict in conflicts)
