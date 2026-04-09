"""Conflict scanning for transfer schedules."""

from __future__ import annotations

from uuid import uuid4

from .models import ConflictAnchor, PersonRecord, ScheduleBlock, ScheduleConflict, ScheduleError
from .transfer_engine import build_people_lookup, display_name, normalize_name
from .transfer_handoffs import (
    cleanup_subway_terminal,
    parse_time_minutes,
    pickup_mismatch_review,
    resolve_current_companion_dropoff_plan,
    resolve_new_companion_availability,
    terminal_split_review,
)


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
    conflict_type = "HANDOFF_REVIEW" if err.code == "HANDOFF_REVIEW" else "DATA_CONFLICT"
    return ScheduleConflict(
        conflict_id=str(uuid4()),
        conflict_type=conflict_type,
        severity="yellow",
        message=err.message,
        affected_people=[err.person_id] if err.person_id else [],
        affected_locations=[err.field] if err.field else [],
        anchors=anchors,
    )


def _is_terminal_split_review_error(err: ScheduleError) -> bool:
    return (
        err.code == "HANDOFF_REVIEW"
        and "manual inspection required because companions are leaving from different terminals"
        in err.message.lower()
    )


def _is_pickup_review_error(err: ScheduleError) -> bool:
    return (
        err.code == "HANDOFF_REVIEW"
        and "companion pickup error" in err.message.lower()
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
        if _is_terminal_split_review_error(err) or _is_pickup_review_error(err):
            continue
        block = block_by_person_id.get(err.person_id or "")
        conflicts.append(_build_data_conflict(err, block))

    for person in people:
        block = block_by_person_id.get(person.id)
        if not block:
            continue

        person_name = display_name(person)

        split_review = terminal_split_review(person, person_by_name)
        if split_review:
            conflicts.append(
                ScheduleConflict(
                    conflict_id=str(uuid4()),
                    conflict_type="HANDOFF_REVIEW",
                    severity="yellow",
                    message=split_review.issue.message,
                    affected_people=split_review.affected_people,
                    affected_locations=split_review.affected_locations,
                    anchors=[
                        _anchor_for(block, person.departure_time),
                    ],
                )
            )

        new_companion = resolve_new_companion_availability(person, person_by_name)
        pickup_review = pickup_mismatch_review(
            person,
            resolve_current_companion_dropoff_plan(
                person,
                person_by_name,
                include_actor=False,
                preferred_last_terminal=new_companion.terminal,
                collect_issues=False,
            ),
            new_companion,
        )
        if pickup_review:
            anchor_token = (
                pickup_review.affected_locations[0]
                if pickup_review.affected_locations
                else None
            )
            conflicts.append(
                ScheduleConflict(
                    conflict_id=str(uuid4()),
                    conflict_type="HANDOFF_REVIEW",
                    severity="yellow",
                    message=pickup_review.issue.message,
                    affected_people=pickup_review.affected_people,
                    affected_locations=pickup_review.affected_locations,
                    anchors=[
                        _anchor_for(block, anchor_token),
                    ],
                )
            )

        if person.second_leg:
            arrival_minutes = parse_time_minutes(person.arrival_time)
            second_dep_minutes = parse_time_minutes(person.second_departure_time)
            if (
                arrival_minutes is not None
                and second_dep_minutes is not None
                and arrival_minutes > second_dep_minutes
            ):
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
            if normalize_name(cleanup_subway_terminal(person.arrival_terminal)) != normalize_name(
                cleanup_subway_terminal(person.second_departure_terminal)
            ):
                conflicts.append(
                    ScheduleConflict(
                        conflict_id=str(uuid4()),
                        conflict_type="LOCATION_CONFLICT",
                        severity="yellow",
                        message=f"{person_name} has a location conflict in their schedule.",
                        affected_people=[person.id],
                        affected_locations=[
                            cleanup_subway_terminal(person.arrival_terminal),
                            cleanup_subway_terminal(person.second_departure_terminal),
                        ],
                        anchors=[
                            _anchor_for(block, person.arrival_terminal),
                            _anchor_for(block, person.second_departure_terminal),
                        ],
                    )
                )

    return conflicts
