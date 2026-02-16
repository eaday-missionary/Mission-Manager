"""Typed models for dashboard services."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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
