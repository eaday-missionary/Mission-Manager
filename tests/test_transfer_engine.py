from mission_manager.models import PersonRecord
from mission_manager.transfer_engine import (
    _parse_time_minutes,
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


def test_render_transfer_schedule_suji_training_early_return_requires_exact_zone_match() -> None:
    people = [
        _person(
            pid="1",
            first="Alex",
            last="Kim",
            current_companion="Ben Park",
            new_zone="수지 Training",
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
    assert "Travel to -" not in actor.raw_text


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


def test_parse_time_minutes_accepts_hh_mm_ss() -> None:
    assert _parse_time_minutes("08:00:00") == 8 * 60


def test_render_transfer_schedule_formats_parseable_times_to_hh_mm() -> None:
    people = [
        _person(
            pid="1",
            first="Alex",
            last="Kim",
            current_companion="Ben Park",
            new_companion="Chris Lee",
            dep_terminal="Seoul Station",
            dep_time="08:30:00",
            arr_terminal="Busan Station",
            arr_time="09:45:59",
            second_leg=True,
            dep2_terminal="Daejeon Station",
            dep2_time="11:00:00",
            arr2_terminal="Daegu Station",
            arr2_time="12:05:01",
        ),
        _person(pid="2", first="Ben", last="Park", current_companion="Alex Kim"),
        _person(pid="3", first="Chris", last="Lee", current_companion="Dana Shin"),
    ]
    result = render_transfer_schedule(people)
    actor = next(block for block in result.blocks if block.person_id == "1")

    assert "08:30:00" not in actor.raw_text
    assert "09:45:59" not in actor.raw_text
    assert "11:00:00" not in actor.raw_text
    assert "12:05:01" not in actor.raw_text
    assert "Departure Time: 08:30" in actor.raw_text
    assert "Arrival Time: 09:45" in actor.raw_text
    assert "Departure Time: 11:00" in actor.raw_text
    assert "Arrival Time: 12:05" in actor.raw_text


def test_render_transfer_schedule_staying_person_waits_when_new_companion_arrives_later() -> None:
    people = [
        _person(
            pid="1",
            first="Alex",
            last="Kim",
            current_companion="Ben Park",
            new_companion="Chris Lee",
            staying=True,
            dep_terminal="-",
        ),
        _person(
            pid="2",
            first="Ben",
            last="Park",
            current_companion="Alex Kim",
            dep_terminal="Seoul Station",
            dep_time="08:00:00",
        ),
        _person(
            pid="3",
            first="Chris",
            last="Lee",
            current_companion="Dana Shin",
            arr_terminal="Seoul Station",
            arr_time="09:15",
        ),
        _person(pid="4", first="Dana", last="Shin", current_companion="Chris Lee"),
    ]
    result = render_transfer_schedule(people)
    actor = next(block for block in result.blocks if block.person_id == "1")
    assert (
        "Drop off Ben Park at Seoul Station. Wait at Seoul Station until your new companion, Chris Lee, arrives there at 09:15."
        in actor.raw_text
    )


def test_render_transfer_schedule_staying_person_new_companion_can_already_be_waiting() -> None:
    people = [
        _person(
            pid="1",
            first="Alex",
            last="Kim",
            current_companion="Ben Park",
            new_companion="Chris Lee",
            staying=True,
            dep_terminal="-",
        ),
        _person(
            pid="2",
            first="Ben",
            last="Park",
            current_companion="Alex Kim",
            dep_terminal="Seoul Station",
            dep_time="08:00:00",
        ),
        _person(
            pid="3",
            first="Chris",
            last="Lee",
            current_companion="Dana Shin",
            arr_terminal="Seoul Station",
            arr_time="07:30",
        ),
        _person(pid="4", first="Dana", last="Shin", current_companion="Chris Lee"),
    ]
    result = render_transfer_schedule(people)
    actor = next(block for block in result.blocks if block.person_id == "1")
    assert "Drop off Ben Park at Seoul Station. Your new companion, Chris Lee, will be waiting." in actor.raw_text


def test_render_transfer_schedule_same_time_handoff_resolves_to_will_be_waiting() -> None:
    people = [
        _person(
            pid="1",
            first="Alex",
            last="Kim",
            current_companion="Ben Park",
            new_companion="Chris Lee",
            staying=True,
            dep_terminal="-",
        ),
        _person(
            pid="2",
            first="Ben",
            last="Park",
            current_companion="Alex Kim",
            dep_terminal="Seoul Station",
            dep_time="08:00:00",
        ),
        _person(
            pid="3",
            first="Chris",
            last="Lee",
            current_companion="Dana Shin",
            arr_terminal="Seoul Station",
            arr_time="08:00",
        ),
        _person(pid="4", first="Dana", last="Shin", current_companion="Chris Lee"),
    ]
    result = render_transfer_schedule(people)
    actor = next(block for block in result.blocks if block.person_id == "1")
    assert "Your new companion, Chris Lee, will be waiting." in actor.raw_text
    assert "Both companions are available at the same time." not in actor.raw_text


def test_render_transfer_schedule_double_fallback_handoff_stays_silent() -> None:
    people = [
        _person(
            pid="1",
            first="Alex",
            last="Kim",
            current_companion="Ben Park",
            new_companion="Chris Lee",
            staying=True,
            dep_terminal="-",
        ),
        _person(
            pid="2",
            first="Ben",
            last="Park",
            current_companion="Alex Kim",
            dep_terminal="Seoul Station",
            dep_time=None,
        ),
        _person(
            pid="3",
            first="Chris",
            last="Lee",
            current_companion="Dana Shin",
            arr_terminal="Seoul Station",
            arr_time=None,
        ),
        _person(
            pid="4",
            first="Dana",
            last="Shin",
            current_companion="Chris Lee",
            dep_terminal="Seoul Station",
            dep_time=None,
        ),
    ]
    result = render_transfer_schedule(people)
    actor = next(block for block in result.blocks if block.person_id == "1")
    assert "Your new companion, Chris Lee, will be waiting." in actor.raw_text
    assert "Both companions fell back to 00:00." not in actor.raw_text


def test_render_transfer_schedule_staying_dropoff_cleans_subway_terminal() -> None:
    people = [
        _person(
            pid="1",
            first="Alex",
            last="Kim",
            current_companion="Ben Park",
            new_companion="Chris Lee",
            staying=True,
            dep_terminal="-",
        ),
        _person(
            pid="2",
            first="Ben",
            last="Park",
            current_companion="Alex Kim",
            dep_terminal="subway 평택역",
            dep_time="08:00",
        ),
        _person(
            pid="3",
            first="Chris",
            last="Lee",
            current_companion="Dana Shin",
            arr_time="07:30",
        ),
        _person(pid="4", first="Dana", last="Shin", current_companion="Chris Lee"),
    ]
    result = render_transfer_schedule(people)
    actor = next(block for block in result.blocks if block.person_id == "1")
    assert "Drop off Ben Park at 평택역." in actor.raw_text
    assert "subway 평택역" not in actor.raw_text.lower()


def test_render_transfer_schedule_traveler_uses_staying_new_companion_dropoff_availability() -> None:
    people = [
        _person(
            pid="1",
            first="Alex",
            last="Kim",
            current_companion="Ben Park",
            new_companion="Chris Lee",
            dep_terminal="Seoul Station",
            dep_time="07:00:00",
            arr_terminal="Busan Station",
            arr_time="08:30",
        ),
        _person(
            pid="2",
            first="Ben",
            last="Park",
            current_companion="Alex Kim",
            dep_terminal="Seoul Station",
            dep_time="07:00:00",
        ),
        _person(
            pid="3",
            first="Chris",
            last="Lee",
            current_companion="Dana Shin",
            new_companion="Alex Kim",
            staying=True,
            dep_terminal="-",
        ),
        _person(
            pid="4",
            first="Dana",
            last="Shin",
            current_companion="Chris Lee",
            dep_terminal="Busan Station",
            dep_time="09:15:00",
        ),
    ]
    result = render_transfer_schedule(people)
    actor = next(block for block in result.blocks if block.person_id == "1")
    assert "Notes: Upon arrival, wait for your companion Chris Lee who will arrive at 09:15." in actor.raw_text


def test_render_transfer_schedule_traveler_with_staying_current_companion_has_no_false_review_error() -> None:
    people = [
        _person(
            pid="1",
            first="Abraham",
            last="Astle",
            current_companion="Brian Curtis",
            new_companion="Kaleb Shearer",
            dep_terminal="Seoul Station",
            dep_time="08:00",
            arr_terminal="Busan Station",
            arr_time="09:30",
        ),
        _person(
            pid="2",
            first="Brian",
            last="Curtis",
            current_companion="Abraham Astle",
            staying=True,
            dep_terminal="-",
            dep_time=None,
            arr_terminal=None,
            arr_time=None,
        ),
        _person(
            pid="3",
            first="Kaleb",
            last="Shearer",
            current_companion="Jett Clark",
            staying=True,
            dep_terminal="-",
            dep_time=None,
            arr_terminal=None,
            arr_time=None,
        ),
        _person(pid="4", first="Jett", last="Clark", current_companion="Kaleb Shearer"),
    ]
    result = render_transfer_schedule(people)
    actor = next(block for block in result.blocks if block.person_id == "1")
    assert "ERROR:" not in actor.raw_text
    assert not any(
        err.code == "HANDOFF_REVIEW"
        and err.field == "current_companion"
        and err.person_id == "1"
        for err in result.errors
    )


def test_render_transfer_schedule_multi_name_current_companion_uses_departing_companion_reference() -> None:
    people = [
        _person(
            pid="1",
            first="Alex",
            last="Kim",
            current_companion="Aaron Able & Ben Park",
            new_companion="Chris Lee",
            staying=True,
            dep_terminal="-",
        ),
        _person(
            pid="2",
            first="Aaron",
            last="Able",
            current_companion="Alex Kim",
            dep_terminal="-",
            staying=True,
            dep_time=None,
        ),
        _person(
            pid="3",
            first="Ben",
            last="Park",
            current_companion="Alex Kim",
            dep_terminal="Busan Station",
            dep_time="08:20:00",
        ),
        _person(
            pid="4",
            first="Chris",
            last="Lee",
            current_companion="Dana Shin",
            arr_time="09:00",
        ),
        _person(pid="5", first="Dana", last="Shin", current_companion="Chris Lee"),
    ]
    result = render_transfer_schedule(people)
    actor = next(block for block in result.blocks if block.person_id == "1")
    assert (
        "Drop off Ben Park at Busan Station. Wait at Busan Station until your new companion, Chris Lee, arrives there at 09:00."
        in actor.raw_text
    )


def test_render_transfer_schedule_multi_current_companions_render_ordered_dropoffs() -> None:
    people = [
        _person(
            pid="1",
            first="Alex",
            last="Kim",
            current_companion="Aaron Able & Ben Park",
            new_companion="Chris Lee",
            staying=True,
            dep_terminal="-",
        ),
        _person(
            pid="2",
            first="Aaron",
            last="Able",
            current_companion="Alex Kim",
            dep_terminal="Busan Station",
            dep_time="08:20:00",
        ),
        _person(
            pid="3",
            first="Ben",
            last="Park",
            current_companion="Alex Kim",
            dep_terminal="Seoul Station",
            dep_time="08:20:00",
        ),
        _person(
            pid="4",
            first="Chris",
            last="Lee",
            current_companion="Dana Shin",
            arr_time="09:00",
        ),
        _person(pid="5", first="Dana", last="Shin", current_companion="Chris Lee"),
    ]
    result = render_transfer_schedule(people)
    actor = next(block for block in result.blocks if block.person_id == "1")
    assert "Drop off Ben Park at Seoul Station." in actor.raw_text
    assert (
        "Drop off Aaron Able at Busan Station. Wait at Busan Station until your new companion, Chris Lee, arrives there at 09:00."
        in actor.raw_text
    )
    assert not any(err.code == "HANDOFF_REVIEW" and err.field == "current_companion" for err in result.errors)


def test_render_transfer_schedule_ambiguous_multi_new_companion_requires_review() -> None:
    people = [
        _person(
            pid="1",
            first="Alex",
            last="Kim",
            current_companion="Ben Park",
            new_companion="Chris Lee & Dana Shin",
            staying=True,
            dep_terminal="-",
        ),
        _person(
            pid="2",
            first="Ben",
            last="Park",
            current_companion="Alex Kim",
            dep_terminal="Seoul Station",
            dep_time="08:00",
        ),
        _person(
            pid="3",
            first="Chris",
            last="Lee",
            current_companion="Evan Hall",
            arr_terminal="Busan Station",
            arr_time="09:00",
        ),
        _person(
            pid="4",
            first="Dana",
            last="Shin",
            current_companion="Frank Young",
            arr_terminal="Daegu Station",
            arr_time="09:00",
        ),
        _person(pid="5", first="Evan", last="Hall", current_companion="Chris Lee"),
        _person(pid="6", first="Frank", last="Young", current_companion="Dana Shin"),
    ]
    result = render_transfer_schedule(people)
    actor = next(block for block in result.blocks if block.person_id == "1")
    assert "ERROR:" not in actor.raw_text
    assert any(err.code == "HANDOFF_REVIEW" and err.field == "new_companion" for err in result.errors)
    assert any(
        "multiple new companions, manual confirmation required" in err.message.lower()
        for err in result.errors
    )


def test_render_transfer_schedule_staying_person_with_no_departing_current_companion_uses_arrival_only_note() -> None:
    people = [
        _person(
            pid="1",
            first="Evelynn",
            last="Fosburg",
            current_companion="Jenna Mahoney",
            new_companion="Jenna Mahoney & Sariah Jung",
            staying=True,
            dep_terminal="-",
            dep_time=None,
            arr_terminal=None,
            arr_time=None,
        ),
        _person(
            pid="2",
            first="Jenna",
            last="Mahoney",
            current_companion="Evelynn Fosburg",
            new_companion="Evelynn Fosburg & Sariah Jung",
            staying=True,
            dep_terminal="-",
            dep_time=None,
            arr_terminal=None,
            arr_time=None,
        ),
        _person(
            pid="3",
            first="Sariah",
            last="Jung",
            current_companion="Keira Arnold",
            arr_terminal="Seoul Station",
            arr_time="12:57",
        ),
        _person(pid="4", first="Keira", last="Arnold", current_companion="Sariah Jung"),
    ]
    result = render_transfer_schedule(people)
    actor = next(block for block in result.blocks if block.person_id == "1")
    assert "Your new companion, Sariah Jung, will arrive at 12:57." in actor.raw_text
    assert "Drop off" not in actor.raw_text
    assert "ERROR:" not in actor.raw_text


def test_render_transfer_schedule_fallback_time_stays_silent_without_ambiguity() -> None:
    people = [
        _person(
            pid="1",
            first="Alex",
            last="Kim",
            current_companion="Ben Park",
            new_companion="Chris Lee",
            staying=True,
            dep_terminal="-",
            dep_time=None,
            arr_terminal=None,
            arr_time=None,
        ),
        _person(
            pid="2",
            first="Ben",
            last="Park",
            current_companion="Alex Kim",
            dep_terminal="Seoul Station",
            dep_time=None,
        ),
        _person(
            pid="3",
            first="Chris",
            last="Lee",
            current_companion="Dana Shin",
            arr_terminal="Seoul Station",
            arr_time=None,
        ),
        _person(
            pid="4",
            first="Dana",
            last="Shin",
            current_companion="Chris Lee",
            dep_terminal="Seoul Station",
            dep_time=None,
        ),
    ]
    result = render_transfer_schedule(people)
    actor = next(block for block in result.blocks if block.person_id == "1")
    assert "Your new companion, Chris Lee, will be waiting." in actor.raw_text
    assert "Both companions fell back to 00:00." not in actor.raw_text
    assert "ERROR:" not in actor.raw_text
    assert not any(err.code == "HANDOFF_REVIEW" for err in result.errors)


def test_render_transfer_schedule_staying_dropoff_orders_subway_without_time_last() -> None:
    people = [
        _person(
            pid="1",
            first="Alex",
            last="Kim",
            current_companion="Aaron Able & Ben Park",
            new_companion="Chris Lee",
            staying=True,
            dep_terminal="-",
        ),
        _person(
            pid="2",
            first="Aaron",
            last="Able",
            current_companion="Alex Kim",
            dep_terminal="Daejeon Station",
            dep_time="08:00",
        ),
        _person(
            pid="3",
            first="Ben",
            last="Park",
            current_companion="Alex Kim",
            dep_terminal="Busan Subway",
            dep_time=None,
        ),
        _person(
            pid="4",
            first="Chris",
            last="Lee",
            current_companion="Dana Shin",
            arr_terminal="Busan",
            arr_time="09:15",
        ),
        _person(pid="5", first="Dana", last="Shin", current_companion="Chris Lee"),
    ]
    result = render_transfer_schedule(people)
    actor = next(block for block in result.blocks if block.person_id == "1")
    assert actor.raw_text.index("Drop off Aaron Able at Daejeon Station.") < actor.raw_text.index(
        "Drop off Ben Park at Busan."
    )
    assert "Wait at Busan until your new companion, Chris Lee, arrives there at 09:15." in actor.raw_text


def test_render_transfer_schedule_multiple_new_companions_use_earliest_final_arrival() -> None:
    people = [
        _person(
            pid="1",
            first="Alex",
            last="Kim",
            current_companion="Ben Park",
            new_companion="Chris Lee & Dana Shin",
            staying=True,
            dep_terminal="-",
        ),
        _person(
            pid="2",
            first="Ben",
            last="Park",
            current_companion="Alex Kim",
            dep_terminal="Seoul Station",
            dep_time="08:30",
        ),
        _person(
            pid="3",
            first="Chris",
            last="Lee",
            current_companion="Evan Hall",
            second_leg=True,
            arr_terminal="Daegu",
            arr_time="08:45",
            arr2_terminal="Seoul Station",
            arr2_time="09:40",
        ),
        _person(
            pid="4",
            first="Dana",
            last="Shin",
            current_companion="Frank Young",
            arr_terminal="Seoul Station",
            arr_time="09:10",
        ),
        _person(pid="5", first="Evan", last="Hall", current_companion="Chris Lee"),
        _person(pid="6", first="Frank", last="Young", current_companion="Dana Shin"),
    ]
    result = render_transfer_schedule(people)
    actor = next(block for block in result.blocks if block.person_id == "1")
    assert "Wait at Seoul Station until your new companion, Chris Lee & Dana Shin, arrives there at 09:10." in actor.raw_text


def test_render_transfer_schedule_overlap_uses_only_changing_new_companion_name() -> None:
    people = [
        _person(
            pid="1",
            first="Alex",
            last="Kim",
            current_companion="Ben Park",
            new_companion="Ben Park & Chris Lee",
            dep_terminal="Seoul Station",
            dep_time="08:00",
            arr_terminal="Busan Station",
            arr_time="09:00",
        ),
        _person(
            pid="2",
            first="Ben",
            last="Park",
            current_companion="Alex Kim",
            staying=True,
            dep_terminal="-",
        ),
        _person(
            pid="3",
            first="Chris",
            last="Lee",
            current_companion="Dana Shin",
            arr_terminal="Busan Station",
            arr_time="09:30",
        ),
        _person(pid="4", first="Dana", last="Shin", current_companion="Chris Lee"),
    ]
    result = render_transfer_schedule(people)
    actor = next(block for block in result.blocks if block.person_id == "1")
    assert "Notes: Upon arrival, wait for your companion Chris Lee who will arrive at 09:30." in actor.raw_text
    assert "Ben Park & Chris Lee" not in actor.raw_text


def test_render_transfer_schedule_leaving_person_renders_pre_dropoff_lines() -> None:
    people = [
        _person(
            pid="1",
            first="Alex",
            last="Kim",
            current_companion="Ben Park & Chris Lee",
            new_companion="Dana Shin",
            dep_terminal="Busan Station",
            dep_time="09:00",
            arr_terminal="Daegu Station",
            arr_time="10:00",
        ),
        _person(
            pid="2",
            first="Ben",
            last="Park",
            current_companion="Alex Kim",
            dep_terminal="Seoul Station",
            dep_time="07:45",
        ),
        _person(
            pid="3",
            first="Chris",
            last="Lee",
            current_companion="Alex Kim",
            dep_terminal="Incheon Station",
            dep_time="08:30",
        ),
        _person(
            pid="4",
            first="Dana",
            last="Shin",
            current_companion="Evan Hall",
            arr_terminal="Daegu Station",
            arr_time="10:30",
        ),
        _person(pid="5", first="Evan", last="Hall", current_companion="Dana Shin"),
    ]
    result = render_transfer_schedule(people)
    actor = next(block for block in result.blocks if block.person_id == "1")
    assert "Drop off Ben Park at Seoul Station." in actor.raw_text
    assert "Drop off Chris Lee at Incheon Station." in actor.raw_text
    assert actor.raw_text.index("Drop off Ben Park at Seoul Station.") < actor.raw_text.index(
        "Travel to Busan Station with Ben Park & Chris Lee."
    )


def test_render_transfer_schedule_same_terminal_earliest_arrival_tie_stays_deterministic() -> None:
    people = [
        _person(
            pid="1",
            first="Alex",
            last="Kim",
            current_companion="Ben Park",
            new_companion="Chris Lee & Dana Shin",
            staying=True,
            dep_terminal="-",
        ),
        _person(
            pid="2",
            first="Ben",
            last="Park",
            current_companion="Alex Kim",
            dep_terminal="Seoul Station",
            dep_time="08:00",
        ),
        _person(
            pid="3",
            first="Chris",
            last="Lee",
            current_companion="Evan Hall",
            arr_terminal="Seoul Station",
            arr_time="09:00",
        ),
        _person(
            pid="4",
            first="Dana",
            last="Shin",
            current_companion="Frank Young",
            arr_terminal="Seoul Station",
            arr_time="09:00",
        ),
        _person(pid="5", first="Evan", last="Hall", current_companion="Chris Lee"),
        _person(pid="6", first="Frank", last="Young", current_companion="Dana Shin"),
    ]
    result = render_transfer_schedule(people)
    actor = next(block for block in result.blocks if block.person_id == "1")
    assert "ERROR:" not in actor.raw_text
    assert "Wait at Seoul Station until your new companion, Chris Lee & Dana Shin, arrives there at 09:00." in actor.raw_text
    assert not any(err.code == "HANDOFF_REVIEW" for err in result.errors)


def test_render_transfer_schedule_pickup_alias_variants_keep_waiting_text() -> None:
    cases = [
        ("익산시외버스터미널", "익산 시외"),
        ("세종고속시외버스터미널", "세종 고속 시외 터미널"),
        ("유성 시외", "대전 유성 터미널"),
        ("성남 버스 터미널", "성남 종합 버스 버미널"),
    ]
    for index, (dropoff_terminal, reunion_terminal) in enumerate(cases, start=1):
        people = [
            _person(
                pid="1",
                first="Alex",
                last="Kim",
                current_companion="Ben Park",
                new_companion="Chris Lee",
                staying=True,
                dep_terminal="-",
            ),
            _person(
                pid="2",
                first="Ben",
                last="Park",
                current_companion="Alex Kim",
                dep_terminal=dropoff_terminal,
                dep_time="08:00",
            ),
            _person(
                pid="3",
                first="Chris",
                last="Lee",
                current_companion="Dana Shin",
                arr_terminal=reunion_terminal,
                arr_time="09:30",
            ),
            _person(pid="4", first="Dana", last="Shin", current_companion="Chris Lee"),
        ]
        result = render_transfer_schedule(people)
        actor = next(block for block in result.blocks if block.person_id == "1")
        assert "Wait at" in actor.raw_text, f"case {index} should keep waiting text"
        assert not any(
            err.code == "HANDOFF_REVIEW" and "companion pickup error" in err.message.lower()
            for err in result.errors
        ), f"case {index} should not raise companion pickup error"


def test_render_transfer_schedule_staying_pickup_mismatch_with_subway_final_leg_uses_coordination_sentence() -> None:
    people = [
        _person(
            pid="1",
            first="Yewon",
            last="Jeong",
            current_companion="Zyra Pacaldo",
            new_companion="Kacie Jacobs",
            staying=True,
            dep_terminal="-",
            dep_time=None,
            arr_terminal=None,
            arr_time=None,
        ),
        _person(
            pid="2",
            first="Zyra",
            last="Pacaldo",
            current_companion="Yewon Jeong",
            dep_terminal="성남 종합 터미널",
            dep_time="09:50",
        ),
        _person(
            pid="3",
            first="Kacie",
            last="Jacobs",
            current_companion="Michelle Pak",
            second_leg=True,
            dep_terminal="subway 평택역",
            dep_time="blue line",
            arr_terminal="수원역",
            arr_time=None,
            dep2_terminal="subway 수원역",
            dep2_time="yellow line",
            arr2_terminal="죽전역",
            arr2_time=None,
        ),
        _person(pid="4", first="Michelle", last="Pak", current_companion="Kacie Jacobs"),
    ]
    result = render_transfer_schedule(people)
    actor = next(block for block in result.blocks if block.person_id == "1")
    assert "Drop off Zyra Pacaldo at 성남 종합 터미널." in actor.raw_text
    assert "[New companion is arriving at 죽전역]" in actor.raw_text
    assert "Please communicate with your new companion to determine a meetup time in advance." in actor.raw_text
    assert "will be waiting" not in actor.raw_text
    assert "Wait at" not in actor.raw_text
    assert "ERROR:" not in actor.raw_text
    assert any(
        err.code == "HANDOFF_REVIEW"
        and "companion pickup error" in err.message.lower()
        for err in result.errors
    )


def test_render_transfer_schedule_staying_pickup_mismatch_with_usable_time_omits_handoff_sentence() -> None:
    people = [
        _person(
            pid="1",
            first="Alex",
            last="Kim",
            current_companion="Ben Park",
            new_companion="Chris Lee",
            staying=True,
            dep_terminal="-",
        ),
        _person(
            pid="2",
            first="Ben",
            last="Park",
            current_companion="Alex Kim",
            dep_terminal="Seoul Station",
            dep_time="08:00",
        ),
        _person(
            pid="3",
            first="Chris",
            last="Lee",
            current_companion="Dana Shin",
            arr_terminal="Busan Station",
            arr_time="09:30",
        ),
        _person(pid="4", first="Dana", last="Shin", current_companion="Chris Lee"),
    ]
    result = render_transfer_schedule(people)
    actor = next(block for block in result.blocks if block.person_id == "1")
    assert "Drop off Ben Park at Seoul Station." in actor.raw_text
    assert "Wait at" not in actor.raw_text
    assert "will be waiting" not in actor.raw_text
    assert "Please communicate with your new companion" not in actor.raw_text
    assert "[New companion is arriving at Busan Station]" in actor.raw_text
    assert any(
        err.code == "HANDOFF_REVIEW"
        and "companion pickup error" in err.message.lower()
        for err in result.errors
    )


def test_render_transfer_schedule_traveler_notes_use_coordination_sentence_for_subway_final_arrival_without_time() -> None:
    people = [
        _person(
            pid="1",
            first="Alex",
            last="Kim",
            current_companion="Ben Park",
            new_companion="Chris Lee",
            dep_terminal="Seoul Station",
            dep_time="08:00",
            arr_terminal="Busan Station",
            arr_time="09:00",
        ),
        _person(
            pid="2",
            first="Ben",
            last="Park",
            current_companion="Alex Kim",
            dep_terminal="Seoul Station",
            dep_time="08:00",
        ),
        _person(
            pid="3",
            first="Chris",
            last="Lee",
            current_companion="Dana Shin",
            second_leg=True,
            dep_terminal="Daejeon Station",
            dep_time="08:30",
            arr_terminal="Daegu Station",
            arr_time="09:00",
            dep2_terminal="subway Daegu Station",
            dep2_time="green line",
            arr2_terminal="Busan Station",
            arr2_time=None,
        ),
        _person(pid="4", first="Dana", last="Shin", current_companion="Chris Lee"),
    ]
    result = render_transfer_schedule(people)
    actor = next(block for block in result.blocks if block.person_id == "1")
    assert "Notes: Please communicate with your new companion to determine a meetup time in advance." in actor.raw_text
    assert "will be waiting for you" not in actor.raw_text
    assert "wait for your companion" not in actor.raw_text.lower()


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


def test_render_transfer_schedule_missing_companion_message_includes_person_and_source_context() -> None:
    people = [
        _person(
            pid="1",
            first="Justin",
            last="Sherwood",
            current_companion="Xaviah Patch",
            new_companion="Nobody",
            dep_terminal="Subway",
        )
    ]
    people[0].source_file_name = "March 2026 Transfer Plan2.xlsm"
    people[0].source_row_number = 64

    result = render_transfer_schedule(people)

    assert any(
        error.message
        == "Justin Sherwood (row 64, March 2026 Transfer Plan2.xlsm) references missing current companion 'Xaviah Patch'."
        for error in result.errors
    )


def test_split_companion_names_supports_ampersand_and_comma() -> None:
    raw = "Alpha One, Beta Two & Gamma Three"
    assert split_companion_names(raw) == ["Alpha One", "Beta Two", "Gamma Three"]


def test_render_transfer_schedule_trainee_rows_are_rendered_without_placeholder_review_noise() -> None:
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
    assert not any(err.code == "HANDOFF_REVIEW" for err in result.errors)
