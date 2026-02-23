"""Transfer schedule rendering engine based on transfer-editor pseudo-code."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable
from uuid import uuid4

from .models import PersonRecord, ScheduleBlock, ScheduleError

SUBWAY = "Subway"
SUJI_TRAINING = "\uc218\uc9c0 Training"
SEPARATOR = "-----------------------------------"
FIGHTING = "\ud654\uc774\ud305!!!"


@dataclass
class RenderResult:
    blocks: list[ScheduleBlock]
    errors: list[ScheduleError]
    warnings: list[str]


def normalize_name(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.strip().split()).lower()


def display_name(person: PersonRecord) -> str:
    return f"{(person.first_name or '').strip()} {(person.last_name or '').strip()}".strip()


def split_companion_names(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [
        " ".join(part.split())
        for part in re.split(r"[&,]", raw)
        if part and part.strip()
    ]


def is_trainee_name(name: str) -> bool:
    return normalize_name(name) == "trainee"


def _time_to_minutes(value: str | None) -> int:
    if not value:
        return 0
    try:
        hh, mm = value.split(":", 1)
        return int(hh) * 60 + int(mm)
    except Exception:
        return 0


def _time_or_default(value: str | None) -> str:
    return value if value else "00:00"


def _final_arrival_time(person: PersonRecord) -> str | None:
    if person.second_leg and person.second_arrival_time:
        return person.second_arrival_time
    return person.arrival_time


def _is_blank(value: str | None) -> bool:
    if value is None:
        return True
    text = value.strip()
    return text == "" or text == "-"


def _build_people_index(people: Iterable[PersonRecord]) -> dict[str, PersonRecord]:
    index: dict[str, PersonRecord] = {}
    for person in people:
        canonical = normalize_name(display_name(person))
        if not canonical or is_trainee_name(canonical):
            continue
        aliases = {canonical}
        parts = canonical.split()
        if len(parts) == 2:
            aliases.add(f"{parts[1]} {parts[0]}")
        for alias in aliases:
            if alias not in index:
                index[alias] = person
    return index


def build_people_lookup(people: Iterable[PersonRecord]) -> dict[str, PersonRecord]:
    """Public wrapper for consistent companion lookups across modules."""
    return _build_people_index(people)


def _resolve_people_by_names(
    names: list[str],
    people_by_name: dict[str, PersonRecord],
    actor: PersonRecord,
    errors: list[ScheduleError],
    field: str,
) -> list[PersonRecord]:
    found: list[PersonRecord] = []
    for raw_name in names:
        lookup = normalize_name(raw_name)
        if not lookup or is_trainee_name(lookup):
            continue
        person = people_by_name.get(lookup)
        if not person:
            errors.append(
                ScheduleError(
                    code="DATA_CONFLICT",
                    message=f"Companion row not found for '{raw_name}'.",
                    person_id=actor.id,
                    field=field,
                    suggested_action="Verify companion spelling and ensure that person exists in dashboard data.",
                )
            )
            continue
        found.append(person)
    return found


def _best_companion(people: list[PersonRecord]) -> PersonRecord | None:
    if not people:
        return None
    return sorted(people, key=lambda p: normalize_name(display_name(p)))[0]


def _companion_departure_time(person: PersonRecord | None) -> str | None:
    if not person:
        return None
    return person.departure_time


def _companion_departure_terminal(person: PersonRecord | None) -> str:
    if not person or _is_blank(person.departure_terminal):
        return "-"
    return person.departure_terminal or "-"


def _new_companion_final_arrival(
    actor: PersonRecord,
    people_by_name: dict[str, PersonRecord],
    errors: list[ScheduleError],
) -> str | None:
    targets = _resolve_people_by_names(
        split_companion_names(actor.new_companion),
        people_by_name,
        actor,
        errors,
        "new_companion",
    )
    if not targets:
        return None
    times = [_final_arrival_time(p) for p in targets]
    times = [t for t in times if t]
    if not times:
        return None
    return sorted(times, key=_time_to_minutes)[-1]


def _nccc_departure_time(
    actor: PersonRecord,
    people_by_name: dict[str, PersonRecord],
    errors: list[ScheduleError],
) -> str | None:
    current_list = _resolve_people_by_names(
        split_companion_names(actor.current_companion),
        people_by_name,
        actor,
        errors,
        "current_companion",
    )
    if not current_list:
        return None

    nccc_targets: dict[str, PersonRecord] = {}
    for current in current_list:
        nccc_list = _resolve_people_by_names(
            split_companion_names(current.new_companion),
            people_by_name,
            actor,
            errors,
            "new_companion",
        )
        for nccc in nccc_list:
            nccc_targets[nccc.id] = nccc

    departure_times = [
        candidate.departure_time
        for candidate in nccc_targets.values()
        if not _is_blank(candidate.departure_time)
    ]
    if not departure_times:
        return None
    return sorted(departure_times, key=_time_to_minutes)[0]


def _starting_companionship_key(person: PersonRecord) -> str:
    names = [normalize_name(display_name(person))]
    names.extend(normalize_name(n) for n in split_companion_names(person.current_companion))
    filtered = sorted({n for n in names if n and not is_trainee_name(n)})
    return "|".join(filtered)


def _order_people(people: list[PersonRecord]) -> list[PersonRecord]:
    active = [p for p in people if not is_trainee_name(normalize_name(display_name(p)))]
    zone_groups: dict[str, list[PersonRecord]] = {}
    for person in active:
        zone = (person.current_zone or "-").strip() or "-"
        zone_groups.setdefault(zone, []).append(person)

    ordered: list[PersonRecord] = []
    for zone in sorted(zone_groups.keys(), key=lambda z: z.casefold()):
        group_order: list[str] = []
        by_comp_key: dict[str, list[PersonRecord]] = {}
        for person in zone_groups[zone]:
            key = _starting_companionship_key(person)
            by_comp_key.setdefault(key, []).append(person)
            if key not in group_order:
                group_order.append(key)

        for key in group_order:
            members = by_comp_key[key]
            members_sorted = sorted(members, key=lambda p: normalize_name(display_name(p)))
            member_by_name: dict[str, PersonRecord] = {}
            for member in members_sorted:
                canonical = normalize_name(display_name(member))
                member_by_name[canonical] = member
                parts = canonical.split()
                if len(parts) == 2:
                    member_by_name.setdefault(f"{parts[1]} {parts[0]}", member)
            visited: set[str] = set()
            for person in members_sorted:
                if person.id in visited:
                    continue
                ordered.append(person)
                visited.add(person.id)
                companion_names = split_companion_names(person.current_companion)
                for name in companion_names:
                    match = member_by_name.get(normalize_name(name))
                    if match and match.id not in visited:
                        ordered.append(match)
                        visited.add(match.id)
            for person in members_sorted:
                if person.id not in visited:
                    ordered.append(person)
                    visited.add(person.id)
    return ordered


def _render_person_block(
    person: PersonRecord,
    people_by_name: dict[str, PersonRecord],
    errors: list[ScheduleError],
) -> str:
    lines: list[str] = []

    def add(value: str) -> None:
        lines.append(value)

    def nl() -> None:
        lines.append("")

    person_name = display_name(person)
    current_names = split_companion_names(person.current_companion)
    new_companion_text = person.new_companion or "-"

    current_people = _resolve_people_by_names(
        current_names, people_by_name, person, errors, "current_companion"
    )
    current_primary = _best_companion(current_people)
    current_departure_time = _companion_departure_time(current_primary)
    current_departure_terminal = _companion_departure_terminal(current_primary)

    new_comp_final = _new_companion_final_arrival(person, people_by_name, errors)
    new_comp_final_display = _time_or_default(new_comp_final)

    add(person_name)
    nl()

    departure_terminal = person.departure_terminal
    second_departure_terminal = person.second_departure_terminal

    if normalize_name(person.new_zone) == normalize_name(SUJI_TRAINING) and normalize_name(departure_terminal) == normalize_name(SUBWAY):
        add("Arrive at the mission office before 10:45.")
        nl()
        add(SEPARATOR)
        return "\n".join(lines)

    if normalize_name(departure_terminal) == normalize_name(SUBWAY) or normalize_name(second_departure_terminal) == normalize_name(SUBWAY):
        add("!!!!! Make sure your bus card is filled up BEFORE transfer day !!!!!")
        nl()

    dep_blank = _is_blank(departure_terminal)
    if dep_blank:
        all_comp_dep_blank = bool(current_people) and all(_is_blank(cp.departure_terminal) for cp in current_people)
        if all_comp_dep_blank:
            add(FIGHTING)
            nl()
            add(SEPARATOR)
            return "\n".join(lines)

        if not _is_blank(person.pre_travel):
            add(f"please arrive at the {person.pre_travel} apartment by Thursday night")

        if person.staying is True:
            wait = _time_to_minutes(new_comp_final_display) > _time_to_minutes(
                _time_or_default(current_departure_time)
            )
            current_companion_label = person.current_companion or "-"
            if wait:
                add(
                    f"Drop off {current_companion_label} at {current_departure_terminal}. Wait at {current_departure_terminal} until your new companion, {new_companion_text}, arrives there at {new_comp_final_display}."
                )
            else:
                add(
                    f"Drop off {current_companion_label} at {current_departure_terminal}. Your new companion, {new_companion_text}, will be waiting."
                )
            nl()
            add(SEPARATOR)
            return "\n".join(lines)

        add(f"Travel to {_time_or_default(departure_terminal)} with {person.current_companion or '-'}.")
        nl()
        add(SEPARATOR)
        return "\n".join(lines)

    if not _is_blank(person.pre_travel):
        add(f"please arrive at the {person.pre_travel} apartment by Thursday night")

    if person.staying is True:
        wait = _time_to_minutes(new_comp_final_display) > _time_to_minutes(
            _time_or_default(current_departure_time)
        )
        current_companion_label = person.current_companion or "-"
        if wait:
            add(
                f"Drop off {current_companion_label} at {current_departure_terminal}. Wait at {current_departure_terminal} until your new companion, {new_companion_text}, arrives there at {new_comp_final_display}."
            )
        else:
            add(
                f"Drop off {current_companion_label} at {current_departure_terminal}. Your new companion, {new_companion_text}, will be waiting."
            )
        nl()
        add(SEPARATOR)
        return "\n".join(lines)

    add(f"Travel to {departure_terminal} with {person.current_companion or '-'}.")
    nl()

    if normalize_name(departure_terminal) == normalize_name(SUBWAY):
        nccc_time = _time_or_default(_nccc_departure_time(person, people_by_name, errors))
        add(
            f"Travel to _____ through ______. Leave in time to arrive there at {nccc_time}, and meet your new companion, {new_companion_text}."
        )
    else:
        add(f"Departure Location: {departure_terminal}")
        add(f"Departure Time: {_time_or_default(person.departure_time)}")
        nl()
        add(f"Arrival Time: {_time_or_default(person.arrival_time)}")
        add(f"Arrival Location: {person.arrival_terminal or '-'}")
        nl()
        if normalize_name(person.new_zone) == normalize_name(SUJI_TRAINING):
            add("Travel to the mission office from there. Arrive before 10:45.")
            nl()

    if person.second_leg:
        if normalize_name(person.arrival_terminal) != normalize_name(person.second_departure_terminal):
            add(f"WARNING You need to travel to {person.second_departure_terminal or '-'} for your second leg of travel.")
    else:
        wait = (
            _time_to_minutes(new_comp_final_display) > _time_to_minutes(_time_or_default(person.arrival_time))
            or _time_to_minutes(new_comp_final_display) > _time_to_minutes(_time_or_default(current_departure_time))
        )
        if wait:
            add(
                f"Notes: Upon arrival, wait for your companion {new_companion_text} who will arrive at {new_comp_final_display}."
            )
        else:
            add(f"Notes: Upon arrival, your companion {new_companion_text} will be waiting for you.")
        nl()

    if person.second_leg:
        add("Second leg of travel:")
        nl()
        if normalize_name(person.second_departure_terminal) == normalize_name(SUBWAY):
            nccc_time_2 = _time_or_default(_nccc_departure_time(person, people_by_name, errors))
            add(
                f"Travel to _____ through ______. Leave in time to arrive there at {nccc_time_2}, and meet your new companion, {new_companion_text}."
            )
        else:
            add(f"Departure Location: {person.second_departure_terminal or '-'}")
            add(f"Departure Time: {_time_or_default(person.second_departure_time)}")
            nl()
            add(f"Arrival Time: {_time_or_default(person.second_arrival_time)}")
            add(f"Arrival Location: {person.second_arrival_terminal or '-'}")
            nl()

        wait_second = (
            _time_to_minutes(new_comp_final_display) > _time_to_minutes(_time_or_default(person.second_arrival_time))
            or _time_to_minutes(new_comp_final_display) > _time_to_minutes(_time_or_default(current_departure_time))
        )
        if wait_second:
            add(f"Notes: Wait for your companion {new_companion_text} who will arrive at {new_comp_final_display}.")
        else:
            add(f"Notes: Your companion {new_companion_text} will be waiting for you.")

    nl()
    add(SEPARATOR)
    return "\n".join(lines)


def render_transfer_schedule(people: list[PersonRecord]) -> RenderResult:
    errors: list[ScheduleError] = []
    warnings: list[str] = []
    people_by_name = build_people_lookup(people)
    ordered_people = _order_people(people)
    blocks: list[ScheduleBlock] = []

    for idx, person in enumerate(ordered_people, start=1):
        raw_text = _render_person_block(person, people_by_name, errors)
        blocks.append(
            ScheduleBlock(
                block_id=str(uuid4()),
                person_id=person.id,
                person_display_name=display_name(person),
                current_zone=person.current_zone,
                starting_companionship_key=_starting_companionship_key(person),
                render_order=idx,
                raw_text=raw_text,
                source_person_updated_at=person.updated_at,
            )
        )

    return RenderResult(blocks=blocks, errors=errors, warnings=warnings)
