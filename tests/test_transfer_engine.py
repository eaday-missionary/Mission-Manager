from mission_manager.models import PersonRecord
from mission_manager.transfer_engine import (
    render_transfer_schedule,
    split_companion_names,
)


def _person(
    *,
    pid: str,
    first: str,
    last: str,
    current_companion: str | None = None,
    new_companion: str | None = None,
    zone: str = "Zone A",
    area: str = "Area 1",
    new_zone: str = "Zone B",
    new_area: str = "Area 2",
    staying: bool | None = False,
    pre_travel: str | None = None,
    dep_terminal: str | None = "Seoul Station",
    dep_time: str | None = "08:00",
    arr_terminal: str | None = "Busan Station",
    arr_time: str | None = "10:00",
    second_leg: bool | None = False,
    dep2_terminal: str | None = None,
    dep2_time: str | None = None,
    arr2_terminal: str | None = None,
    arr2_time: str | None = None,
    updated_at: str | None = None,
) -> PersonRecord:
    return PersonRecord(
        id=pid,
        first_name=first,
        last_name=last,
        current_companion=current_companion,
        new_companion=new_companion,
        current_zone=zone,
        current_area=area,
        new_zone=new_zone,
        new_area=new_area,
        staying=staying,
        pre_travel=pre_travel,
        departure_terminal=dep_terminal,
        departure_time=dep_time,
        arrival_terminal=arr_terminal,
        arrival_time=arr_time,
        second_leg=second_leg,
        second_departure_terminal=dep2_terminal,
        second_departure_time=dep2_time,
        second_arrival_terminal=arr2_terminal,
        second_arrival_time=arr2_time,
        updated_at=updated_at,
    )


def test_render_transfer_schedule_includes_required_separator_and_order() -> None:
    people = [
        _person(pid="1", first="John", last="Doe", current_companion="Jane Roe"),
        _person(pid="2", first="Jane", last="Roe", current_companion="John Doe"),
    ]
    result = render_transfer_schedule(people)
    assert not result.errors
    assert len(result.blocks) == 2
    assert result.blocks[0].raw_text.endswith("-----------------------------------")
    assert abs(result.blocks[0].render_order - result.blocks[1].render_order) == 1


def test_render_transfer_schedule_missing_time_uses_0000() -> None:
    people = [
        _person(
            pid="1",
            first="Alex",
            last="Kim",
            staying=True,
            current_companion="Ben Park",
            new_companion="Chris Lee",
            dep_terminal="Seoul Station",
            dep_time="07:00",
            arr_terminal="Daegu",
            arr_time="09:00",
        ),
        _person(
            pid="2",
            first="Ben",
            last="Park",
            current_companion="Alex Kim",
            new_companion="Chris Lee",
            dep_terminal="Seoul Station",
            dep_time="08:00",
        ),
        _person(
            pid="3",
            first="Chris",
            last="Lee",
            current_companion="Dana Shin",
            dep_time=None,
            arr_time=None,
        ),
    ]
    result = render_transfer_schedule(people)
    text = "\n".join(block.raw_text for block in result.blocks)
    assert "00:00" in text


def test_render_transfer_schedule_missing_companion_produces_data_conflict() -> None:
    people = [
        _person(
            pid="1",
            first="Alex",
            last="Kim",
            current_companion="Missing Person",
            new_companion="Nobody",
            dep_terminal="Subway",
        )
    ]
    result = render_transfer_schedule(people)
    assert result.errors
    assert any(error.code == "DATA_CONFLICT" for error in result.errors)


def test_split_companion_names_supports_ampersand_and_comma() -> None:
    raw = "Alpha One, Beta Two & Gamma Three"
    assert split_companion_names(raw) == ["Alpha One", "Beta Two", "Gamma Three"]


def test_reversed_name_lookup_resolves_companions() -> None:
    people = [
        _person(
            pid="1",
            first="Alex",
            last="Kim",
            current_companion="Park Ben",
            new_companion="Lee Chris",
            dep_terminal="Subway",
            staying=False,
        ),
        _person(pid="2", first="Ben", last="Park", new_companion="Chris Lee"),
        _person(pid="3", first="Chris", last="Lee", dep_time="09:15"),
    ]
    result = render_transfer_schedule(people)
    actor = next(block for block in result.blocks if block.person_id == "1")
    assert "arrive there at 09:15" in actor.raw_text
    assert not any(err.code == "DATA_CONFLICT" and err.person_id == "1" for err in result.errors)


def test_nccc_time_uses_earliest_non_blank_from_all_current_companions() -> None:
    people = [
        _person(
            pid="1",
            first="Actor",
            last="One",
            current_companion="Beta Two, Gamma Three",
            dep_terminal="Subway",
            staying=False,
        ),
        _person(pid="2", first="Beta", last="Two", new_companion="Echo Five"),
        _person(pid="3", first="Gamma", last="Three", new_companion="Foxtrot Six"),
        _person(pid="4", first="Echo", last="Five", dep_time="11:00"),
        _person(pid="5", first="Foxtrot", last="Six", dep_time="09:00"),
    ]
    result = render_transfer_schedule(people)
    actor = next(block for block in result.blocks if block.person_id == "1")
    assert "arrive there at 09:00" in actor.raw_text


def test_nccc_time_uses_0000_only_when_no_candidate_time_exists() -> None:
    people = [
        _person(
            pid="1",
            first="Actor",
            last="One",
            current_companion="Beta Two & Gamma Three",
            dep_terminal="Subway",
            staying=False,
        ),
        _person(pid="2", first="Beta", last="Two", new_companion="Echo Five"),
        _person(pid="3", first="Gamma", last="Three", new_companion="Foxtrot Six"),
        _person(pid="4", first="Echo", last="Five", dep_time=None),
        _person(pid="5", first="Foxtrot", last="Six", dep_time=None),
    ]
    result = render_transfer_schedule(people)
    actor = next(block for block in result.blocks if block.person_id == "1")
    assert "arrive there at 00:00" in actor.raw_text
