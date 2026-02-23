# Transfer Editor Epic User Journeys

## Purpose
This document defines end-to-end user journeys for mission office staff using the Transfer Editor workflow, including schedule generation, review, conflict detection, and fix cycles.

## Persona
### Mission Office Staff
- High-frequency operational user coordinating transfers.
- Needs clear conflict visibility and rapid correction loops.
- Uses Dashboard as source-of-truth editor and Transfer Editor as schedule verification surface.

## Journey Format
Each journey uses:
- `Goal`
- `Preconditions`
- `Steps`
- `System Response`
- `Outcome`
- `Failure Path`

## Journey 1: First-Time Navigation to Transfer Editor
- `JRNY-001 Goal`: Reach transfer editor and understand next action when no schedule exists.
- `Preconditions`: Dashboard dataset is loaded; no transfer schedule generated yet.
- `Steps`:
  1. User opens app and views top tab navigation.
  2. User clicks `Transfer Editor` tab.
  3. User observes transfer editor empty state.
- `System Response`:
  - Shows two-pane transfer editor layout.
  - Uses dark transfer-editor surfaces with readable light text and consistent solid scrollbars.
  - Displays empty-state message directing user to run `Create Schedule`.
  - Shows no-conflict placeholder state in right panel.
- `Outcome`: User understands schedule must be generated first.
- `Failure Path`: If transfer editor fails to load, system shows recoverable error with retry and dashboard-return actions.

## Journey 2: Create Schedule from Dashboard with Confirmation
- `JRNY-002 Goal`: Generate complete transfer schedule from dashboard data.
- `Preconditions`: Dashboard has valid person records.
- `Steps`:
  1. User scrolls to dashboard schedule actions.
  2. User clicks `Create Schedule`.
  3. Confirmation warning appears.
  4. User confirms creation.
  5. User navigates to `Transfer Editor`.
- `System Response`:
  - Warning message text is exact:
    - `WARNING, this will erase the current schedule in the transfer editor and regenerate a new schedule. Do you still want to continue?`
  - On confirm, backend regenerates all schedule blocks and conflict records.
  - Transfer editor reloads schedule + conflicts for newest schedule version.
- `Outcome`: Full schedule is available for review.
- `Failure Path`: If user cancels warning, no schedule overwrite occurs; if generation fails, user gets actionable error and retry guidance.

## Journey 3: Review Grouped Schedule Output
- `JRNY-003 Goal`: Verify that output organization supports operational review.
- `Preconditions`: Schedule exists.
- `Steps`:
  1. User opens transfer editor schedule.
  2. User scans zone headers.
  3. User reviews blocks grouped by companionship.
  4. User confirms each person is adjacent to current companion.
- `System Response`:
  - Schedule text shows deterministic render order:
    - Grouped by current zone.
    - Grouped by starting companionship within zone.
    - Current companions adjacent.
  - Each block ends with separator line.
- `Outcome`: User can quickly review by operational grouping.
- `Failure Path`: If ordering is inconsistent, conflict/data warning surfaces and user is guided to regenerate or inspect source rows.

## Journey 4: Identify and Resolve Time Conflicts (Red)
- `JRNY-004 Goal`: Find and resolve timing inconsistencies.
- `Preconditions`: Generated schedule includes one or more time conflicts.
- `Steps`:
  1. User opens transfer editor and sees red highlights.
  2. User checks right panel red conflict entries.
  3. User clicks a red conflict entry to jump to affected schedule text.
  4. User returns to dashboard and edits relevant time fields.
  5. User triggers `Fix Schedule`.
- `System Response`:
  - Red inline highlights match red right-panel entries.
  - Right panel lists affected people and locations.
  - `Fix Schedule` rebuilds changed/dependent blocks and refreshes conflict set.
- `Outcome`: Corrected time conflicts disappear or reduce after fix cycle.
- `Failure Path`: If conflicts remain, entries persist with updated messaging and exact affected locations.

## Journey 5: Identify and Resolve Location Conflicts (Yellow)
- `JRNY-005 Goal`: Find and resolve terminal/location mismatches.
- `Preconditions`: Schedule includes one or more location conflicts.
- `Steps`:
  1. User views yellow highlighted schedule segments.
  2. User selects yellow conflict in right panel.
  3. User confirms mismatch details (for example first arrival vs second departure terminal).
  4. User edits dashboard location fields.
  5. User runs `Fix Schedule`.
- `System Response`:
  - Yellow inline highlights map to yellow right-panel entries.
  - Conflict messages specify affected locations.
  - Fix refresh updates only impacted schedule blocks and all conflict summaries.
- `Outcome`: Location inconsistencies are cleared or narrowed for follow-up.
- `Failure Path`: Unresolved location issues remain visible with actionable guidance.

## Journey 6: Run Fix Schedule After Targeted Dashboard Edits
- `JRNY-006 Goal`: Apply fast incremental schedule updates without full regeneration.
- `Preconditions`: Existing schedule version exists; user edited one or more dashboard records.
- `Steps`:
  1. User edits person data in dashboard.
  2. User clicks `Fix Schedule`.
  3. User opens transfer editor to review updates.
- `System Response`:
  - Backend detects changed people using `updated_at` since last schedule generation marker/version.
  - Backend rebuilds changed records plus companion/dependency closure.
  - UI reports whether blocks were rebuilt or no changes were found.
- `Outcome`: Transfer editor reflects recent edits with minimal regeneration overhead.
- `Failure Path`: If delta detection fails, system reports issue and offers full `Create Schedule` fallback.

## Journey 7: Companion Dependency Cascade Handling
- `JRNY-007 Goal`: Ensure linked companion instructions stay coherent after one edit.
- `Preconditions`: Edited person participates in companion lookups/instructions.
- `Steps`:
  1. User updates a person tied to companion chains.
  2. User runs `Fix Schedule`.
  3. User reviews both directly edited and dependency-related blocks.
- `System Response`:
  - Fix operation expands update set to include required companion/dependency rows.
  - Affected blocks are rebuilt together to keep instructions coherent.
  - Conflict panel updates globally after rebuild.
- `Outcome`: Companion-linked instructions remain internally consistent.
- `Failure Path`: Missing dependency rows are flagged as data conflicts with person-level identifiers.

## Journey 8: Recover from Data Conflicts and Missing Companion References
- `JRNY-008 Goal`: Recover from source-data conditions that prevent deterministic schedule instructions.
- `Preconditions`: Source data has missing companion references or invalid dependency relationships.
- `Steps`:
  1. User runs create/fix operation.
  2. System reports data conflict entries.
  3. User navigates to dashboard and corrects companion fields.
  4. User reruns fix/create.
- `System Response`:
  - Data conflicts are listed in right panel with warning styling and actionable messages.
  - Companion lookup errors are explicit (not treated as blank).
  - On rerun, corrected rows render normally and stale data conflicts clear.
- `Outcome`: Schedule returns to deterministic and readable output.
- `Failure Path`: Repeated invalid references keep conflicts visible and prevent silent data corruption.

## Journey 9: No-Conflict Success Path
- `JRNY-009 Goal`: Confirm that a clean schedule is easy to validate.
- `Preconditions`: Schedule generated with no time/location/data conflicts.
- `Steps`:
  1. User opens transfer editor.
  2. User scans schedule blocks and right panel.
  3. User confirms no conflict indicators are present.
- `System Response`:
  - No inline highlights are rendered.
  - Right panel shows explicit no-conflict state.
  - Metadata or status confirms latest schedule version is active.
- `Outcome`: User can finalize schedule confidence quickly.
- `Failure Path`: If stale conflict cache is detected, UI prompts refresh/reload to reconcile.

## Journey 10: Large Dataset Responsiveness and Usability
- `JRNY-010 Goal`: Maintain usable workflow at mission-scale record counts.
- `Preconditions`: Dataset size is approximately 100-150 people.
- `Steps`:
  1. User creates or fixes schedule for full dataset.
  2. User scrolls through schedule text.
  3. User navigates conflict entries and jumps between anchors.
- `System Response`:
  - Create/fix feedback remains timely.
  - Scrolling and anchor jumps stay responsive.
  - Scrollbar interactions remain visually consistent and usable across document and conflict panes.
  - Two-pane layout remains usable at minimum app window size.
- `Outcome`: User can operate full transfer cycle without performance bottlenecks.
- `Failure Path`: If thresholds are exceeded, UI surfaces operation delay state and preserves safe retry path.

## Journey 11: Locate Schedule Mentions Quickly with Live Search
- `JRNY-011 Goal`: Find repeated schedule text occurrences quickly without manual scrolling.
- `Preconditions`: Transfer schedule exists and is loaded in Transfer Editor.
- `Steps`:
  1. User presses `Ctrl+F` while Transfer Editor tab is active.
  2. User types a search string in the transfer search bar.
  3. User sees auto-jump to first matching occurrence in the schedule pane.
  4. User presses Down to move to next match and Up to move to previous match.
- `System Response`:
  - Search updates character-by-character with case-insensitive contains matching.
  - All matches are highlighted in light sky blue and active match is highlighted in light turquoise.
  - Up/Down navigation wraps at boundaries (last -> first, first -> last).
  - Search-highlight colors remain visible even when matched text overlaps conflict-highlighted lines.
- `Outcome`: User reviews all relevant schedule occurrences quickly and accurately.
- `Failure Path`: If no matches are found, UI shows `0 matches`; user can clear or adjust query and retry.

## Cross-Journey UX Rules
- `UX-007` Must use consistent loading/success/error patterns across create, fix, and read actions.
- `UX-008` Must use exact destructive warning copy for schedule overwrite.
- `UX-009` Must provide actionable recovery guidance in all failure paths.
- `UX-010` Must preserve text encoding and readability for UTF-8/Hangul output.
- `UX-011` Must avoid dead-end states; every error includes next-step action.

## Journey Acceptance Checklist
- [ ] Every journey includes Goal, Preconditions, Steps, System Response, Outcome, and Failure Path.
- [ ] `Create Schedule` overwrite warning text is exact and documented.
- [ ] Time conflicts are documented as red in text and panel.
- [ ] Location conflicts are documented as yellow in text and panel.
- [ ] Data conflicts and missing companion behavior are explicit and recoverable.
- [ ] `Fix Schedule` delta behavior is documented using `updated_at` + dependency closure.
- [ ] Grouped output behavior (zone + companionship + adjacency) is documented.
- [ ] No-conflict path is explicitly defined.
- [ ] Performance journey exists for 100-150 record usage.
- [ ] Search journey covers live typing, keyboard navigation, and `Ctrl+F` focus behavior.

## Documentation Conventions and Traceability
- Requirement ID prefixes:
  - Functional: `FR-`
  - User experience: `UX-`
  - Performance: `PERF-`
  - Accessibility: `ACC-`
  - Journeys: `JRNY-`
- Normative terms:
  - `Must`: required for epic completion.
  - `Should`: recommended improvement.
