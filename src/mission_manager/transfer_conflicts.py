"""Conflict scanning for transfer schedules."""

from __future__ import annotations

from uuid import uuid4

from .models import ConflictAnchor, PersonRecord, ScheduleBlock, ScheduleConflict, ScheduleError
from .transfer_engine import build_people_lookup, display_name, normalize_name, split_companion_names


def _time_to_minutes(value: str | None) -> int:
    if not value:
        return 0
    try:
        hh, mm = value.split(":", 1)
        return int(hh) * 60 + int(mm)
    except Exception:
        return 0


def _anchor_for(block: ScheduleBlock, token: str | None) -> ConflictAnchor:
    lines = block.raw_text.splitlines()
    if token:
        for idx, line in enumerate(lines, start=1):
            if token in line:
                return ConflictAnchor(
                    block_id=block.block_id,
                    line_start=idx,
                    line_end=idx,
                    highlight_token=token,
                )
    return ConflictAnchor(block_id=block.block_id, line_start=1, line_end=1, highlight_token=token)


def _build_data_conflict(
    err: ScheduleError,
    block: ScheduleBlock | None,
) -> ScheduleConflict:
    anchors = [_anchor_for(block, None)] if block else []
    return ScheduleConflict(
        conflict_id=str(uuid4()),
        conflict_type="DATA_CONFLICT",
        severity="yellow",
        message=err.message,
        affected_people=[err.person_id] if err.person_id else [],
        affected_locations=[err.field] if err.field else [],
        anchors=anchors,
    )


def detect_transfer_conflicts(
    people: list[PersonRecord],
    blocks: list[ScheduleBlock],
    render_errors: list[ScheduleError],
) -> list[ScheduleConflict]:
    conflicts: list[ScheduleConflict] = []
    person_by_name = build_people_lookup(people)
    person_blocks = [block for block in blocks if block.block_kind == "person" and block.person_id]
    block_by_person_id = {block.person_id: block for block in person_blocks if block.person_id}

    for err in render_errors:
        block = block_by_person_id.get(err.person_id or "")
        conflicts.append(_build_data_conflict(err, block))

    for person in people:
        block = block_by_person_id.get(person.id)
        if not block:
            continue

        person_name = display_name(person)

        current_comp = None
        for name in split_companion_names(person.current_companion):
            current_comp = person_by_name.get(normalize_name(name))
            if current_comp:
                break

        if current_comp and person.departure_time and current_comp.departure_time:
            if _time_to_minutes(person.departure_time) < _time_to_minutes(current_comp.departure_time):
                conflicts.append(
                    ScheduleConflict(
                        conflict_id=str(uuid4()),
                        conflict_type="TIME_CONFLICT",
                        severity="red",
                        message=f"{person_name} has a time conflict in their schedule.",
                        affected_people=[person.id, current_comp.id],
                        affected_locations=[
                            person.departure_terminal or "-",
                            current_comp.departure_terminal or "-",
                        ],
                        anchors=[
                            _anchor_for(block, person.departure_time),
                            _anchor_for(block_by_person_id.get(current_comp.id, block), current_comp.departure_time),
                        ],
                    )
                )

        if person.second_leg and person.arrival_time and person.second_departure_time:
            if _time_to_minutes(person.arrival_time) > _time_to_minutes(person.second_departure_time):
                conflicts.append(
                    ScheduleConflict(
                        conflict_id=str(uuid4()),
                        conflict_type="TIME_CONFLICT",
                        severity="red",
                        message=f"{person_name} has a time conflict in their schedule.",
                        affected_people=[person.id],
                        affected_locations=[
                            person.arrival_terminal or "-",
                            person.second_departure_terminal or "-",
                        ],
                        anchors=[
                            _anchor_for(block, person.arrival_time),
                            _anchor_for(block, person.second_departure_time),
                        ],
                    )
                )

        if person.second_leg and person.arrival_terminal and person.second_departure_terminal:
            if normalize_name(person.arrival_terminal) != normalize_name(person.second_departure_terminal):
                conflicts.append(
                    ScheduleConflict(
                        conflict_id=str(uuid4()),
                        conflict_type="LOCATION_CONFLICT",
                        severity="yellow",
                        message=f"{person_name} has a location conflict in their schedule.",
                        affected_people=[person.id],
                        affected_locations=[person.arrival_terminal, person.second_departure_terminal],
                        anchors=[
                            _anchor_for(block, person.arrival_terminal),
                            _anchor_for(block, person.second_departure_terminal),
                        ],
                    )
                )

    return conflicts
