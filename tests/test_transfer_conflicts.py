from mission_manager.models import PersonRecord, ScheduleError
from mission_manager.transfer_conflicts import detect_transfer_conflicts
from mission_manager.transfer_engine import render_transfer_schedule


def _person(
    *,
    pid: str,
    first: str,
    last: str,
    current_companion: str | None = None,
    new_companion: str | None = None,
    zone: str = "Zone A",
    staying: bool | None = False,
    dep_terminal: str | None = "Seoul",
    dep_time: str | None = "08:00",
    arr_terminal: str | None = "Busan",
    arr_time: str | None = "09:00",
    second_leg: bool | None = False,
    dep2_terminal: str | None = None,
    dep2_time: str | None = None,
    arr2_terminal: str | None = None,
    arr2_time: str | None = None,
) -> PersonRecord:
    return PersonRecord(
        id=pid,
        first_name=first,
        last_name=last,
        current_companion=current_companion,
        new_companion=new_companion,
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
        second_arrival_terminal=arr2_terminal,
        second_arrival_time=arr2_time,
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


def test_detect_transfer_conflicts_includes_handoff_review_conflicts() -> None:
    people = [_person(pid="1", first="A", last="One", current_companion="B Two")]
    rendered = render_transfer_schedule(people)
    extra_error = ScheduleError(
        code="HANDOFF_REVIEW",
        message="Manual review required.",
        person_id="1",
        field="current_companion",
    )
    conflicts = detect_transfer_conflicts(
        people, rendered.blocks, rendered.errors + [extra_error]
    )
    assert any(conflict.conflict_type == "HANDOFF_REVIEW" for conflict in conflicts)


def test_detect_transfer_conflicts_skips_handoff_review_for_silent_fallback_only_cases() -> None:
    people = [
        _person(
            pid="1",
            first="Alex",
            last="Kim",
            current_companion="Ben Park",
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
            dep_terminal="Seoul",
            dep_time=None,
        ),
    ]
    rendered = render_transfer_schedule(people)
    conflicts = detect_transfer_conflicts(people, rendered.blocks, rendered.errors)
    assert not any(conflict.conflict_type == "HANDOFF_REVIEW" for conflict in conflicts)


def test_detect_transfer_conflicts_skips_current_companion_mismatch_when_same_terminal() -> None:
    people = [
        _person(
            pid="1",
            first="Dallin",
            last="Farr",
            current_companion="Tate Weeks",
            dep_terminal="군산 시외 버스터미널",
            dep_time="08:00:00",
        ),
        _person(
            pid="2",
            first="Tate",
            last="Weeks",
            current_companion="Dallin Farr",
            dep_terminal="군산시외버스터미널",
            dep_time="11:30:00",
        ),
    ]
    rendered = render_transfer_schedule(people)
    conflicts = detect_transfer_conflicts(people, rendered.blocks, rendered.errors)
    assert not any(
        conflict.conflict_type == "TIME_CONFLICT"
        and "Dallin Farr has a time conflict in their schedule." == conflict.message
        for conflict in conflicts
    )


def test_detect_transfer_conflicts_flags_terminal_split_as_handoff_review_only() -> None:
    people = [
        _person(
            pid="1",
            first="Sophie",
            last="Bowen",
            current_companion="Penina Togia'i",
            dep_terminal="오산역환승센터",
            dep_time="09:00",
        ),
        _person(
            pid="2",
            first="Penina",
            last="Togia'i",
            current_companion="Sophie Bowen",
            dep_terminal="평택시외버스터미널",
            dep_time="10:10:00",
        ),
    ]
    rendered = render_transfer_schedule(people)
    conflicts = detect_transfer_conflicts(people, rendered.blocks, rendered.errors)
    assert not any(
        conflict.conflict_type == "TIME_CONFLICT"
        and "Sophie Bowen has a time conflict in their schedule." == conflict.message
        for conflict in conflicts
    )
    assert any(
        conflict.conflict_type == "HANDOFF_REVIEW"
        and "manual inspection required because companions are leaving from different terminals"
        in conflict.message.lower()
        for conflict in conflicts
    )


def test_detect_transfer_conflicts_skips_current_companion_mismatch_with_fallback_time() -> None:
    people = [
        _person(
            pid="1",
            first="Alex",
            last="Kim",
            current_companion="Ben Park",
            dep_terminal="Seoul",
            dep_time=None,
        ),
        _person(
            pid="2",
            first="Ben",
            last="Park",
            current_companion="Alex Kim",
            dep_terminal="Busan",
            dep_time="10:00",
        ),
    ]
    rendered = render_transfer_schedule(people)
    conflicts = detect_transfer_conflicts(people, rendered.blocks, rendered.errors)
    assert not any(
        conflict.conflict_type == "TIME_CONFLICT"
        and "Alex Kim has a time conflict in their schedule." == conflict.message
        for conflict in conflicts
    )


def test_detect_transfer_conflicts_handles_reversed_companion_name_lookup_for_terminal_split_review() -> None:
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
            dep_terminal="Busan",
            dep_time="08:00",
        ),
    ]
    rendered = render_transfer_schedule(people)
    conflicts = detect_transfer_conflicts(people, rendered.blocks, rendered.errors)
    assert any(
        conflict.conflict_type == "HANDOFF_REVIEW"
        and "manual inspection required because companions are leaving from different terminals"
        in conflict.message.lower()
        for conflict in conflicts
    )


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


def test_detect_transfer_conflicts_parses_hh_mm_ss_times_for_terminal_split_review() -> None:
    people = [
        _person(
            pid="1",
            first="John",
            last="Doe",
            current_companion="Jane Roe",
            dep_terminal="Seoul",
            dep_time="07:30:00",
        ),
        _person(
            pid="2",
            first="Jane",
            last="Roe",
            current_companion="John Doe",
            dep_terminal="Busan",
            dep_time="08:00:00",
        ),
    ]
    rendered = render_transfer_schedule(people)
    conflicts = detect_transfer_conflicts(people, rendered.blocks, rendered.errors)
    assert any(
        conflict.conflict_type == "HANDOFF_REVIEW"
        and "manual inspection required because companions are leaving from different terminals"
        in conflict.message.lower()
        for conflict in conflicts
    )


def test_detect_transfer_conflicts_cleans_subway_locations_before_location_compare() -> None:
    people = [
        _person(
            pid="1",
            first="John",
            last="Doe",
            current_companion="Jane Roe",
            arr_terminal="Seoul Subway",
            arr_time="10:00",
            second_leg=True,
            dep2_terminal="Seoul",
            dep2_time="11:00",
        ),
        _person(
            pid="2",
            first="Jane",
            last="Roe",
            current_companion="John Doe",
        ),
    ]
    rendered = render_transfer_schedule(people)
    conflicts = detect_transfer_conflicts(people, rendered.blocks, rendered.errors)
    assert not any(conflict.conflict_type == "LOCATION_CONFLICT" for conflict in conflicts)


def test_detect_transfer_conflicts_flags_traveling_alone_manual_review() -> None:
    people = [
        _person(
            pid="1",
            first="Penina",
            last="Togia'i",
            current_companion="Sophie Bowen",
            dep_terminal="평택시외버스터미널",
            dep_time="10:10",
        ),
        _person(
            pid="2",
            first="Sophie",
            last="Bowen",
            current_companion="Penina Togia'i",
            dep_terminal="오산역환승센터",
            dep_time="09:00",
        ),
    ]
    rendered = render_transfer_schedule(people)
    conflicts = detect_transfer_conflicts(people, rendered.blocks, rendered.errors)
    assert any(
        conflict.conflict_type == "HANDOFF_REVIEW"
        and "manual inspection required because companions are leaving from different terminals"
        in conflict.message.lower()
        for conflict in conflicts
    )


def test_detect_transfer_conflicts_skips_traveling_alone_flag_for_same_normalized_terminal() -> None:
    people = [
        _person(
            pid="1",
            first="Dallin",
            last="Farr",
            current_companion="Tate Weeks",
            dep_terminal="군산 시외 버스터미널",
            dep_time="11:30",
        ),
        _person(
            pid="2",
            first="Tate",
            last="Weeks",
            current_companion="Dallin Farr",
            dep_terminal="군산시외버스터미널",
            dep_time="08:00",
        ),
    ]
    rendered = render_transfer_schedule(people)
    conflicts = detect_transfer_conflicts(people, rendered.blocks, rendered.errors)
    assert not any(
        conflict.conflict_type == "HANDOFF_REVIEW"
        and "manual inspection required because companions are leaving from different terminals"
        in conflict.message.lower()
        for conflict in conflicts
    )


def test_detect_transfer_conflicts_flags_multi_new_companion_manual_review() -> None:
    people = [
        _person(
            pid="1",
            first="Alex",
            last="Kim",
            current_companion="Ben Park",
            new_companion="Chris Lee & Dana Shin",
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
            dep_terminal="Seoul",
            dep_time="08:00",
        ),
        _person(
            pid="3",
            first="Chris",
            last="Lee",
            current_companion="Evan Hall",
            arr_terminal="Busan",
            arr_time="09:00",
        ),
        _person(
            pid="4",
            first="Dana",
            last="Shin",
            current_companion="Frank Young",
            arr_terminal="Daegu",
            arr_time="09:00",
        ),
        _person(pid="5", first="Evan", last="Hall", current_companion="Chris Lee"),
        _person(pid="6", first="Frank", last="Young", current_companion="Dana Shin"),
    ]
    rendered = render_transfer_schedule(people)
    conflicts = detect_transfer_conflicts(people, rendered.blocks, rendered.errors)
    assert any(
        conflict.conflict_type == "HANDOFF_REVIEW"
        and "multiple new companions, manual confirmation required" in conflict.message
        for conflict in conflicts
    )


def test_detect_transfer_conflicts_skips_companion_pickup_error_for_alias_terminals() -> None:
    cases = [
        ("익산시외버스터미널", "익산 시외"),
        ("세종고속시외버스터미널", "세종 고속 시외 터미널"),
        ("유성 시외", "대전 유성 터미널"),
        ("성남 버스 터미널", "성남 종합 버스 버미널"),
    ]
    for dropoff_terminal, reunion_terminal in cases:
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
        rendered = render_transfer_schedule(people)
        conflicts = detect_transfer_conflicts(people, rendered.blocks, rendered.errors)
        assert not any(
            conflict.conflict_type == "HANDOFF_REVIEW"
            and "companion pickup error" in conflict.message.lower()
            for conflict in conflicts
        )


def test_detect_transfer_conflicts_skips_companion_pickup_error_for_coordination_cases() -> None:
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
    rendered = render_transfer_schedule(people)
    conflicts = detect_transfer_conflicts(people, rendered.blocks, rendered.errors)
    assert any(
        conflict.conflict_type == "HANDOFF_REVIEW"
        and "companion pickup error" in conflict.message.lower()
        and "성남 종합 터미널" in conflict.affected_locations
        and "죽전역" in conflict.affected_locations
        for conflict in conflicts
    )


def test_detect_transfer_conflicts_flags_companion_pickup_error_with_both_terminals() -> None:
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
    rendered = render_transfer_schedule(people)
    conflicts = detect_transfer_conflicts(people, rendered.blocks, rendered.errors)
    assert any(
        conflict.conflict_type == "HANDOFF_REVIEW"
        and "companion pickup error" in conflict.message.lower()
        and "Seoul Station" in conflict.affected_locations
        and "Busan Station" in conflict.affected_locations
        for conflict in conflicts
    )
