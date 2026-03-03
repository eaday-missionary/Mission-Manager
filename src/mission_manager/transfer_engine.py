"""Transfer schedule rendering engine based on transfer-editor pseudo-code."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable, Literal
from uuid import uuid4

from .models import PersonRecord, ScheduleBlock, ScheduleError

SUBWAY = "Subway"
SUJI_TRAINING = "\uc218\uc9c0 Training"
SEPARATOR = "---------------"
FIGHTING = "\ud654\uc774\ud305!!!"
SUBWAY_TOKEN = re.compile(r"subway", re.IGNORECASE)
HANGUL_TOKEN = re.compile(r"[가-힣]+")


@dataclass
class RenderResult:
    blocks: list[ScheduleBlock]
    errors: list[ScheduleError]
    warnings: list[str]


@dataclass
class _CompanionshipGroup:
    zone: str
    area: str
    key: str
    members: list[PersonRecord]


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


def _canonical_companion_text(raw: str | None) -> str:
    names = split_companion_names(raw)
    return " & ".join(names) if names else "-"


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


def _parse_time_minutes(value: str | None) -> int | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    parts = text.split(":", 1)
    if len(parts) != 2:
        return None
    try:
        hh = int(parts[0])
        mm = int(parts[1])
    except Exception:
        return None
    if hh < 0 or hh > 23 or mm < 0 or mm > 59:
        return None
    return (hh * 60) + mm


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


def _zone_label(person: PersonRecord) -> str:
    return (person.current_zone or "-").strip() or "-"


def _area_label(person: PersonRecord) -> str:
    return (person.current_area or "-").strip() or "-"


def _area_family_key(area: str) -> str:
    match = HANGUL_TOKEN.search(area)
    if match:
        return match.group(0)
    return normalize_name(area) or "-"


def _area_title_suffix(members: list[PersonRecord]) -> str:
    if not members:
        return ""
    normalized_titles: list[str] = []
    for member in members:
        title = (member.title or "").strip().upper()
        if title not in {"S", "E"}:
            return ""
        normalized_titles.append(title)
    first = normalized_titles[0]
    if all(value == first for value in normalized_titles):
        return f" {first}"
    return ""


def _contains_subway(value: str | None) -> bool:
    return bool(value and SUBWAY_TOKEN.search(value))


def _line_or_dash(value: str | None) -> str:
    if _is_blank(value):
        return "-"
    return (value or "").strip() or "-"


def _cleanup_subway_terminal(value: str | None) -> str:
    if _is_blank(value):
        return "-"
    cleaned = SUBWAY_TOKEN.sub("", value or "")
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    cleaned = re.sub(r"\s*([,/])\s*", r"\1 ", cleaned)
    cleaned = cleaned.strip(" -/,")
    cleaned = " ".join(cleaned.split())
    return cleaned if cleaned else "-"


def _needs_wait_for_new_companion(
    new_comp_final_time: str | None,
    candidate_times: list[str | None],
) -> bool:
    new_comp_minutes = _parse_time_minutes(new_comp_final_time)
    if new_comp_minutes is None:
        return False
    comparisons: list[bool] = []
    for candidate in candidate_times:
        candidate_minutes = _parse_time_minutes(candidate)
        if candidate_minutes is None:
            continue
        comparisons.append(new_comp_minutes > candidate_minutes)
    if not comparisons:
        return False
    return any(comparisons)


def _top_ticket_warnings(
    person: PersonRecord,
    *,
    departure_terminal: str | None,
    second_departure_terminal: str | None,
) -> list[str]:
    warnings: list[str] = []
    if (
        not _is_blank(departure_terminal)
        and _is_blank(person.departure_time)
        and _is_blank(person.arrival_time)
    ):
        warnings.append(
            f"WARNING - You must purchase the {departure_terminal} ticket in person"
        )
    if (
        person.second_leg is True
        and not _is_blank(second_departure_terminal)
        and _is_blank(person.second_departure_time)
        and _is_blank(person.second_arrival_time)
    ):
        warnings.append(
            f"WARNING - You must purchase the {second_departure_terminal} ticket in person"
        )
    return warnings


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


def _starting_companionship_key(person: PersonRecord) -> str:
    names: list[str] = []
    actor_name = normalize_name(display_name(person))
    if actor_name:
        if is_trainee_name(actor_name):
            names.append(f"trainee:{person.id}")
        else:
            names.append(actor_name)
    for raw in split_companion_names(person.current_companion):
        norm = normalize_name(raw)
        if not norm or is_trainee_name(norm):
            continue
        names.append(norm)
    filtered = sorted(set(names))
    if filtered:
        return "|".join(filtered)
    return f"solo:{person.id}"


def _arrange_group_members(members: list[PersonRecord]) -> list[PersonRecord]:
    members_sorted = sorted(members, key=lambda p: normalize_name(display_name(p)))
    member_by_name: dict[str, PersonRecord] = {}
    for member in members_sorted:
        canonical = normalize_name(display_name(member))
        if not canonical or is_trainee_name(canonical):
            continue
        member_by_name[canonical] = member
        parts = canonical.split()
        if len(parts) == 2:
            member_by_name.setdefault(f"{parts[1]} {parts[0]}", member)

    ordered: list[PersonRecord] = []
    visited: set[str] = set()
    for person in members_sorted:
        if person.id in visited:
            continue
        ordered.append(person)
        visited.add(person.id)
        companion_names = split_companion_names(person.current_companion)
        for name in companion_names:
            lookup = normalize_name(name)
            if not lookup or is_trainee_name(lookup):
                continue
            match = member_by_name.get(lookup)
            if match and match.id not in visited:
                ordered.append(match)
                visited.add(match.id)
    for person in members_sorted:
        if person.id not in visited:
            ordered.append(person)
            visited.add(person.id)
    return ordered


def _ordered_companionship_groups(people: list[PersonRecord]) -> list[_CompanionshipGroup]:
    zone_order: list[str] = []
    zone_groups: dict[str, list[PersonRecord]] = {}
    for person in people:
        zone = _zone_label(person)
        if zone not in zone_groups:
            zone_order.append(zone)
            zone_groups[zone] = []
        zone_groups[zone].append(person)

    groups: list[_CompanionshipGroup] = []
    for zone in zone_order:
        by_key: dict[str, list[PersonRecord]] = {}
        key_order: list[str] = []
        for person in zone_groups[zone]:
            key = _starting_companionship_key(person)
            if key not in by_key:
                key_order.append(key)
                by_key[key] = []
            by_key[key].append(person)

        family_order: list[str] = []
        groups_by_family: dict[str, list[_CompanionshipGroup]] = {}
        for key in key_order:
            members = _arrange_group_members(by_key[key])
            area = _area_label(members[0]) if members else "-"
            group = _CompanionshipGroup(zone=zone, area=area, key=key, members=members)
            family_key = _area_family_key(area)
            if family_key not in groups_by_family:
                family_order.append(family_key)
                groups_by_family[family_key] = []
            groups_by_family[family_key].append(group)
        for family_key in family_order:
            groups.extend(groups_by_family[family_key])
    return groups


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
    current_companion_text = _canonical_companion_text(person.current_companion)
    new_companion_text = _canonical_companion_text(person.new_companion)

    current_people = _resolve_people_by_names(
        current_names, people_by_name, person, errors, "current_companion"
    )
    current_primary = _best_companion(current_people)
    current_departure_time = _companion_departure_time(current_primary)
    current_departure_terminal = _companion_departure_terminal(current_primary)

    new_comp_final = _new_companion_final_arrival(person, people_by_name, errors)
    new_comp_final_display = _time_or_default(new_comp_final)

    raw_departure_terminal = person.departure_terminal
    raw_second_departure_terminal = person.second_departure_terminal
    dep_subway_raw = _contains_subway(raw_departure_terminal)
    second_dep_subway_raw = _contains_subway(raw_second_departure_terminal)
    has_subway_any_raw = dep_subway_raw or second_dep_subway_raw

    departure_terminal = (
        _cleanup_subway_terminal(raw_departure_terminal)
        if has_subway_any_raw
        else raw_departure_terminal
    )
    second_departure_terminal = (
        _cleanup_subway_terminal(raw_second_departure_terminal)
        if has_subway_any_raw
        else raw_second_departure_terminal
    )

    top_warnings = _top_ticket_warnings(
        person,
        departure_terminal=departure_terminal,
        second_departure_terminal=second_departure_terminal,
    )

    add(person_name)
    nl()
    if top_warnings:
        for warning_line in top_warnings:
            add(warning_line)
            nl()

    if (
        _contains_subway(person.new_zone)
        and _contains_subway(raw_departure_terminal)
    ):
        add("Arrive at the mission office before 10:45.")
        nl()
        add(SEPARATOR)
        return "\n".join(lines)

    if has_subway_any_raw:
        add("!!!!! Make sure your bus card is filled up BEFORE transfer day !!!!!")
        nl()

    dep_blank = _is_blank(departure_terminal)
    if dep_blank:
        all_comp_dep_blank = bool(current_people) and all(
            _is_blank(cp.departure_terminal) for cp in current_people
        )
        if all_comp_dep_blank:
            add(FIGHTING)
            nl()
            add(SEPARATOR)
            return "\n".join(lines)

        if not _is_blank(person.pre_travel):
            add(f"please arrive at the {person.pre_travel} apartment by Thursday night")

        if person.staying is True:
            wait = _needs_wait_for_new_companion(
                new_comp_final,
                [current_departure_time],
            )
            if wait:
                add(
                    f"Drop off {current_companion_text} at {current_departure_terminal}. Wait at {current_departure_terminal} until your new companion, {new_companion_text}, arrives there at {new_comp_final_display}."
                )
            else:
                add(
                    f"Drop off {current_companion_text} at {current_departure_terminal}. Your new companion, {new_companion_text}, will be waiting."
                )
            nl()
            add(SEPARATOR)
            return "\n".join(lines)

        add(f"Travel to - with {current_companion_text}.")
        nl()
        add(SEPARATOR)
        return "\n".join(lines)

    if not _is_blank(person.pre_travel):
        add(f"please arrive at the {person.pre_travel} apartment by Thursday night")

    if person.staying is True:
        wait = _needs_wait_for_new_companion(
            new_comp_final,
            [current_departure_time],
        )
        if wait:
            add(
                f"Drop off {current_companion_text} at {current_departure_terminal}. Wait at {current_departure_terminal} until your new companion, {new_companion_text}, arrives there at {new_comp_final_display}."
            )
        else:
            add(
                f"Drop off {current_companion_text} at {current_departure_terminal}. Your new companion, {new_companion_text}, will be waiting."
            )
        nl()
        add(SEPARATOR)
        return "\n".join(lines)

    add(f"Travel to {departure_terminal} with {current_companion_text}.")
    nl()

    if dep_subway_raw:
        cleaned_dep = departure_terminal if not _is_blank(departure_terminal) else "-"
        cleaned_arr = _cleanup_subway_terminal(person.arrival_terminal)
        subway_line = _line_or_dash(person.departure_time)
        add(
            f"Travel to {cleaned_dep} and ride the {subway_line} to {cleaned_arr}. Leave in time to arrive there at {_time_or_default(person.arrival_time)}."
        )
        if not person.second_leg:
            add(f"There, you will meet your new companion, {new_companion_text}.")
        nl()
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
        if normalize_name(person.arrival_terminal) != normalize_name(second_departure_terminal):
            add(
                f"WARNING You need to travel to {second_departure_terminal or '-'} for your second leg of travel."
            )
            nl()
    else:
        wait = _needs_wait_for_new_companion(
            new_comp_final,
            [person.arrival_time, current_departure_time],
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
        if second_dep_subway_raw:
            cleaned_dep_2 = (
                second_departure_terminal
                if not _is_blank(second_departure_terminal)
                else "-"
            )
            cleaned_arr_2 = _cleanup_subway_terminal(person.second_arrival_terminal)
            subway_line_2 = _line_or_dash(person.second_departure_time)
            add(
                f"Travel to {cleaned_dep_2} and ride the {subway_line_2} to {cleaned_arr_2}. Leave in time to arrive there at {_time_or_default(person.second_arrival_time)},  and meet your new companion, {new_companion_text}."
            )
        else:
            add(f"Departure Location: {second_departure_terminal or '-'}")
            add(f"Departure Time: {_time_or_default(person.second_departure_time)}")
            nl()
            add(f"Arrival Time: {_time_or_default(person.second_arrival_time)}")
            add(f"Arrival Location: {person.second_arrival_terminal or '-'}")
            nl()

        wait_second = _needs_wait_for_new_companion(
            new_comp_final,
            [person.second_arrival_time, current_departure_time],
        )
        if wait_second:
            add(f"Notes: Wait for your companion {new_companion_text} who will arrive at {new_comp_final_display}.")
        else:
            add(f"Notes: Your companion {new_companion_text} will be waiting for you.")

    nl()
    add(SEPARATOR)
    return "\n".join(lines)


def _make_header_block(
    *,
    block_kind: Literal["zone_header", "area_header"],
    current_zone: str,
    render_order: int,
    raw_text: str,
) -> ScheduleBlock:
    return ScheduleBlock(
        block_id=str(uuid4()),
        person_id=None,
        person_display_name=None,
        current_zone=current_zone,
        starting_companionship_key=None,
        render_order=render_order,
        raw_text=raw_text,
        block_kind=block_kind,
        source_person_updated_at=None,
    )


def render_transfer_schedule(people: list[PersonRecord]) -> RenderResult:
    errors: list[ScheduleError] = []
    warnings: list[str] = []
    people_by_name = build_people_lookup(people)
    groups = _ordered_companionship_groups(people)
    blocks: list[ScheduleBlock] = []

    order = 1
    current_zone: str | None = None
    for group in groups:
        if group.zone != current_zone:
            blocks.append(
                _make_header_block(
                    block_kind="zone_header",
                    current_zone=group.zone,
                    render_order=order,
                    raw_text=f"---{group.zone}---",
                )
            )
            order += 1
            current_zone = group.zone

        blocks.append(
            _make_header_block(
                block_kind="area_header",
                current_zone=group.zone,
                render_order=order,
                raw_text=f"------------------------- {group.area}{_area_title_suffix(group.members)} -------------------------",
            )
        )
        order += 1

        for person in group.members:
            raw_text = _render_person_block(person, people_by_name, errors)
            blocks.append(
                ScheduleBlock(
                    block_id=str(uuid4()),
                    person_id=person.id,
                    person_display_name=display_name(person),
                    current_zone=group.zone,
                    starting_companionship_key=group.key,
                    render_order=order,
                    raw_text=raw_text,
                    block_kind="person",
                    source_person_updated_at=person.updated_at,
                )
            )
            order += 1

    return RenderResult(blocks=blocks, errors=errors, warnings=warnings)
