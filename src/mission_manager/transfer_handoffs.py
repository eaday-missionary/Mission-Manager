"""Shared handoff-resolution helpers for transfer rendering and conflict checks."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Literal

from .models import PersonRecord, ScheduleError

SUBWAY_TOKEN = re.compile(r"subway", re.IGNORECASE)


@dataclass
class HandoffResolution:
    display_time: str
    minutes: int
    terminal: str = "-"
    fallback_used: bool = False
    ambiguous: bool = False
    coordination_required: bool = False
    contributor_ids: list[str] = field(default_factory=list)
    contributor_names: list[str] = field(default_factory=list)
    issues: list[ScheduleError] = field(default_factory=list)


@dataclass
class HandoffComparison:
    status: Literal["wait", "other_waits", "review"]
    reference: HandoffResolution


@dataclass
class DropoffStop:
    person_id: str
    person_name: str
    terminal: str
    display_time: str
    minutes: int
    fallback_used: bool = False
    listed_index: int = 0


@dataclass
class DropoffPlan:
    stops: list[DropoffStop]
    final_reference: HandoffResolution
    issues: list[ScheduleError] = field(default_factory=list)
    forced_last_terminal: str | None = None


@dataclass
class TerminalSplitReview:
    issue: ScheduleError
    affected_people: list[str]
    affected_locations: list[str]


@dataclass
class PickupMismatchReview:
    issue: ScheduleError
    affected_people: list[str]
    affected_locations: list[str]


MEETUP_COORDINATION_MESSAGE = "Please communicate with your new companion to determine a meetup time in advance."


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


def companion_name_set(raw: str | None) -> set[str]:
    return {
        normalized
        for normalized in (normalize_name(name) for name in split_companion_names(raw))
        if normalized
    }


def changing_companion_names(
    target_raw: str | None,
    existing_raw: str | None,
) -> list[str]:
    existing = companion_name_set(existing_raw)
    names: list[str] = []
    for raw_name in split_companion_names(target_raw):
        normalized = normalize_name(raw_name)
        if not normalized or normalized in existing:
            continue
        names.append(raw_name)
    return names


def has_companion_overlap(current_raw: str | None, new_raw: str | None) -> bool:
    return bool(companion_name_set(current_raw) & companion_name_set(new_raw))


def parse_time_minutes(value: str | None) -> int | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    parts = text.split(":")
    if len(parts) not in {2, 3}:
        return None
    try:
        hh = int(parts[0])
        mm = int(parts[1])
        ss = int(parts[2]) if len(parts) == 3 else 0
    except Exception:
        return None
    if hh < 0 or hh > 23 or mm < 0 or mm > 59 or ss < 0 or ss > 59:
        return None
    return (hh * 60) + mm


def time_to_minutes(value: str | None) -> int:
    parsed = parse_time_minutes(value)
    if parsed is None:
        return 0
    return parsed


def normalized_time_display(value: str | None) -> str:
    minutes = parse_time_minutes(value)
    if minutes is None:
        return "00:00"
    hh = minutes // 60
    mm = minutes % 60
    return f"{hh:02d}:{mm:02d}"


def contains_subway(value: str | None) -> bool:
    return bool(value and SUBWAY_TOKEN.search(value))


def cleanup_subway_terminal(value: str | None) -> str:
    if is_blank(value):
        return "-"
    cleaned = SUBWAY_TOKEN.sub("", value or "")
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    cleaned = re.sub(r"\s*([,/])\s*", r"\1 ", cleaned)
    cleaned = cleaned.strip(" -/,")
    cleaned = " ".join(cleaned.split())
    return cleaned if cleaned else "-"


def canonical_terminal_key(value: str | None) -> str:
    cleaned = cleanup_subway_terminal(value)
    if cleaned == "-":
        return "-"
    collapsed = re.sub(r"[\s,./()_-]+", "", cleaned)
    return collapsed.casefold() or "-"


def is_blank(value: str | None) -> bool:
    if value is None:
        return True
    text = value.strip()
    return text == "" or text == "-"


_PICKUP_TERMINAL_ALIAS_FAMILIES = (
    frozenset(
        {
            canonical_terminal_key("익산시외버스터미널"),
            canonical_terminal_key("익산 시외"),
        }
    ),
    frozenset(
        {
            canonical_terminal_key("세종고속시외버스터미널"),
            canonical_terminal_key("세종 고속 시외 터미널"),
        }
    ),
    frozenset(
        {
            canonical_terminal_key("유성 시외"),
            canonical_terminal_key("대전 유성 터미널"),
        }
    ),
    frozenset(
        {
            canonical_terminal_key("성남 버스 터미널"),
            canonical_terminal_key("성남 종합 터미널"),
            canonical_terminal_key("성남 종합 버스 버미널"),
        }
    ),
)


def pickup_terminals_match(left: str | None, right: str | None) -> bool:
    left_key = canonical_terminal_key(left)
    right_key = canonical_terminal_key(right)
    if left_key == "-" or right_key == "-":
        return left_key == right_key
    if left_key == right_key:
        return True
    return any(left_key in family and right_key in family for family in _PICKUP_TERMINAL_ALIAS_FAMILIES)


def final_arrival_time(person: PersonRecord) -> str | None:
    if person.second_leg and person.second_arrival_time:
        return person.second_arrival_time
    return person.arrival_time


def final_arrival_terminal(person: PersonRecord) -> str:
    if person.second_leg and not is_blank(person.second_arrival_terminal):
        return cleanup_subway_terminal(person.second_arrival_terminal)
    return cleanup_subway_terminal(person.arrival_terminal)


def _error_context(actor: PersonRecord) -> str:
    context_bits: list[str] = []
    if actor.source_row_number is not None:
        context_bits.append(f"row {actor.source_row_number}")
    if actor.source_file_name:
        context_bits.append(actor.source_file_name)
    return f" ({', '.join(context_bits)})" if context_bits else ""


def _review_error(
    actor: PersonRecord,
    field: str,
    message: str,
) -> ScheduleError:
    actor_name = display_name(actor) or "Unknown person"
    return ScheduleError(
        code="HANDOFF_REVIEW",
        message=f"{actor_name}{_error_context(actor)} {message}",
        person_id=actor.id,
        field=field,
        suggested_action="Review transfer handoff data for ambiguous or missing timing/location details.",
    )


def _missing_error(
    actor: PersonRecord,
    field: str,
    raw_name: str,
) -> ScheduleError:
    actor_name = display_name(actor) or "Unknown person"
    field_label = field.replace("_", " ")
    return ScheduleError(
        code="DATA_CONFLICT",
        message=f"{actor_name}{_error_context(actor)} references missing {field_label} '{raw_name}'.",
        person_id=actor.id,
        field=field,
        suggested_action="Verify companion spelling and ensure that person exists in dashboard data.",
    )


def _manual_flag_error(
    actor: PersonRecord,
    field: str,
    flag: str,
) -> ScheduleError:
    actor_name = display_name(actor) or "Unknown person"
    return ScheduleError(
        code="HANDOFF_REVIEW",
        message=f"{actor_name}{_error_context(actor)} {flag}.",
        person_id=actor.id,
        field=field,
        suggested_action="Review this transfer handoff in the transfer editor before relying on it.",
    )


def _placeholder_person(
    actor: PersonRecord,
    field: str,
    raw_name: str,
) -> PersonRecord:
    return PersonRecord(
        id=f"placeholder:{field}:{actor.id}:{normalize_name(raw_name) or 'trainee'}",
        first_name=raw_name.strip() or "Trainee",
        last_name="",
        current_companion=None,
        new_companion=None,
        current_zone=actor.current_zone,
        current_area=actor.current_area,
        new_zone=actor.new_zone,
        new_area=actor.new_area,
        staying=None,
        pre_travel=None,
        departure_terminal=None,
        departure_time=None,
        arrival_terminal=None,
        arrival_time=None,
        second_leg=None,
        second_departure_terminal=None,
        second_departure_time=None,
        second_arrival_terminal=None,
        second_arrival_time=None,
        source_file_name=actor.source_file_name,
        source_row_number=actor.source_row_number,
    )


def resolve_people_by_names(
    names: list[str],
    people_by_name: dict[str, PersonRecord],
    actor: PersonRecord,
    field: str,
) -> tuple[list[PersonRecord], list[ScheduleError]]:
    found: list[PersonRecord] = []
    issues: list[ScheduleError] = []
    for raw_name in names:
        lookup = normalize_name(raw_name)
        if not lookup:
            continue
        if is_trainee_name(lookup):
            found.append(_placeholder_person(actor, field, raw_name))
            continue
        person = people_by_name.get(lookup)
        if not person:
            issues.append(_missing_error(actor, field, raw_name))
            continue
        found.append(person)
    return found, issues


def _clone_with_issues(
    resolution: HandoffResolution,
    issues: list[ScheduleError],
    *,
    ambiguous: bool | None = None,
) -> HandoffResolution:
    return HandoffResolution(
        display_time=resolution.display_time,
        minutes=resolution.minutes,
        terminal=resolution.terminal,
        fallback_used=resolution.fallback_used,
        ambiguous=resolution.ambiguous if ambiguous is None else ambiguous,
        coordination_required=resolution.coordination_required,
        contributor_ids=list(resolution.contributor_ids),
        contributor_names=list(resolution.contributor_names),
        issues=issues,
    )


def _fallback_reference(
    people: list[PersonRecord],
) -> HandoffResolution:
    return HandoffResolution(
        display_time="00:00",
        minutes=0,
        terminal="-",
        fallback_used=True,
        ambiguous=False,
        coordination_required=False,
        contributor_ids=[person.id for person in people],
        contributor_names=[display_name(person) for person in people],
    )


def _dropoff_stop_from_person(
    person: PersonRecord,
    *,
    listed_index: int,
) -> DropoffStop:
    return DropoffStop(
        person_id=person.id,
        person_name=display_name(person),
        terminal=cleanup_subway_terminal(person.departure_terminal),
        display_time=normalized_time_display(person.departure_time),
        minutes=time_to_minutes(person.departure_time),
        fallback_used=parse_time_minutes(person.departure_time) is None,
        listed_index=listed_index,
    )


def _stop_sort_key(stop: DropoffStop) -> tuple[int, int, int]:
    return (1 if stop.fallback_used else 0, stop.minutes, stop.listed_index)


def _reference_from_stop(
    stop: DropoffStop | None,
    *,
    all_people: list[PersonRecord],
) -> HandoffResolution:
    if stop is None:
        return _fallback_reference(all_people)
    return HandoffResolution(
        display_time=stop.display_time,
        minutes=stop.minutes,
        terminal=stop.terminal,
        fallback_used=stop.fallback_used,
        ambiguous=False,
        coordination_required=False,
        contributor_ids=[person.id for person in all_people],
        contributor_names=[display_name(person) for person in all_people],
    )


def _resolve_current_companion_people(
    actor: PersonRecord,
    people_by_name: dict[str, PersonRecord],
) -> tuple[list[PersonRecord], list[ScheduleError]]:
    return resolve_people_by_names(
        split_companion_names(actor.current_companion),
        people_by_name,
        actor,
        "current_companion",
    )


def resolve_current_companion_dropoff_plan(
    actor: PersonRecord,
    people_by_name: dict[str, PersonRecord],
    *,
    include_actor: bool,
    preferred_last_terminal: str | None = None,
    collect_issues: bool,
) -> DropoffPlan:
    current_people, issues = _resolve_current_companion_people(actor, people_by_name)
    participants = list(current_people)
    if include_actor and all(person.id != actor.id for person in participants):
        participants.append(actor)

    departing_people: list[tuple[int, PersonRecord]] = []
    for index, person in enumerate(participants):
        if person.staying is True:
            continue
        if is_blank(person.departure_terminal) and is_blank(person.departure_time):
            continue
        departing_people.append((index, person))

    stops = [
        _dropoff_stop_from_person(person, listed_index=index)
        for index, person in departing_people
    ]
    ordered = sorted(stops, key=_stop_sort_key)

    forced_last = cleanup_subway_terminal(preferred_last_terminal)
    if forced_last != "-":
        matching = [stop for stop in ordered if canonical_terminal_key(stop.terminal) == canonical_terminal_key(forced_last)]
        non_matching = [stop for stop in ordered if canonical_terminal_key(stop.terminal) != canonical_terminal_key(forced_last)]
        if matching:
            ordered = non_matching + matching
        else:
            forced_last = None
    else:
        forced_last = None

    all_people = [person for _, person in departing_people]
    final_reference = _reference_from_stop(ordered[-1] if ordered else None, all_people=all_people)
    return DropoffPlan(
        stops=ordered,
        final_reference=_clone_with_issues(final_reference, list(issues)),
        issues=list(issues) if collect_issues else [],
        forced_last_terminal=forced_last,
    )


def resolve_current_companion_departure(
    actor: PersonRecord,
    people_by_name: dict[str, PersonRecord],
    *,
    include_actor: bool,
    collect_issues: bool,
) -> HandoffResolution:
    plan = resolve_current_companion_dropoff_plan(
        actor,
        people_by_name,
        include_actor=include_actor,
        preferred_last_terminal=None,
        collect_issues=collect_issues,
    )
    return _clone_with_issues(plan.final_reference, plan.issues)


def terminal_split_review(
    actor: PersonRecord,
    people_by_name: dict[str, PersonRecord],
) -> TerminalSplitReview | None:
    if actor.staying is True:
        return None
    actor_dep = parse_time_minutes(actor.departure_time)
    if actor_dep is None:
        return None

    current_people, issues = _resolve_current_companion_people(actor, people_by_name)
    if issues or not current_people:
        return None

    participants = [actor, *current_people]
    departures: list[tuple[PersonRecord, int, str]] = []
    for person in participants:
        if person.staying is True:
            return None
        departure_minutes = parse_time_minutes(person.departure_time)
        terminal = cleanup_subway_terminal(person.departure_terminal)
        if departure_minutes is None or terminal == "-":
            return None
        departures.append((person, departure_minutes, terminal))

    latest_departure = max(minutes for _, minutes, _ in departures)
    if actor_dep != latest_departure:
        return None

    terminal_keys = {canonical_terminal_key(terminal) for _, _, terminal in departures}
    if len(terminal_keys) <= 1:
        return None

    affected_people: list[str] = []
    affected_locations: list[str] = []
    seen_people: set[str] = set()
    seen_locations: set[str] = set()
    for person, _, terminal in departures:
        if person.id not in seen_people:
            affected_people.append(person.id)
            seen_people.add(person.id)
        terminal_key = canonical_terminal_key(terminal)
        if terminal_key not in seen_locations:
            affected_locations.append(terminal)
            seen_locations.add(terminal_key)

    issue = _manual_flag_error(
        actor,
        "current_companion",
        "manual inspection required because companions are leaving from different terminals",
    )
    return TerminalSplitReview(
        issue=issue,
        affected_people=affected_people,
        affected_locations=affected_locations,
    )


def final_leg_is_subway_without_arrival_time(person: PersonRecord) -> bool:
    if person.second_leg:
        return contains_subway(person.second_departure_terminal) and parse_time_minutes(person.second_arrival_time) is None
    return contains_subway(person.departure_terminal) and parse_time_minutes(person.arrival_time) is None


def _availability_for_person(
    person: PersonRecord,
    people_by_name: dict[str, PersonRecord],
    *,
    reunion_terminal: str | None = None,
) -> HandoffResolution:
    if person.staying is True:
        plan = resolve_current_companion_dropoff_plan(
            person,
            people_by_name,
            include_actor=True,
            preferred_last_terminal=reunion_terminal,
            collect_issues=False,
        )
        return plan.final_reference
    terminal = final_arrival_terminal(person)
    minutes = time_to_minutes(final_arrival_time(person))
    fallback_used = parse_time_minutes(final_arrival_time(person)) is None
    return HandoffResolution(
        display_time=normalized_time_display(final_arrival_time(person)),
        minutes=minutes,
        terminal=terminal,
        fallback_used=fallback_used,
        ambiguous=False,
        coordination_required=final_leg_is_subway_without_arrival_time(person),
        contributor_ids=[person.id],
        contributor_names=[display_name(person)],
    )


def resolve_new_companion_availability(
    actor: PersonRecord,
    people_by_name: dict[str, PersonRecord],
) -> HandoffResolution:
    names = changing_companion_names(actor.new_companion, actor.current_companion)
    if not names:
        names = split_companion_names(actor.new_companion)
    if not names:
        return HandoffResolution(
            display_time="00:00",
            minutes=0,
            terminal="-",
            fallback_used=True,
            ambiguous=False,
            coordination_required=False,
        )
    targets, issues = resolve_people_by_names(
        names,
        people_by_name,
        actor,
        "new_companion",
    )
    if not targets:
        resolution = HandoffResolution(
            display_time="00:00",
            minutes=0,
            terminal="-",
            fallback_used=True,
            ambiguous=False,
            coordination_required=False,
            issues=issues,
        )
        if issues:
            return resolution
        return _clone_with_issues(
            resolution,
            [
                _review_error(
                    actor,
                    "new_companion",
                    "does not have a resolvable new-companion handoff anchor; manual review required.",
                )
            ],
            ambiguous=True,
        )

    actor_reunion_terminal = final_arrival_terminal(actor) if actor.staying is not True else None
    availabilities = [
        _availability_for_person(
            person,
            people_by_name,
            reunion_terminal=actor_reunion_terminal,
        )
        for person in targets
    ]
    indexed = list(enumerate(availabilities))
    chosen_index, chosen = min(
        indexed,
        key=lambda pair: (
            1 if pair[1].fallback_used else 0,
            pair[1].minutes,
            pair[0],
        ),
    )

    extra_issues = list(issues)
    ambiguous = False
    earliest_tied = [
        item
        for item in availabilities
        if item.fallback_used == chosen.fallback_used and item.minutes == chosen.minutes
    ]
    overlap_present = has_companion_overlap(actor.current_companion, actor.new_companion)
    non_blank_terminals = {item.terminal for item in availabilities if item.terminal != "-"}

    if (
        not chosen.fallback_used
        and len({canonical_terminal_key(item.terminal) for item in earliest_tied if item.terminal != "-"}) > 1
    ):
        ambiguous = True
        extra_issues.append(
            _manual_flag_error(
                actor,
                "new_companion",
                "multiple new companions, manual confirmation required",
            )
        )
    elif overlap_present and len({canonical_terminal_key(item) for item in non_blank_terminals}) > 1:
        extra_issues.append(
            _manual_flag_error(
                actor,
                "new_companion",
                "multiple new companions, manual confirmation required",
            )
        )
    return HandoffResolution(
        display_time=chosen.display_time,
        minutes=chosen.minutes,
        terminal=chosen.terminal,
        fallback_used=chosen.fallback_used,
        ambiguous=ambiguous,
        coordination_required=chosen.coordination_required,
        contributor_ids=[targets[chosen_index].id],
        contributor_names=[display_name(targets[chosen_index])],
        issues=extra_issues,
    )


def arrival_reference(
    person: PersonRecord,
    *,
    second_leg: bool,
) -> HandoffResolution:
    time_value = person.second_arrival_time if second_leg else person.arrival_time
    terminal_value = person.second_arrival_terminal if second_leg else person.arrival_terminal
    return HandoffResolution(
        display_time=normalized_time_display(time_value),
        minutes=time_to_minutes(time_value),
        terminal=cleanup_subway_terminal(terminal_value),
        fallback_used=parse_time_minutes(time_value) is None,
        ambiguous=False,
        coordination_required=False,
        contributor_ids=[person.id],
        contributor_names=[display_name(person)],
    )


def pickup_mismatch_review(
    actor: PersonRecord,
    dropoff_plan: DropoffPlan,
    new_companion: HandoffResolution,
) -> PickupMismatchReview | None:
    if actor.staying is not True:
        return None
    if not dropoff_plan.stops:
        return None
    dropoff_terminal = dropoff_plan.final_reference.terminal
    reunion_terminal = new_companion.terminal
    if dropoff_terminal == "-" or reunion_terminal == "-":
        return None
    if pickup_terminals_match(dropoff_terminal, reunion_terminal):
        return None

    issue = _manual_flag_error(
        actor,
        "new_companion",
        "companion pickup error",
    )
    affected_people: list[str] = []
    seen_people: set[str] = set()
    for person_id in [actor.id, *dropoff_plan.final_reference.contributor_ids, *new_companion.contributor_ids]:
        if person_id and person_id not in seen_people:
            affected_people.append(person_id)
            seen_people.add(person_id)
    affected_locations = [dropoff_terminal, reunion_terminal]
    return PickupMismatchReview(
        issue=issue,
        affected_people=affected_people,
        affected_locations=affected_locations,
    )


def compare_handoff(
    new_companion: HandoffResolution,
    candidates: list[HandoffResolution],
) -> HandoffComparison:
    if not candidates:
        return HandoffComparison(status="other_waits", reference=new_companion)
    if new_companion.ambiguous or any(candidate.ambiguous for candidate in candidates):
        chosen = max(
            candidates,
            key=lambda item: (item.minutes, not item.fallback_used, item.display_time),
        )
        return HandoffComparison(status="review", reference=chosen)

    chosen = max(
        candidates,
        key=lambda item: (not item.ambiguous, item.minutes, not item.fallback_used, item.display_time),
    )
    if new_companion.ambiguous or chosen.ambiguous:
        return HandoffComparison(status="review", reference=chosen)
    if new_companion.minutes == chosen.minutes:
        return HandoffComparison(status="other_waits", reference=chosen)
    if new_companion.minutes > chosen.minutes:
        return HandoffComparison(status="wait", reference=chosen)
    return HandoffComparison(status="other_waits", reference=chosen)
