"""Dashboard business services."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .constants import DEFAULT_SORT_DIR, DEFAULT_SORT_FIELD, PERSON_FIELDS
from .importers import normalize_boolean, normalize_text, normalize_time, parse_excel_file
from .models import AppendResult, DatasetState, ImportResult, ReplaceResult, ValidationError
from .storage import StorageRepository


class DashboardService:
    def __init__(self, repo: StorageRepository | None = None) -> None:
        self.repo = repo or StorageRepository()

    def load_local_dataset(self) -> DatasetState:
        return self.repo.dataset_state()

    def import_excel(self, file_path: str) -> ImportResult:
        parsed = parse_excel_file(file_path)
        if parsed.errors:
            return ImportResult(success=False, records_processed=parsed.records_processed, records_skipped=parsed.records_skipped, errors=parsed.errors, warnings=parsed.warnings)
        inserted, _ = self.repo.replace_people(parsed.records, source_file_name=file_path, processed=parsed.records_processed, skipped=parsed.records_skipped)
        return ImportResult(success=True, records_processed=parsed.records_processed, records_inserted=inserted, records_skipped=parsed.records_skipped, warnings=parsed.warnings)

    def append_excel(self, file_path: str) -> AppendResult:
        parsed = parse_excel_file(file_path)
        if parsed.errors:
            return AppendResult(success=False, records_processed=parsed.records_processed, records_skipped=parsed.records_skipped, errors=parsed.errors, warnings=parsed.warnings)
        inserted, updated = self.repo.append_people(parsed.records, source_file_name=file_path, processed=parsed.records_processed, skipped=parsed.records_skipped)
        return AppendResult(success=True, records_processed=parsed.records_processed, records_inserted=inserted, records_updated=updated, records_skipped=parsed.records_skipped, warnings=parsed.warnings)

    def replace_excel(self, file_path: str) -> ReplaceResult:
        return ReplaceResult(**asdict(self.import_excel(file_path)))

    def list_people(self, filters: dict[str, Any] | None = None, sort: tuple[str, str] | None = None, search: tuple[str | None, str | None] | None = None):
        sort_field, sort_dir = sort or (DEFAULT_SORT_FIELD, DEFAULT_SORT_DIR)
        search_field, search_query = search or (None, None)
        return self.repo.list_people(filters=filters, sort_field=sort_field, sort_dir=sort_dir, search_field=search_field, search_query=search_query)

    def get_person(self, person_id: str):
        return self.repo.get_person(person_id)

    def update_person(self, person_id: str, patch: dict[str, Any]):
        normalized: dict[str, Any] = {}
        errors: list[ValidationError] = []
        for field, value in patch.items():
            if field not in PERSON_FIELDS:
                continue
            if field in ("staying", "second_leg"):
                normalized[field], _ = normalize_boolean(value)
            elif field in ("departure_time", "arrival_time", "second_departure_time", "second_arrival_time"):
                tval = normalize_time(value)
                if normalize_text(value) is not None and tval is None:
                    errors.append(ValidationError(code="ROW_VALIDATION_ERROR", message=f"Invalid time value '{value}'", field=field))
                normalized[field] = tval
            else:
                normalized[field] = normalize_text(value)

        if not normalized.get("first_name") and "first_name" in normalized:
            errors.append(ValidationError(code="ROW_VALIDATION_ERROR", message="First Name is required", field="first_name"))
        if not normalized.get("last_name") and "last_name" in normalized:
            errors.append(ValidationError(code="ROW_VALIDATION_ERROR", message="Last Name is required", field="last_name"))
        if errors:
            return None, errors

        person = self.repo.update_person(person_id, normalized)
        return person, []

    def clear_dataset(self, confirm: bool) -> None:
        if confirm:
            self.repo.clear_dataset()
