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
    title: str | None = None,
) -> PersonRecord:
    return PersonRecord(
        id=pid,
        first_name=first,
        last_name=last,
        title=title,
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


def _person_blocks(raw_result) -> list:
    return [block for block in raw_result.blocks if block.block_kind == "person"]


def test_render_transfer_schedule_emits_zone_area_headers_and_15_dash_separator() -> None:
    people = [
        _person(
            pid="1",
            first="John",
            last="Doe",
            current_companion="Jane Roe",
            zone="Zone Alpha",
            area="Area East",
        ),
        _person(
            pid="2",
            first="Jane",
            last="Roe",
            current_companion="John Doe",
            zone="Zone Alpha",
            area="Area East",
        ),
    ]
    result = render_transfer_schedule(people)

    assert not result.errors
    assert result.blocks[0].block_kind == "zone_header"
    assert result.blocks[0].raw_text == "---Zone Alpha---"
    assert result.blocks[1].block_kind == "area_header"
    assert result.blocks[1].raw_text == "------------------------- Area East -------------------------"

    person_blocks = _person_blocks(result)
    assert len(person_blocks) == 2
    assert all(block.raw_text.endswith("---------------") for block in person_blocks)


def test_render_transfer_schedule_preserves_zone_first_appearance_order() -> None:
    people = [
        _person(pid="1", first="A", last="One", zone="Zone B", area="Area 1"),
        _person(pid="2", first="B", last="Two", zone="Zone A", area="Area 2"),
        _person(pid="3", first="C", last="Three", zone="Zone B", area="Area 3"),
    ]
    result = render_transfer_schedule(people)
    zone_headers = [block.raw_text for block in result.blocks if block.block_kind == "zone_header"]
    assert zone_headers == ["---Zone B---", "---Zone A---"]


def test_render_transfer_schedule_subway_contains_cleans_route_text() -> None:
    people = [
        _person(
            pid="1",
            first="Alex",
            last="Kim",
            current_companion="Ben Park",
            new_companion="Chris Lee",
            dep_terminal="Suji Subway",
            dep_time="yellow",
            arr_terminal="Seoul Subway",
            arr_time="09:30",
        ),
        _person(pid="2", first="Ben", last="Park", current_companion="Alex Kim"),
        _person(pid="3", first="Chris", last="Lee", current_companion="Dana Shin"),
    ]
    result = render_transfer_schedule(people)
    actor = next(block for block in result.blocks if block.person_id == "1")
    assert "Travel to Suji with Ben Park." in actor.raw_text
    assert "Travel to Suji Subway with Ben Park." not in actor.raw_text
    assert "Travel to Suji and ride the yellow to Seoul. Leave in time to arrive there at 09:30." in actor.raw_text
    assert "There, you will meet your new companion, Chris Lee." in actor.raw_text
    assert "Travel to Suji Subway and ride the yellow to Seoul Subway." not in actor.raw_text


def test_render_transfer_schedule_second_leg_subway_uses_second_leg_fields() -> None:
    people = [
        _person(
            pid="1",
            first="Alex",
            last="Kim",
            current_companion="Ben Park",
            new_companion="Chris Lee",
            dep_terminal="Seoul Station",
            arr_terminal="Daegu",
            arr_time="10:00",
            second_leg=True,
            dep2_terminal="Daejeon Subway",
            dep2_time="blue",
            arr2_terminal="Busan Subway",
            arr2_time="13:15",
        ),
        _person(pid="2", first="Ben", last="Park", current_companion="Alex Kim"),
        _person(pid="3", first="Chris", last="Lee", current_companion="Dana Shin"),
    ]
    result = render_transfer_schedule(people)
    actor = next(block for block in result.blocks if block.person_id == "1")
    assert "Second leg of travel:" in actor.raw_text
    assert "Travel to Daejeon and ride the blue to Busan. Leave in time to arrive there at 13:15" in actor.raw_text
    assert "line to Busan" not in actor.raw_text


def test_render_transfer_schedule_subway_line_uses_dash_when_departure_time_missing() -> None:
    people = [
        _person(
            pid="1",
            first="Alex",
            last="Kim",
            current_companion="Ben Park",
            new_companion="Chris Lee",
            dep_terminal="Suji Subway",
            dep_time="",
            arr_terminal="Seoul Subway",
            arr_time="09:30",
        ),
        _person(pid="2", first="Ben", last="Park", current_companion="Alex Kim"),
        _person(pid="3", first="Chris", last="Lee", current_companion="Dana Shin"),
    ]
    result = render_transfer_schedule(people)
    actor = next(block for block in result.blocks if block.person_id == "1")
    assert "ride the - to" in actor.raw_text


def test_render_transfer_schedule_rule15_warning_renders_under_name_with_spacing() -> None:
    people = [
        _person(
            pid="1",
            first="Alex",
            last="Kim",
            current_companion="Ben Park",
            dep_terminal="Seoul Station",
            dep_time=None,
            arr_time=None,
        ),
        _person(pid="2", first="Ben", last="Park", current_companion="Alex Kim"),
    ]
    result = render_transfer_schedule(people)
    actor = next(block for block in result.blocks if block.person_id == "1")
    lines = actor.raw_text.splitlines()
    assert lines[0] == "Alex Kim"
    assert lines[1] == ""
    assert lines[2] == "WARNING - You must purchase the Seoul Station ticket in person"
    assert lines[3] == ""
    assert lines[4] == "Travel to Seoul Station with Ben Park."


def test_render_transfer_schedule_rule16_warning_requires_second_leg() -> None:
    people = [
        _person(
            pid="1",
            first="Alex",
            last="Kim",
            current_companion="Ben Park",
            second_leg=False,
            dep2_terminal="Daejeon",
            dep2_time=None,
            arr2_time=None,
        ),
        _person(pid="2", first="Ben", last="Park", current_companion="Alex Kim"),
    ]
    result = render_transfer_schedule(people)
    actor = next(block for block in result.blocks if block.person_id == "1")
    assert "WARNING - You must purchase the Daejeon ticket in person" not in actor.raw_text


def test_render_transfer_schedule_rule15_and_rule16_precede_bus_warning() -> None:
    people = [
        _person(
            pid="1",
            first="Alex",
            last="Kim",
            current_companion="Ben Park",
            new_companion="Chris Lee",
            dep_terminal="Suji Subway",
            dep_time=None,
            arr_terminal="Seoul Subway",
            arr_time=None,
            second_leg=True,
            dep2_terminal="Daejeon Subway",
            dep2_time=None,
            arr2_terminal="Busan Subway",
            arr2_time=None,
        ),
        _person(pid="2", first="Ben", last="Park", current_companion="Alex Kim"),
        _person(pid="3", first="Chris", last="Lee", current_companion="Dana Shin"),
    ]
    result = render_transfer_schedule(people)
    actor = next(block for block in result.blocks if block.person_id == "1")
    text = actor.raw_text
    first_warning = "WARNING - You must purchase the Suji ticket in person"
    second_warning = "WARNING - You must purchase the Daejeon ticket in person"
    bus_warning = "!!!!! Make sure your bus card is filled up BEFORE transfer day !!!!!"
    assert first_warning in text
    assert second_warning in text
    assert bus_warning in text
    assert text.index(first_warning) < text.index(second_warning) < text.index(bus_warning)
    assert "There, you will meet your new companion" not in text
    lines = text.splitlines()
    assert lines[0] == "Alex Kim"
    assert lines[1] == ""
    assert lines[2] == first_warning
    assert lines[3] == ""
    assert lines[4] == second_warning
    assert lines[5] == ""
    assert lines[6] == bus_warning
    assert lines[7] == ""


def test_render_transfer_schedule_no_ticket_warning_when_cleanup_results_in_blank_terminal() -> None:
    people = [
        _person(
            pid="1",
            first="Alex",
            last="Kim",
            current_companion="Ben Park",
            dep_terminal="Subway",
            dep_time=None,
            arr_time=None,
        ),
        _person(pid="2", first="Ben", last="Park", current_companion="Alex Kim"),
    ]
    result = render_transfer_schedule(people)
    actor = next(block for block in result.blocks if block.person_id == "1")
    assert "WARNING - You must purchase" not in actor.raw_text


def test_render_transfer_schedule_rule16_warning_appears_when_new_zone_contains_subway() -> None:
    people = [
        _person(
            pid="1",
            first="Alex",
            last="Kim",
            current_companion="Ben Park",
            new_zone="Gangnam subway Transfer",
            dep_terminal="Subway",
            second_leg=True,
            dep2_terminal="Daejeon",
            dep2_time=None,
            arr2_time=None,
        ),
        _person(pid="2", first="Ben", last="Park", current_companion="Alex Kim"),
    ]
    result = render_transfer_schedule(people)
    actor = next(block for block in result.blocks if block.person_id == "1")
    assert "WARNING - You must purchase the Daejeon ticket in person" in actor.raw_text
    assert "Arrive at the mission office before 10:45." in actor.raw_text
    assert "!!!!! Make sure your bus card is filled up BEFORE transfer day !!!!!" not in actor.raw_text


def test_render_transfer_schedule_rule15_warning_appears_on_staying_early_return() -> None:
    people = [
        _person(
            pid="1",
            first="Alex",
            last="Kim",
            current_companion="Ben Park",
            new_companion="Chris Lee",
            staying=True,
            dep_terminal="Seoul Station",
            dep_time=None,
            arr_time=None,
        ),
        _person(pid="2", first="Ben", last="Park", current_companion="Alex Kim"),
        _person(pid="3", first="Chris", last="Lee", current_companion="Dana Shin"),
    ]
    result = render_transfer_schedule(people)
    actor = next(block for block in result.blocks if block.person_id == "1")
    assert "WARNING - You must purchase the Seoul Station ticket in person" in actor.raw_text
    assert actor.raw_text.endswith("---------------")


def test_render_transfer_schedule_second_leg_mismatch_warning_has_blank_line_after() -> None:
    people = [
        _person(
            pid="1",
            first="Alex",
            last="Kim",
            current_companion="Ben Park",
            new_companion="Chris Lee",
            dep_terminal="Seoul Station",
            arr_terminal="Daegu",
            arr_time="10:00",
            second_leg=True,
            dep2_terminal="Daejeon",
            dep2_time="11:00",
            arr2_terminal="Busan",
            arr2_time="13:00",
        ),
        _person(pid="2", first="Ben", last="Park", current_companion="Alex Kim"),
        _person(pid="3", first="Chris", last="Lee", current_companion="Dana Shin"),
    ]
    result = render_transfer_schedule(people)
    actor = next(block for block in result.blocks if block.person_id == "1")
    assert "WARNING You need to travel to Daejeon for your second leg of travel.\n\nSecond leg of travel:" in actor.raw_text


def test_render_transfer_schedule_area_header_suffix_for_all_s_titles() -> None:
    people = [
        _person(
            pid="1",
            first="Mina",
            last="Kim",
            current_companion="Sara Park",
            zone="Zone A",
            area="분당 E2",
            title="S",
        ),
        _person(
            pid="2",
            first="Sara",
            last="Park",
            current_companion="Mina Kim",
            zone="Zone A",
            area="분당 E2",
            title="S",
        ),
    ]
    result = render_transfer_schedule(people)
    area_headers = [block.raw_text for block in result.blocks if block.block_kind == "area_header"]
    assert area_headers == ["------------------------- 분당 E2 S -------------------------"]


def test_render_transfer_schedule_area_header_suffix_for_all_e_titles() -> None:
    people = [
        _person(
            pid="1",
            first="John",
            last="Cho",
            current_companion="Paul Lee",
            zone="Zone A",
            area="안양 E1",
            title="E",
        ),
        _person(
            pid="2",
            first="Paul",
            last="Lee",
            current_companion="John Cho",
            zone="Zone A",
            area="안양 E1",
            title="E",
        ),
    ]
    result = render_transfer_schedule(people)
    area_headers = [block.raw_text for block in result.blocks if block.block_kind == "area_header"]
    assert area_headers == ["------------------------- 안양 E1 E -------------------------"]


def test_render_transfer_schedule_area_header_has_no_suffix_for_invalid_or_mixed_titles() -> None:
    people = [
        _person(
            pid="1",
            first="A",
            last="One",
            current_companion="B Two",
            zone="Zone A",
            area="분당 E2",
            title="S",
        ),
        _person(
            pid="2",
            first="B",
            last="Two",
            current_companion="A One",
            zone="Zone A",
            area="분당 E2",
            title="X",
        ),
    ]
    result = render_transfer_schedule(people)
    area_headers = [block.raw_text for block in result.blocks if block.block_kind == "area_header"]
    assert area_headers == ["------------------------- 분당 E2 -------------------------"]


def test_render_transfer_schedule_clusters_same_hangul_area_families_adjacent() -> None:
    people = [
        _person(pid="1", first="A", last="One", current_companion="B Two", zone="Zone A", area="분당 E2"),
        _person(pid="2", first="B", last="Two", current_companion="A One", zone="Zone A", area="분당 E2"),
        _person(pid="3", first="C", last="Three", current_companion="D Four", zone="Zone A", area="안양 E1"),
        _person(pid="4", first="D", last="Four", current_companion="C Three", zone="Zone A", area="안양 E1"),
        _person(pid="5", first="E", last="Five", current_companion="F Six", zone="Zone A", area="1 분당 E1"),
        _person(pid="6", first="F", last="Six", current_companion="E Five", zone="Zone A", area="1 분당 E1"),
    ]
    result = render_transfer_schedule(people)
    area_headers = [block.raw_text for block in result.blocks if block.block_kind == "area_header"]
    assert area_headers == [
        "------------------------- 분당 E2 -------------------------",
        "------------------------- 1 분당 E1 -------------------------",
        "------------------------- 안양 E1 -------------------------",
    ]


def test_render_transfer_schedule_no_hangul_fallback_clusters_exact_area_names() -> None:
    people = [
        _person(pid="1", first="A", last="One", current_companion="B Two", zone="Zone A", area="Area East"),
        _person(pid="2", first="B", last="Two", current_companion="A One", zone="Zone A", area="Area East"),
        _person(pid="3", first="C", last="Three", current_companion="D Four", zone="Zone A", area="Area West"),
        _person(pid="4", first="D", last="Four", current_companion="C Three", zone="Zone A", area="Area West"),
        _person(pid="5", first="E", last="Five", current_companion="F Six", zone="Zone A", area="Area East"),
        _person(pid="6", first="F", last="Six", current_companion="E Five", zone="Zone A", area="Area East"),
    ]
    result = render_transfer_schedule(people)
    area_headers = [block.raw_text for block in result.blocks if block.block_kind == "area_header"]
    assert area_headers == [
        "------------------------- Area East -------------------------",
        "------------------------- Area East -------------------------",
        "------------------------- Area West -------------------------",
    ]


def test_render_transfer_schedule_blank_departure_step7_uses_dash_placeholder() -> None:
    people = [
        _person(
            pid="1",
            first="Alex",
            last="Kim",
            current_companion="Ben Park",
            dep_terminal="-",
            staying=False,
        ),
        _person(
            pid="2",
            first="Ben",
            last="Park",
            current_companion="Alex Kim",
            dep_terminal="Seoul Station",
        ),
    ]
    result = render_transfer_schedule(people)
    actor = next(block for block in result.blocks if block.person_id == "1")
    assert "Travel to - with Ben Park." in actor.raw_text


def test_render_transfer_schedule_blank_departure_prints_fighting_when_current_equals_new_companion() -> None:
    people = [
        _person(
            pid="1",
            first="Alex",
            last="Kim",
            current_companion="Ben Park",
            new_companion="Ben Park",
            dep_terminal="-",
            staying=False,
        ),
        _person(
            pid="2",
            first="Ben",
            last="Park",
            current_companion="Alex Kim",
            dep_terminal="Seoul Station",
        ),
    ]
    result = render_transfer_schedule(people)
    actor = next(block for block in result.blocks if block.person_id == "1")
    assert "화이팅!!!" in actor.raw_text
    assert "Travel to - with" not in actor.raw_text


def test_render_transfer_schedule_blank_departure_does_not_print_fighting_when_current_differs_from_new() -> None:
    people = [
        _person(
            pid="1",
            first="Alex",
            last="Kim",
            current_companion="Ben Park",
            new_companion="Chris Lee",
            dep_terminal="-",
            staying=False,
        ),
        _person(
            pid="2",
            first="Ben",
            last="Park",
            current_companion="Alex Kim",
            dep_terminal="-",
        ),
        _person(
            pid="3",
            first="Chris",
            last="Lee",
            current_companion="Dana Shin",
            dep_terminal="-",
        ),
    ]
    result = render_transfer_schedule(people)
    actor = next(block for block in result.blocks if block.person_id == "1")
    assert "화이팅!!!" not in actor.raw_text
    assert "Travel to - with Ben Park." in actor.raw_text


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
    text = "\n".join(block.raw_text for block in _person_blocks(result))
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


def test_render_transfer_schedule_trainee_rows_are_rendered_without_lookup_error() -> None:
    people = [
        _person(
            pid="1",
            first="Trainee",
            last="",
            current_companion="Trainee",
            new_companion="Trainee",
            zone="Zone A",
            area="Area T",
        ),
        _person(
            pid="2",
            first="Alex",
            last="Kim",
            current_companion="Trainee",
            new_companion="Trainee",
            zone="Zone A",
            area="Area T",
        ),
    ]
    result = render_transfer_schedule(people)
    person_ids = {block.person_id for block in _person_blocks(result)}
    assert "1" in person_ids
    assert "2" in person_ids
    assert not any(err.code == "DATA_CONFLICT" and err.field == "current_companion" for err in result.errors)
