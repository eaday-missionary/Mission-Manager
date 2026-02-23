# Transfer Editor Epic Backend Spec

## Purpose and Scope
This document defines backend requirements for generating, storing, updating, and validating transfer schedules from dashboard data.

In scope:
- Build schedule text blocks from dashboard person records using `docs/transfer editor/transfer editor-pseudo-code.md`.
- Provide full schedule generation (`Create Schedule`) and delta schedule repair (`Fix Schedule`).
- Detect and classify schedule conflicts (time, location, data).
- Persist generated schedule blocks, conflict records, and schedule metadata.
- Expose query interfaces required by the transfer editor frontend.

Out of scope:
- Authentication and role permissions.
- Cloud sync and cross-device collaboration.
- Automatic conflict auto-resolution (system detects and reports; user resolves by editing dashboard data).
- Transfer-editor document search UX (`Ctrl+F`, match highlighting, Up/Down navigation), which is frontend-only behavior.

## Runtime and Dependencies
- Backend runtime: Python (same runtime as dashboard epic).
- Data source: dashboard-local SQLite dataset and person schema.
- Required functional dependency:
  - Pseudo-code rules in `docs/transfer editor/transfer editor-pseudo-code.md` are normative for schedule output logic.

## Data Inputs and Contracts
The transfer editor backend must use the canonical person schema defined by the dashboard epic. Transfer editor does not define a new person schema.

Input source contract:
- Transfer editor reads directly from dashboard-local persisted person records.
- Field normalization (booleans, times, blanks) follows dashboard importer/service rules.
- Missing values use dashboard persisted values, but pseudo-code fallback behavior applies during rendering (for example, required but missing time renders as `00:00` where specified).

Required person fields consumed by transfer editor logic:
- `first_name`, `last_name`
- `current_companion`, `new_companion`
- `current_zone`, `current_area`, `new_zone`, `new_area`
- `staying`, `pre_travel`
- `departure_terminal`, `departure_time`
- `arrival_terminal`, `arrival_time`
- `second_leg`, `second_departure_terminal`, `second_departure_time`, `second_arrival_terminal`, `second_arrival_time`
- `updated_at` (for `Fix Schedule` delta detection)

## Transfer Schedule Domain Models

### `ScheduleBuildResult`
- `success: bool`
- `schedule_version: int | None`
- `generated_at: str | None` (ISO-8601 UTC)
- `blocks_generated: int`
- `conflicts_found: int`
- `errors: list[ScheduleError]`
- `warnings: list[str]`

### `ScheduleFixResult`
- `success: bool`
- `schedule_version: int | None`
- `generated_at: str | None` (ISO-8601 UTC)
- `blocks_rebuilt: int`
- `people_rebuilt: int`
- `conflicts_found: int`
- `errors: list[ScheduleError]`
- `warnings: list[str]`

### `ScheduleBlock`
- `block_id: str` (UUID)
- `person_id: str`
- `person_display_name: str` (`FirstName LastName`)
- `current_zone: str | None`
- `starting_companionship_key: str` (normalized unordered key from row companionship)
- `render_order: int`
- `raw_text: str` (full rendered schedule block, including separator)
- `created_at: str`
- `updated_at: str`
- `source_person_updated_at: str | None` (copied from dashboard person row at build time)

### `ScheduleConflict`
- `conflict_id: str` (UUID)
- `conflict_type: str` (`TIME_CONFLICT` | `LOCATION_CONFLICT` | `DATA_CONFLICT`)
- `severity: str` (`red` for time, `yellow` for location, `yellow` for data unless escalated)
- `message: str`
- `affected_people: list[str]` (person IDs)
- `affected_locations: list[str]` (terminals/sections used by right panel)
- `anchors: list[ConflictAnchor]`
- `created_at: str`

### `ConflictAnchor`
- `block_id: str`
- `line_start: int` (1-based within `raw_text`)
- `line_end: int` (1-based within `raw_text`)
- `char_start: int | None`
- `char_end: int | None`
- `highlight_token: str | None`

### `ScheduleMetadata`
- `schedule_version: int`
- `generated_at: str`
- `generated_by_operation: str` (`create` | `fix`)
- `source_dataset_version: int`
- `source_dataset_last_imported_at: str | None`
- `source_max_person_updated_at: str | None`
- `pseudo_code_version_ref: str` (path and hash/timestamp reference)
- `block_count: int`
- `conflict_count: int`

### `ScheduleError`
- `code: str`
- `message: str`
- `person_id: str | None`
- `field: str | None`
- `suggested_action: str | None`

## Backend Service Interfaces
Required backend service contracts:

- `create_schedule(confirm_overwrite: bool) -> ScheduleBuildResult`
- `fix_schedule() -> ScheduleFixResult`
- `get_schedule_document() -> list[ScheduleBlock]`
- `list_schedule_conflicts() -> list[ScheduleConflict]`

Optional helper contracts (internal but recommended):
- `get_schedule_metadata() -> ScheduleMetadata | None`
- `resolve_schedule_dependencies(changed_person_ids: list[str]) -> set[str]`

## Create Schedule Pipeline

### 1) Confirmation Gate
- `create_schedule` must reject when `confirm_overwrite=False`.
- Required warning copy (exact string):
  - `WARNING, this will erase the current schedule in the transfer editor and regenerate a new schedule. Do you still want to continue?`

### 2) Source Snapshot
- Read current dashboard dataset in one consistent transaction/snapshot.
- Compute `source_max_person_updated_at` across all people for metadata.

### 3) Schedule Rendering
- Render each person's block using pseudo-code branches and formatting rules from `docs/transfer editor/transfer editor-pseudo-code.md`.
- Enforce:
  - Companion row lookup errors are explicit errors (not silent blanks).
  - Missing required time when needed is rendered as `00:00`.
  - UTF-8 text and Hangul are preserved in storage/output.
  - Block terminator line `-----------------------------------` included per person.

### 4) Output Ordering
- Group schedule blocks by current zone section.
- Within each zone, group by starting companionship.
- Ensure each person's block is directly adjacent to their current companion in final order.
- Persist deterministic `render_order`.

### 5) Conflict Scan
- Run full conflict detection pass across all rendered schedules.
- Generate conflict records and anchors for frontend right-panel alignment.

### 6) Atomic Publish
- Replace prior transfer schedule blocks/conflicts in a single transaction.
- Write new `ScheduleMetadata` with incremented `schedule_version`.

## Fix Schedule Delta Pipeline
`fix_schedule()` behavior is delta-based, not full rebuild.

### Delta Detection Rule
- Detect changed people by comparing dashboard person `updated_at` to `ScheduleMetadata.source_max_person_updated_at` or per-block `source_person_updated_at`.
- Baseline must come from last successful schedule generation (create/fix).

### Dependency Closure Rule
For every changed person, include:
- Their current companion row.
- Their new companion row.
- Anyone who references them as current companion or new companion.
- Companion chains required by pseudo-code logic (for example NCCC lookups).

### Delta Rebuild Steps
1. Resolve changed person IDs.
2. Expand to dependency closure.
3. Re-render only affected blocks.
4. Recompute output ordering for impacted companionship groups/zones.
5. Re-run global conflict detection across full active schedule.
6. Publish changed blocks + refreshed conflicts atomically with incremented `schedule_version`.

If no rows are changed:
- Return success with `blocks_rebuilt=0`.
- Keep schedule content unchanged.
- Optionally still refresh conflict scan if configured; default behavior is no-op.

## Conflict Detection Rules
Conflict detection includes, but is not limited to, these rules.

### `TIME_CONFLICT` (severity `red`)
- Person is instructed to drop off companion at time `T_dropoff` but own departure time is earlier than `T_dropoff`.
- Second-leg handoff impossible:
  - Person arrives at second departure terminal at `T_arrive_second_terminal`, but second departure time is earlier than arrival.
- Companion rendezvous impossible:
  - Required wait/no-wait logic contradicts actual final arrival time of new companion.
- Any cross-person instruction where a referenced companion time and actor time create an impossible sequence.

### `LOCATION_CONFLICT` (severity `yellow`)
- Second-leg transition mismatch:
  - First-leg `arrival_terminal` differs from `second_departure_terminal` and no travel gap instruction resolves it.
- Companion handoff location mismatch:
  - Instructioned handoff location differs across paired companion schedule blocks.

### `DATA_CONFLICT` (default severity `yellow`)
- Required companion row missing for pseudo-code lookup.
- Required field missing for deterministic instruction branch when fallback is not allowed.
- Invalid relationship topology (cyclic or unresolved companion references affecting deterministic output).

### Conflict Message Contract
- Message format should be human-readable and actionable.
- Example:
  - `FirstName LastName has a time conflict in their schedule.`
- Each conflict must include affected locations for right-panel rendering and only appear next to affected block anchors.

## Persistence Contract
Transfer editor backend persistence can be in existing SQLite database with new tables.

Required tables:
- `transfer_schedule_blocks`
  - `block_id` (PK), `schedule_version`, `person_id`, `person_display_name`, `current_zone`, `starting_companionship_key`, `render_order`, `raw_text`, `source_person_updated_at`, `created_at`, `updated_at`
- `transfer_schedule_conflicts`
  - `conflict_id` (PK), `schedule_version`, `conflict_type`, `severity`, `message`, `affected_people_json`, `affected_locations_json`, `anchors_json`, `created_at`
- `transfer_schedule_meta`
  - `schedule_version` (PK), `generated_at`, `generated_by_operation`, `source_dataset_version`, `source_dataset_last_imported_at`, `source_max_person_updated_at`, `pseudo_code_version_ref`, `block_count`, `conflict_count`

Recommended indexes:
- `transfer_schedule_blocks(schedule_version, render_order)`
- `transfer_schedule_blocks(person_id, schedule_version)`
- `transfer_schedule_conflicts(schedule_version, conflict_type, severity)`

## Error Model and Observability
Error categories:
- `CONFIRMATION_REQUIRED`
- `SOURCE_DATA_MISSING`
- `PSEUDOCODE_RENDER_ERROR`
- `DEPENDENCY_RESOLUTION_ERROR`
- `TIME_CONFLICT`
- `LOCATION_CONFLICT`
- `DATA_CONFLICT`
- `PERSISTENCE_ERROR`
- `UNKNOWN_ERROR`

Every surfaced error must include:
- `code`
- `message`
- `person_id` (when applicable)
- `field` (when applicable)
- `suggested_action` (when applicable)

Structured logs must include:
- Schedule build start/end (`create`/`fix`).
- Record counts (`people_read`, `blocks_generated`, `blocks_rebuilt`, `conflicts_found`).
- Delta sets (`changed_people`, `dependency_expansion_count`).
- Publish transaction success/failure and rollback events.

## Performance Targets
For 100-150 person records on typical mission hardware:
- Full `create_schedule`: target `<= 2s`.
- `fix_schedule` with small delta (<= 20 affected people): target `<= 700ms`.
- Global conflict scan after build/fix: target `<= 300ms`.
- `get_schedule_document` read path: target `<= 150ms`.

## Acceptance Criteria (Backend)
- `create_schedule` requires explicit confirmation and exact warning copy support.
- Generated schedules follow pseudo-code logic and formatting requirements.
- Final output ordering is deterministic and companion-adjacent within zone groupings.
- `fix_schedule` updates only changed + dependency-impacted blocks using `updated_at` delta logic.
- Time conflicts are classified as `TIME_CONFLICT` and mapped to `red`.
- Location conflicts are classified as `LOCATION_CONFLICT` and mapped to `yellow`.
- Missing companion rows generate explicit `DATA_CONFLICT` errors.
- Missing required time values use `00:00` where pseudo-code specifies fallback.
- UTF-8 and Hangul are preserved in stored and returned schedule text.
- Schedule publish is transactional and rollback-safe.

## Test Cases and Scenarios
1. Create schedule happy path:
- Valid dashboard dataset produces full block set and metadata with no errors.

2. Confirmation enforcement:
- `create_schedule(confirm_overwrite=False)` returns `CONFIRMATION_REQUIRED` and no data mutation.

3. Pseudo-code branch fidelity:
- `staying=yes/no`, `subway`, `second_leg=yes/no`, and training-zone branches render expected instructions.

4. Missing companion row:
- Companion lookup failure emits `DATA_CONFLICT` and targeted actionable error.

5. Missing required time fallback:
- Required but absent time renders as `00:00` when rule requires replacement.

6. Time conflict examples:
- Drop-off time later than own departure.
- Second-leg departure before second-leg arrival.
- Companion wait/no-wait contradiction.

7. Location conflict examples:
- First-leg arrival terminal differs from second departure terminal without resolvable instruction.

8. Delta fix minimal rebuild:
- Only edited person + dependency closure blocks are rebuilt; unaffected blocks remain unchanged.

9. No-op fix:
- No changed records returns success with `blocks_rebuilt=0`.

10. Transaction rollback:
- Simulated persistence error during publish leaves previous schedule version intact.

11. Anchor integrity:
- Every conflict anchor references an existing block and valid line range.

12. Unicode/Hangul preservation:
- Hangul terminals/zones round-trip through storage without corruption.

## Assumptions and Defaults
- Backend remains Python-based and uses existing local SQLite persistence.
- Transfer editor source data is dashboard canonical schema and normalized values.
- `Fix Schedule` baseline is last successful transfer schedule metadata version.
- Transfer editor conflict detection reports issues; it does not auto-correct dashboard data.
- Pseudo-code file remains source of truth for sentence-level schedule generation behavior.
