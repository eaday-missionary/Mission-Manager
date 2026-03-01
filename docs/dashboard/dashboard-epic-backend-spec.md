# Dashboard Epic Backend Spec

## Purpose and Scope
This document defines backend requirements for the dashboard feature, including Excel import, schema validation, normalization, local persistence, query support, and safe data operations.

In scope:
- Import/parsing/validation for `.xlsx` and `.xlsm` files.
- Canonical person-record normalization.
- Local persistence using SQLite.
- Backend services for import, append, replace, edit, list, and startup load.
- Error handling, observability, and transactional integrity.

Out of scope:
- Authentication and role management.
- Cloud sync and cross-device replication.
- Multi-user concurrent edits across machines.

## Runtime and Dependencies
- Backend implementation language: Python.
- Required libraries:
  - `openpyxl` for Excel ingestion (`.xlsx` and `.xlsm`).
  - `xlrd` for legacy `.xls` ingestion.
  - `sqlite3` (Python standard library) for local persistence.

## Canonical Person Schema (Backend Model)
Backend canonical record type:

- `first_name: str`
- `last_name: str`
- `current_companion: str | null`
- `new_companion: str | null`
- `current_zone: str | null`
- `current_area: str | null`
- `new_zone: str | null`
- `new_area: str | null`
- `staying: bool | null`
- `pre_travel: str | null`
- `departure_terminal: str | null`
- `departure_time: str | null` (`HH:mm`)
- `arrival_terminal: str | null`
- `arrival_time: str | null` (`HH:mm`)
- `second_leg: bool | null`
- `second_departure_terminal: str | null`
- `second_departure_time: str | null` (`HH:mm`)
- `second_arrival_terminal: str | null`
- `second_arrival_time: str | null` (`HH:mm`)

Meta fields:
- `id: str` (UUID)
- `created_at: str` (ISO-8601 UTC)
- `updated_at: str` (ISO-8601 UTC)
- `source_file_name: str`
- `source_row_number: int`
- `dataset_version: int`

## Accepted Excel Headers Contract
The importer uses canonical internal headers and accepts known aliases from sample mission spreadsheets.
Validation is order-independent and name-based.

Canonical header set:

- `First Name`
- `Last Name`
- `Current Companion`
- `New Companion`
- `Current Zone`
- `Current Area`
- `New Zone`
- `New Area`
- `Staying or leaving?`
- `Pre Travel`
- `Departure Terminal`
- `Departure Time`
- `Arrival Terminal`
- `Arrival Time`
- `Second Leg?`
- `2nd Departure Terminal`
- `2nd Departure Time`
- `2nd Arrival Terminal`
- `2nd Arrival Time`

Accepted aliases:
- `Transfer to Zone` -> `New Zone`
- `Transfer to Area` -> `New Area`
- `Staying?` -> `Staying or leaving?`
- `Departing Terminal` -> `Departure Terminal`
- `Arriving Terminal` -> `Arrival Terminal`
- `Departing Terminal 2` -> `2nd Departure Terminal`
- `Departure Time 2` -> `2nd Departure Time`
- `Arrival Time 2` -> `2nd Arrival Time`
- `Arriving Terminal 2` -> `2nd Arrival Terminal`

Schema behavior:
- Missing required canonical fields (after alias mapping) must fail import with explicit `missing_headers` output.
- Unknown non-required columns are allowed and ignored, and listed in warnings as `unexpected_headers`.

## Backend Service Interfaces
Required service contracts:

- `import_excel(file_path) -> ImportResult`
- `append_excel(file_path) -> AppendResult`
- `replace_excel(file_path) -> ReplaceResult`
- `list_people(filters, sort, search) -> list[PersonRecord]`
- `get_person(person_id) -> PersonRecord`
- `create_person(patch) -> PersonRecord`
- `update_person(person_id, patch) -> PersonRecord`
- `load_local_dataset() -> DatasetState`
- `clear_dataset() -> None`

Standard result fields (`ImportResult`, `AppendResult`, `ReplaceResult`):
- `success: bool`
- `records_processed: int`
- `records_inserted: int`
- `records_updated: int`
- `records_skipped: int`
- `errors: list[ValidationError]`
- `warnings: list[str]`

`ValidationError` shape:
- `code: str`
- `message: str`
- `field: str | null`
- `row_number: int | null`
- `suggested_action: str | null`

## Local Persistence Contract
SQLite is required for MVP persistence.

Database location:
- Must be stored in app-local machine storage (platform-specific app data directory).

Required tables:
- `people`
- `dataset_meta`
- `import_history`

Required indexes:
- `current_zone`
- `current_area`
- `new_zone`
- `new_area`
- `first_name`
- `last_name`
- `departure_time`
- `arrival_time`
- `second_leg`
- `second_departure_time`
- `second_arrival_time`

## Import Pipeline Specification
### 1) File Validation
- Verify file extension is `.xlsx` or `.xlsm`.
- Verify file is readable and not locked/corrupt.
- Verify workbook and at least one worksheet exist.
- Default ingestion sheet is the first worksheet.

### 2) Schema Validation
- Header row is expected at row `1`.
- Header names must match strict required set.
- Column order may vary.
- Fail fast on critical schema mismatch with actionable error detail.

### 3) Row Parsing
- Skip fully empty rows.
- Preserve original row numbers for diagnostics.
- Trim surrounding whitespace on text values.

### 4) Type Normalization
Boolean fields:
- Applies to `staying` and `second_leg`.
- True-like values: `yes`, `y`, `true`, `1`.
- False-like values: `no`, `n`, `false`, `0`.
- Blank values normalize to `null`.
- Unknown literal normalizes to `null` and emits a warning.

### 5) Time Normalization
- Accept Excel serial time values and text values.
- Normalize valid times to strict `HH:mm`.
- Invalid time values produce field-level `ROW_VALIDATION_ERROR`.

### 6) Record Validation Rules
- Identity-required fields: `First Name`, `Last Name`.
- Other fields are optional and persist as `null` when missing.
- Backend persists null values; frontend renders `-`.

## Append, Replace, and Edit Semantics
### Append
- Duplicate key rule: `First Name + Last Name + Current Area`.
- Matching key updates existing record.
- Non-matching key inserts new record.

### Replace
- Must parse and validate candidate dataset before destructive commit.
- Replace operation must execute in a transaction.
- On failure, previous dataset remains intact.
- On success, people dataset is replaced transactionally without clearing prior transfer schedule projections.
- Application flow must attempt immediate schedule regeneration after successful replace.
- If post-replace regeneration fails, prior transfer projections remain visible until a later successful regeneration.

### Clear Dataset
- Clear operation must delete people data and transfer schedule projection tables.
- Clear operation must execute transactionally so UI cannot observe partially cleared state.

### Edit
- Patch-based update by `person_id`.
- Re-validate changed fields.
- Re-apply boolean/time normalization for updated fields.
- UI `Apply` action triggers this `update_person(person_id, patch)` path and persists immediately.
- Successful edit/create/import/append/replace flows should trigger schedule regeneration through application orchestration.
- UI post-apply navigation (returning to previously active tab) does not change backend edit contracts.

### Manual Create
- Create path must accept person payload without prior Excel import.
- Uses same normalization and validation rules as edit path (`first_name` and `last_name` required; time/boolean normalization identical).
- Inserts one new row in `people` with generated UUID and timestamps.
- Updates `dataset_meta.record_count`.
- Does not overwrite import metadata fields (`last_imported_at`, `source_file_name`) during manual create.

## Query Support for Frontend Requirements
Required query behavior:
- Default sort: `current_zone ASC` (alphabetical).
- Must support filter/sort fields:
  - `current_area`
  - `new_zone`
  - `new_area`
  - `first_name` (A-Z)
  - `last_name` (A-Z)
  - `departure_time` (earliest-latest)
  - `arrival_time` (earliest-latest)
  - `second_leg` (yes/no)
  - `second_departure_time` (earliest-latest)
  - `second_arrival_time` (earliest-latest)
- Must support live global search across all 19 data fields with case-insensitive contains matching.
- Must support boolean text matching so user queries like `yes`/`no` match stored boolean fields (`staying`, `second_leg`).
- Combined search/filter/sort results must be deterministic and stable.

## Data Persistence and Startup Behavior
- On startup, backend must load latest valid persisted dataset automatically.
- If database is missing, backend initializes clean storage state.
- If database is corrupt, backend initializes clean state and surfaces recovery signal to UI.
- Successful import/append/replace/edit must auto-save persistently.

Required dataset metadata fields:
- `schema_version`
- `last_imported_at`
- `record_count`
- `source_file_name`

## Error Model and Observability
Error categories:
- `FILE_ERROR`
- `SCHEMA_ERROR`
- `ROW_VALIDATION_ERROR`
- `PERSISTENCE_ERROR`
- `CONFLICT_ERROR`
- `UNKNOWN_ERROR`

Each surfaced error must include:
- `code`
- `message`
- `field` (optional)
- `row_number` (optional)
- `suggested_action` (optional)

Structured logging requirements:
- Import start/end events.
- Record counters (`processed`, `inserted`, `updated`, `skipped`).
- Replace rollback events.
- Corruption detection and recovery events.

## Security and Data Integrity
- Data remains local to machine storage.
- Use parameterized SQL exclusively.
- Use transactions for append, replace, and update operations.
- Ensure atomic commits.
- Destructive operations require explicit service-level confirmation input.

## Performance Requirements
- Must support 100-150 records with near-instant list query interactions.
- Import target for typical files: `<= 2s`.
- Search/filter/sort query target: `<= 300ms` on typical mission hardware.

## Compatibility Note with Provided Sample Workbook
Sample file reference:
- `Test_excel_files/testing for mission manager.xlsm`

Observed header variants include names such as:
- `Transfer to Zone`
- `Staying?`
- `Departing Terminal`

Those variants are now accepted through alias mapping and normalized to canonical fields internally.

## Acceptance Criteria (Backend)
- Canonical-header `.xlsx` and `.xlsm` imports succeed.
- Invalid schema returns actionable missing/unexpected header lists.
- Excel serial times normalize to `HH:mm`.
- Boolean variants normalize to `bool | null`.
- Append performs update/insert by composite dedupe key.
- Replace is transactional and rollback-safe.
- Startup loads persisted SQLite data automatically.
- Supported filters/sorts/searches return deterministic results.

## Test Cases and Scenarios
1. Schema pass case:
- Canonical 19 headers present -> import succeeds.

2. Schema fail case:
- Missing required header -> `SCHEMA_ERROR` with header name.

3. Sample workbook compatibility:
- Sample `.xlsm` header variants -> explicit mismatch report.

4. Time parsing:
- Excel numeric serial time -> normalized `HH:mm`.
- Text `HH:mm` -> accepted.
- Invalid time text -> row validation error.

5. Boolean normalization:
- `yes/y/true/1` -> `true`
- `no/n/false/0` -> `false`
- blank -> `null`

6. Append dedupe:
- Matching composite key updates existing row.
- Non-matching key inserts new row.

7. Replace safety:
- Replacement parse/validation failure preserves prior dataset.

8. Persistence:
- Restart reloads prior dataset.
- Corrupt DB triggers clean-state init + recovery signal.

9. Query behavior:
- Default `current_zone ASC` sort.
- Field-specific search across all 19 fields.
- Time sorts are chronological.

10. Edit behavior:
- Valid edit persists.
- Invalid time/boolean edit returns field-level validation error.

11. Manual create behavior:
- Valid create persists one new row and increments record count metadata.
- Missing required names or invalid time values return field-level validation errors.

## Assumptions and Defaults
- Backend remains Python-based.
- `.xlsx` and `.xlsm` are in scope; `.xls` is out of scope for MVP.
- SQLite is the local persistence engine.
- Header policy uses canonical names plus known sample header aliases.
- `Staying or leaving?` and `Second Leg?` normalize to `bool | null`.
- Missing field values persist as `null`; frontend renders `-`.
