"""Typed models for dashboard services."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class ValidationError:
    code: str
    message: str
    field: str | None = None
    row_number: int | None = None
    suggested_action: str | None = None


@dataclass
class PersonRecord:
    id: str
    first_name: str
    last_name: str
    current_companion: str | None = None
    new_companion: str | None = None
    current_zone: str | None = None
    current_area: str | None = None
    new_zone: str | None = None
    new_area: str | None = None
    staying: bool | None = None
    pre_travel: str | None = None
    departure_terminal: str | None = None
    departure_time: str | None = None
    arrival_terminal: str | None = None
    arrival_time: str | None = None
    second_leg: bool | None = None
    second_departure_terminal: str | None = None
    second_departure_time: str | None = None
    second_arrival_terminal: str | None = None
    second_arrival_time: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    source_file_name: str | None = None
    source_row_number: int | None = None
    dataset_version: int | None = None


@dataclass
class OperationResult:
    success: bool
    records_processed: int = 0
    records_inserted: int = 0
    records_updated: int = 0
    records_skipped: int = 0
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class DatasetState:
    record_count: int
    schema_version: int
    last_imported_at: str | None
    source_file_name: str | None
    recovery_notice: str | None = None


@dataclass
class ParsedDataset:
    records: list[dict[str, Any]]
    records_processed: int
    records_skipped: int
    errors: list[ValidationError]
    warnings: list[str]


ImportResult = OperationResult
AppendResult = OperationResult
ReplaceResult = OperationResult


@dataclass
class ScheduleError:
    code: str
    message: str
    person_id: str | None = None
    field: str | None = None
    suggested_action: str | None = None


@dataclass
class ConflictAnchor:
    block_id: str
    line_start: int
    line_end: int
    char_start: int | None = None
    char_end: int | None = None
    highlight_token: str | None = None


@dataclass
class ScheduleBlock:
    block_id: str
    person_id: str | None
    person_display_name: str | None
    current_zone: str | None
    starting_companionship_key: str | None
    render_order: int
    raw_text: str
    block_kind: Literal["person", "zone_header", "area_header"] = "person"
    created_at: str | None = None
    updated_at: str | None = None
    source_person_updated_at: str | None = None


@dataclass
class ScheduleConflict:
    conflict_id: str
    conflict_type: str
    severity: str
    message: str
    affected_people: list[str] = field(default_factory=list)
    affected_locations: list[str] = field(default_factory=list)
    anchors: list[ConflictAnchor] = field(default_factory=list)
    created_at: str | None = None


@dataclass
class ScheduleMetadata:
    schedule_version: int
    generated_at: str
    generated_by_operation: str
    source_dataset_version: int
    source_dataset_last_imported_at: str | None
    source_max_person_updated_at: str | None
    pseudo_code_version_ref: str
    block_count: int
    conflict_count: int


@dataclass
class ScheduleBuildResult:
    success: bool
    schedule_version: int | None = None
    generated_at: str | None = None
    blocks_generated: int = 0
    conflicts_found: int = 0
    errors: list[ScheduleError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
