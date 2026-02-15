# Dashboard Epic User Journeys

## Purpose
This document describes ideal end-to-end user journeys for mission office staff interacting with the dashboard frontend. Each journey defines what users see, what they do, and how the system should respond in both success and edge/failure paths.

## Persona
### Mission Office Staff
- High-volume operational user.
- Prioritizes speed, consistency, and safe data management controls.

## Person Record Data Used in Journeys
Every person record in every journey uses this schema:

| Field Name | Type |
| --- | --- |
| First Name | String |
| Last Name | String |
| Current Companion | String |
| New Companion | String |
| Current Zone | String |
| Current Area | String |
| New Zone | String |
| New Area | String |
| Staying or leaving? | Boolean |
| Pre Travel | String |
| Departure Terminal | String |
| Departure Time | Military Time Value (24h HH:mm) |
| Arrival Terminal | String |
| Arrival Time | Military Time Value (24h HH:mm) |
| Second Leg? | String |
| 2nd Departure Terminal | String |
| 2nd Departure Time | Military Time Value (24h HH:mm) |
| 2nd Arrival Terminal | String |
| 2nd Arrival Time | Military Time Value (24h HH:mm) |

Shared display/search rules:
- Missing values render as `-` while labels remain visible.
- All 19 fields are individually searchable.
- Default list sorting is `Current Zone` alphabetical.

## Journey Format
Each journey uses this schema:
- `Goal`: user intent.
- `Preconditions`: required starting state.
- `Steps`: ordered user-visible interaction flow.
- `System Response`: expected frontend feedback/state transitions.
- `Outcome`: definition of success.
- `Failure Path`: expected behavior when errors or edge cases occur.

## Journey 1: First-Time Setup and Initial Excel Import
- `JRNY-001 Goal`: Load first dataset so dashboard can be used.
- `Preconditions`: No existing local dataset.
- `Steps`:
  1. Staff user opens app and sees empty/onboarding import screen.
  2. Staff user selects Excel file and confirms import.
  3. Staff user reviews parsing summary and proceeds.
- `System Response`:
  - Shows loading state during parse.
  - Displays validation summary (records imported, warnings/errors).
  - Validates required schema columns for the 19-field contract.
  - Routes to Main Dashboard after successful commit.
- `Outcome`: Dataset is available for search/filter/sort.
- `Failure Path`: Invalid file or parse/schema failure keeps user on import screen with actionable error and retry option.

## Journey 2: Returning User with Auto-Loaded Local Data
- `JRNY-002 Goal`: Resume work immediately without re-import.
- `Preconditions`: Valid local dataset exists.
- `Steps`:
  1. Staff user opens app.
  2. Dashboard loads directly into list view.
- `System Response`:
  - Restores dataset and displays current record count.
  - Applies default `Current Zone` alphabetical sorting.
  - Optionally displays last updated timestamp.
- `Outcome`: Staff user can continue tasks instantly.
- `Failure Path`: Corrupt local data triggers clear recovery notice and route to import flow.

## Journey 3: Field-Specific Search to Find One Person
- `JRNY-003 Goal`: Find one specific person quickly using field-level search.
- `Preconditions`: Dataset loaded.
- `Steps`:
  1. Staff user selects `Departure Terminal` in field selector.
  2. Staff user enters terminal value to narrow records.
  3. Staff user optionally refines by `Current Area`.
  4. Staff user selects target record.
- `System Response`:
  - Updates results and count in near real time.
  - Shows active field-search context.
  - Highlights empty/no-match state if none found.
- `Outcome`: Correct record opened in detail view.
- `Failure Path`: No results state offers clear action to reset query or switch fields.

## Journey 4: Default Zone Sort, Then Custom Filter + Sort
- `JRNY-004 Goal`: Build a focused working list for review.
- `Preconditions`: Dataset loaded with filterable fields.
- `Steps`:
  1. Staff user lands on default `Current Zone` alphabetical list.
  2. Staff user filters by `New Zone` and `Current Area`.
  3. Staff user overrides sort to `Departure Time` (earliest-latest).
  4. Staff user reviews subset and optionally switches to `Last Name` (A-Z).
- `System Response`:
  - Shows active filter chips/indicators.
  - Sort direction and active sort key remain visible.
  - Result count updates with each change.
- `Outcome`: Staff user obtains a stable, narrowed list matching operational needs.
- `Failure Path`: Invalid filter combination returns no-results guidance with one-click clear.

## Journey 5: Open a Person Record and Edit Information
- `JRNY-005 Goal`: Correct or update one person record.
- `Preconditions`: User is on list view with at least one record.
- `Steps`:
  1. Staff user opens person detail view.
  2. Staff user reviews all 19 labeled fields.
  3. Staff user edits one or more fields and saves.
- `System Response`:
  - Shows `-` for any missing values while preserving labels.
  - Validates required fields.
  - Shows inline errors for invalid values.
  - On success, confirms save and persists locally.
- `Outcome`: Updated values appear in detail and list views.
- `Failure Path`: Validation errors block save; user can fix and retry or cancel.

## Journey 6: Append New Spreadsheet Data to Existing Dataset
- `JRNY-006 Goal`: Add newly received records without losing current data.
- `Preconditions`: Existing local dataset loaded.
- `Steps`:
  1. Staff user navigates to Data Management.
  2. Staff user selects Append Data and uploads spreadsheet.
  3. Staff user reviews merge summary and confirms.
- `System Response`:
  - Validates required columns in append file.
  - Shows estimated added/updated/skipped counts (as supported).
  - Persists merged dataset locally on success.
  - Preserves available sort/filter behaviors after append completes.
- `Outcome`: Existing records remain; new applicable records added.
- `Failure Path`: If append fails, original dataset remains intact and user receives retry guidance.

## Journey 7: Replace Dataset (Erase and Re-import)
- `JRNY-007 Goal`: Replace entire dataset safely.
- `Preconditions`: Existing local dataset loaded.
- `Steps`:
  1. Staff user selects Replace Dataset in Data Management.
  2. Staff user reviews destructive action warning.
  3. Staff user confirms and uploads replacement file.
- `System Response`:
  - Requires explicit confirmation before erase.
  - Validates replacement schema before commit.
  - Replaces local dataset only after successful parse/validation.
  - Returns to list with default `Current Zone` alphabetical sorting.
- `Outcome`: New dataset fully replaces prior dataset.
- `Failure Path`: Failed replacement does not destroy existing dataset; user remains informed and can retry.

## Journey 8: Recover from Import Errors (Invalid/Missing Columns)
- `JRNY-008 Goal`: Recover from schema/format issues during import.
- `Preconditions`: User attempts import/append/replace with problematic file.
- `Steps`:
  1. Staff user uploads file.
  2. System flags missing/invalid columns from required 19-field schema.
  3. Staff user reviews guidance, fixes file externally, retries import.
- `System Response`:
  - Shows specific problematic columns/rows where possible.
  - Offers direct retry path.
- `Outcome`: Corrected file imports successfully.
- `Failure Path`: Repeated failure continues to surface actionable diagnostics without app crash.

## Journey 9: Empty Values vs No Results Recovery
- `JRNY-009 Goal`: Distinguish missing field values from true no-results states.
- `Preconditions`: Dataset loaded; some records contain missing values.
- `Steps`:
  1. Staff user opens a record with blank second-leg data.
  2. UI shows labels with `-` values.
  3. Staff user performs a filter/search combination that yields zero matching records.
- `System Response`:
  - Keeps record-level missing values as `-` when records are present.
  - Shows dedicated no-results state only when no records match criteria.
  - Provides direct recovery actions (clear filters/search).
- `Outcome`: Staff user clearly understands difference between incomplete data and empty result sets.
- `Failure Path`: If recovery action fails, UI provides clear next step rather than dead end.

## Journey 10: Accidental Destructive Action Avoidance
- `JRNY-010 Goal`: Prevent unintended data loss.
- `Preconditions`: Staff user initiates replace/erase action.
- `Steps`:
  1. Staff user clicks destructive option.
  2. Confirmation dialog explains impact and asks for explicit confirmation.
  3. Staff user cancels or confirms.
- `System Response`:
  - Cancel exits safely with no data change.
  - Confirm proceeds with clear progress status.
  - If post-confirmation error occurs, system keeps last valid dataset whenever possible.
- `Outcome`: Destructive actions occur only with explicit user intent.
- `Failure Path`: Any operation failure is surfaced with clear recovery actions.

## Cross-Journey UX Rules
- `UX-009` Must use consistent loading, success, and error feedback patterns.
- `UX-010` Must use consistent confirmation language for destructive actions.
- `UX-011` Must provide clear recovery actions in every error state.
- `UX-012` Should preserve user context when moving between list and detail views.
- `UX-013` Must avoid dead-end states; every major error includes a next action.
- `UX-014` Must maintain 19-field label visibility in all record detail states.
- `UX-015` Must keep field-level search available for all records.
- `UX-016` Must render missing values as `-` consistently across views.

## Journey Acceptance Checklist
- [ ] Persona usage is staff-only, with no ordinary missionary references.
- [ ] Every journey includes Goal, Preconditions, Steps, System Response, Outcome, and Failure Path.
- [ ] All 19 schema fields are documented consistently.
- [ ] Missing values are shown as `-` while labels remain visible.
- [ ] Every field is individually searchable.
- [ ] Default `Current Zone` alphabetical sort is documented.
- [ ] Alternate sort/filter behavior is documented for all requested fields.
- [ ] Search/filter/sort journeys define user-visible performance expectations.
- [ ] Edit journey includes validation and save/cancel outcomes.
- [ ] Append and replace journeys clearly separate non-destructive vs destructive behavior.
- [ ] Error-handling journeys define actionable recovery steps.

## Documentation Conventions and Traceability
- Requirement ID prefixes:
  - Functional requirements: `FR-`
  - User experience requirements: `UX-`
  - Performance requirements: `PERF-`
  - Accessibility requirements: `ACC-`
  - Journey IDs: `JRNY-`
- Normative terms:
  - `Must`: MVP-required behavior.
  - `Should`: Recommended, non-blocking enhancement.
- Journey schema contract:
  - `Goal`, `Preconditions`, `Steps`, `System Response`, `Outcome`, `Failure Path`.
