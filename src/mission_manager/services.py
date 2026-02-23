"""Dashboard business services."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from .constants import DEFAULT_SORT_DIR, DEFAULT_SORT_FIELD, PERSON_FIELDS
from .importers import normalize_boolean, normalize_text, normalize_time, parse_excel_file
from .models import (
    AppendResult,
    DatasetState,
    ImportResult,
    ReplaceResult,
    ScheduleBlock,
    ScheduleBuildResult,
    ScheduleConflict,
    ScheduleError,
    ScheduleFixResult,
    ValidationError,
)
from .storage import StorageRepository
from .transfer_conflicts import detect_transfer_conflicts
from .transfer_engine import render_transfer_schedule, resolve_dependency_ids


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

    def get_schedule_document(self) -> list[ScheduleBlock]:
        return self.repo.load_transfer_schedule()

    def list_schedule_conflicts(self) -> list[ScheduleConflict]:
        return self.repo.load_transfer_conflicts()

    def create_schedule(self, confirm_overwrite: bool) -> ScheduleBuildResult:
        if not confirm_overwrite:
            return ScheduleBuildResult(
                success=False,
                errors=[
                    ScheduleError(
                        code="CONFIRMATION_REQUIRED",
                        message="Schedule overwrite confirmation is required.",
                    )
                ],
            )

        people = self.repo.list_people()
        if not people:
            return ScheduleBuildResult(
                success=False,
                errors=[
                    ScheduleError(
                        code="SOURCE_DATA_MISSING",
                        message="No dashboard records found. Import data before creating a schedule.",
                    )
                ],
            )

        render = render_transfer_schedule(people)
        conflicts = detect_transfer_conflicts(people, render.blocks, render.errors)
        state = self.repo.dataset_state()
        source_max_updated = max(
            (p.updated_at for p in people if p.updated_at), default=None
        )
        meta = self.repo.replace_transfer_schedule(
            blocks=render.blocks,
            conflicts=conflicts,
            generated_by_operation="create",
            source_dataset_version=state.schema_version,
            source_dataset_last_imported_at=state.last_imported_at,
            source_max_person_updated_at=source_max_updated,
            pseudo_code_version_ref=str(
                Path("docs/transfer editor/transfer editor-pseudo-code.md")
            ),
        )
        return ScheduleBuildResult(
            success=True,
            schedule_version=meta.schedule_version,
            generated_at=meta.generated_at,
            blocks_generated=len(render.blocks),
            conflicts_found=len(conflicts),
            errors=render.errors,
            warnings=render.warnings,
        )

    def fix_schedule(self) -> ScheduleFixResult:
        latest = self.repo.load_latest_transfer_meta()
        if latest is None:
            created = self.create_schedule(confirm_overwrite=True)
            return ScheduleFixResult(
                success=created.success,
                schedule_version=created.schedule_version,
                generated_at=created.generated_at,
                blocks_rebuilt=created.blocks_generated,
                people_rebuilt=created.blocks_generated,
                conflicts_found=created.conflicts_found,
                errors=created.errors,
                warnings=created.warnings,
            )

        changed_people = self.repo.get_people_updated_since(
            latest.source_max_person_updated_at
        )
        if not changed_people:
            return ScheduleFixResult(
                success=True,
                schedule_version=latest.schedule_version,
                generated_at=latest.generated_at,
                blocks_rebuilt=0,
                people_rebuilt=0,
                conflicts_found=latest.conflict_count,
            )

        all_people = self.repo.list_people()
        affected_ids = resolve_dependency_ids(
            all_people, {person.id for person in changed_people}
        )
        render = render_transfer_schedule(all_people)
        conflicts = detect_transfer_conflicts(all_people, render.blocks, render.errors)
        state = self.repo.dataset_state()
        source_max_updated = max(
            (p.updated_at for p in all_people if p.updated_at), default=None
        )
        meta = self.repo.replace_transfer_schedule(
            blocks=render.blocks,
            conflicts=conflicts,
            generated_by_operation="fix",
            source_dataset_version=state.schema_version,
            source_dataset_last_imported_at=state.last_imported_at,
            source_max_person_updated_at=source_max_updated,
            pseudo_code_version_ref=str(
                Path("docs/transfer editor/transfer editor-pseudo-code.md")
            ),
        )
        return ScheduleFixResult(
            success=True,
            schedule_version=meta.schedule_version,
            generated_at=meta.generated_at,
            blocks_rebuilt=len(affected_ids),
            people_rebuilt=len(affected_ids),
            conflicts_found=len(conflicts),
            errors=render.errors,
            warnings=render.warnings,
        )
