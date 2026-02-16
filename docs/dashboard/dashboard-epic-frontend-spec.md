# Dashboard Epic Frontend Spec

## Purpose and Scope
This document defines how the dashboard frontend looks, behaves, and responds to mission office staff during data import, discovery, editing, and local data management.

In scope:
- Excel import as the primary data entry path.
- Browsing all records in a list/table view.
- Fast search, filtering, and sorting for approximately 100-150 records.
- Viewing and editing individual person records.
- Local persistence, append, and full dataset replacement flows.

Out of scope (for this iteration):
- Authentication and role-based permissions.
- Cloud sync or cross-device data sharing.
- Multi-user simultaneous editing/conflict resolution.
- Audit history/version log UI.

## Target Users
### Mission Office Staff
- High-frequency operational users managing many records.
- Need reliable bulk review workflows and quick corrections.
- Need safe destructive actions with clear confirmations.

## Person Record Data Contract (Excel Source)
All records imported from Excel must map to this contract. Every field label must be shown in the UI for every person, even when the value is missing.

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

Value display rules:
- `FR-028` Must display all 19 field labels for each person in detail view and structured row/table contexts.
- `FR-029` Must render missing values as `-`.
- `FR-030` Must treat time values as strict `HH:mm` for validation, sorting, and display.

## Information Architecture
Primary frontend views:
- `View A: Onboarding / Import State` (no usable local dataset yet).
- `View B: Main Dashboard List` (search/filter/sort + record browsing).
- `View C: Person Detail / Edit` (read/edit single record).
- `View D: Data Management` (append dataset, replace dataset, storage status).

Navigation model:
- App launch routes to View B when valid local data exists, else View A.
- Selecting a record in View B opens View C.
- Data operations from View D return users to View B on success.
- Cancel in View C returns users to the exact prior list context (filters/sort/query retained).

## Core UX Requirements
- `FR-001` Must support importing one Excel file (`.xlsx`/`.xlsm`/`.xls`) to create a dataset.
- `FR-002` Must show parsing/validation feedback before committing imported data.
- `FR-003` Must provide global text search across key person fields.
- `FR-004` Must provide field-specific filters.
- `FR-005` Must support column sorting with ascending/descending direction.
- `FR-006` Must allow selecting one record to open detailed view.
- `FR-007` Must allow editing a record in a dedicated detail form (panel/page/modal).
- `FR-008` Must provide explicit Apply and Cancel actions for edits.
- `FR-009` Must support append import that adds records to the existing dataset.
- `FR-010` Must support full dataset reset/replace behind confirmation safeguards.
- `UX-001` Must preserve user context (search/filter/sort/page position) when returning from detail view.
- `UX-002` Should prefer progressive disclosure: show advanced controls only when needed.
- `FR-031` Must support global search across all 19 fields using case-insensitive contains matching.
- `FR-032` Must set default list sorting to `Current Zone` in alphabetical order.
- `FR-033` Must support filter/sort controls for: `Current Area`, `New Zone`, `New Area`, `First Name` (A-Z), `Last Name` (A-Z), `Departure Time` (earliest-latest), `Arrival Time` (earliest-latest), `Second Leg?` (yes/no), `2nd Departure Time` (earliest-latest), and `2nd Arrival Time` (earliest-latest).
- `FR-034` Must interpret `Second Leg?` as yes/no filter values.

## Screen-Level Functional Requirements
### Initial/Empty State
- `FR-011` Must show a clear prompt to upload the first spreadsheet.
- `FR-012` Must display accepted file types and basic formatting guidance.
- `FR-013` Must provide immediate error messaging for unsupported file type or unreadable file.
- `FR-035` Must show schema-mismatch messaging when required columns are missing or invalid.

### Main Dashboard State
- `FR-014` Must display records in a scannable list/table with stable columns.
- `FR-015` Must include search input, filter controls, and sortable columns.
- `FR-016` Must show total result count and currently visible result count.
- `FR-017` Must show a no-results state with quick actions to clear filters/search.
- `FR-036` Must apply default `Current Zone` alphabetical sort on first load and post-import load.
- `FR-037` Must refresh list results automatically as users type, sort, or change filters (no manual refresh action).
- `FR-038` Must show active sort/filter indicators clearly.
- `FR-040` Must provide two dashboard table modes:
  - `Full View`: all 19 columns visible at once without horizontal scrolling.
  - `Compact`: denser table with horizontal scrolling for full column access.

### Person Detail State
- `FR-018` Must display all editable fields for one selected person.
- `FR-019` Must validate required fields before apply and show inline errors.
- `FR-020` Must show inline success feedback after apply, persist changes locally, and keep the user in Person Detail view.
- `FR-039` Must show all 19 data labels with `-` where a value is missing.
- `FR-041` Must provide vertical scrolling in Person Detail so all fields are reachable at smaller window sizes.
- `FR-042` Must place `Apply` and `Cancel` in a fixed right-side action panel that remains visible while fields scroll.

### Data Management State
- `FR-021` Must show current dataset status (loaded timestamp, approximate count).
- `FR-022` Must provide append-data action using Excel import.
- `FR-023` Must provide replace-all-data action with explicit confirmation.

## Interaction and Feedback Standards
- `UX-003` Must show loading indicators for import, heavy filtering, and apply operations.
- `UX-004` Must show clear success notifications after import, append, replace, and apply.
- `UX-005` Must show actionable error messages (what happened + what to do next).
- `UX-006` Must require confirmation for destructive actions (replace/erase dataset).
- `UX-007` Must distinguish blocking errors (cannot continue) vs non-blocking warnings.

## Performance and Responsiveness Requirements
- `PERF-001` Must deliver perceived-instant interactions for list operations at 100-150 records.
- `PERF-002` Must target <=300 ms response for local search/filter/sort updates in typical usage.
- `PERF-003` Should keep first render of existing local dataset within acceptable interactive delay (target <=1 s on typical mission devices).
- `UX-008` Must remain usable on laptop and narrow/mobile widths for read and basic edit tasks.
- `UX-017` Must open at the configured minimum window size (`1100x680`) and remain usable at that size.

## Data Persistence Behavior (Frontend-visible)
- `FR-024` Must auto-save imported and edited data locally without requiring manual export.
- `FR-025` Must auto-load the latest valid local dataset on app restart.
- `FR-026` Must detect missing/corrupt local data and fall back to Import State with clear notice.
- `FR-027` Should include a lightweight local schema/version marker for future compatibility changes.

## Accessibility and Usability Requirements
- `ACC-001` Must support keyboard navigation for primary actions (search, row selection, apply/cancel, confirmations).
- `ACC-002` Must manage focus correctly in dialogs/forms (focus trap, return focus on close).
- `ACC-003` Must provide explicit field labels and plain-language validation errors.
- `ACC-004` Must maintain readable contrast and typography for common lighting conditions.

## Acceptance Criteria
### Import
- Uploading a valid Excel file with all required columns creates a visible dataset and routes the user to Main Dashboard.
- Invalid file types, malformed files, or missing required columns show actionable blocking errors.

### Search, Filter, Sort
- Search updates letter-by-letter and uses case-insensitive contains matching across all 19 fields.
- Default load order is `Current Zone` alphabetical.
- Supported filters/sorts include `Current Area`, `New Zone`, `New Area`, `First Name`, `Last Name`, `Departure Time`, `Arrival Time`, `Second Leg?`, `2nd Departure Time`, and `2nd Arrival Time`.
- Time fields sort in true chronological order using `HH:mm`.
- Full View shows all 19 columns simultaneously; Compact mode exposes all columns via horizontal scroll.

### Detail Edit
- User can open a person record, edit valid fields, apply, and immediately see updated values while remaining in detail view.
- User can reach every detail field via vertical scroll while keeping `Apply`/`Cancel` visible in the right action panel.
- All 19 labels are always shown; missing values display as `-`.
- Invalid edits are blocked with field-level error guidance.

### Local Persistence
- Closing/reopening the app reloads latest valid data and previous session can continue.
- If local data is unreadable, user is informed and guided to re-import.

### Replace/Append Dataset
- Append adds new rows without erasing existing rows unless duplicates are explicitly resolved by defined rules.
- Replace flow requires confirmation and fully swaps local dataset on success.

### Error Handling
- All critical failures surface concise, actionable messages.
- Non-critical warnings do not force app exit and offer recovery actions.

## Open Questions for Future Iterations
- Should duplicate resolution be manual, automatic, or rule-based by key columns?
- Should the app support export/backups of the local dataset?
- Is cloud synchronization required for multi-device usage?
- Is edit history/audit trail required?


## Implementation Note
- Current implementation supports canonical headers and known sample-header aliases (for example `Transfer to Zone`, `Staying?`, `Departing Terminal`) which are normalized internally.
- Dashboard search is global (no field dropdown), refresh is automatic, and the UI uses a built-in dark themed style.
