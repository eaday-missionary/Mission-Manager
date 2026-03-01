# Transfer Editor Epic Frontend Spec

## Purpose and Scope
This document defines transfer editor frontend behavior for schedule viewing, conflict visibility, and schedule regeneration workflows.

In scope:
- Transfer Editor tab/page navigation.
- Rendering generated schedule text from backend output.
- Conflict highlighting and right-panel conflict messaging.
- User interactions for `Create Schedule`.
- Frontend error/loading/empty states and accessibility behavior.

Out of scope:
- Editing dashboard person fields directly in Transfer Editor.
- Auto-resolving conflicts in the UI.
- Cloud collaboration and multi-user conflict handling.

## Information Architecture
Primary views and entry points:
- `Dashboard` tab (source dataset management and schedule actions).
- `Transfer Editor` tab (schedule text + conflict panel).
- `Schedule Text` tab (single continuous combined schedule text for copy/paste).

Navigation/ownership rules:
- Users access transfer editor via the top tab row.
- `Create Schedule` is initiated from Dashboard context and updates Transfer Editor content.
- Transfer Editor remains read-focused; corrections are made in dashboard data and synchronized automatically after successful data mutations.

## UI Layout Contract
Transfer Editor page is two-pane:
- Left pane: scrollable schedule card list (`ScheduleBlock` list in render order).
- Right pane: conflict panel showing conflict entries anchored to affected schedule blocks.
- `Schedule Text` tab: one read-focused text surface that concatenates all schedule block `raw_text` content in render order.

Required layout behavior:
- `FR-001` Left pane must support vertical scrolling across complete generated schedule-card output.
- `FR-002` Right pane must remain visible while left pane scrolls.
- `FR-033` A transfer-editor search bar must be shown above the two panes for schedule-text lookup.
- `FR-003` Each schedule block must render inside a boxed card preserving line breaks and separator line `-----------------------------------`.
- `FR-004` Right pane entries must only include conflicts that affect currently loaded schedule blocks.
- `FR-005` Empty conflict state must display a positive no-conflict message instead of blank panel.
- `FR-031` Transfer editor text and conflict panel surfaces must use dark backgrounds with white-readable text.
- `FR-032` Transfer editor scrollbars must use the shared app sleek solid scrollbar styling for visual consistency.

## Visual Conflict Semantics
- `FR-006` Time conflicts must be highlighted in red in the schedule text.
- `FR-007` Time conflict messages in the right panel must use red text.
- `FR-008` Location conflicts must be highlighted in yellow in the schedule text.
- `FR-009` Location conflict messages in the right panel must use yellow text.
- `FR-010` Data conflicts must use warning styling (yellow by default) and appear in the right panel with actionable wording.
- `FR-011` Inline highlights and right-panel entries must map consistently via backend conflict anchors.

## Interaction Requirements

### Create Schedule
- `FR-012` Dashboard `Create Schedule` action must show confirmation warning before execution.
- `FR-013` Warning copy must exactly match:
  - `WARNING, this will erase the current schedule in the transfer editor and regenerate a new schedule. Do you still want to continue?`
- `FR-014` Canceling confirmation must leave current transfer editor schedule unchanged.
- `FR-015` Confirming must refresh transfer editor document and conflict panel from latest backend schedule version.

### Regenerate Schedule After Edits
- `FR-016` Successful dashboard data mutations (`Apply`, `Add`, `Import`, `Append`, `Replace`) must automatically refresh transfer editor content.
- `FR-017` Refresh flow should preserve scroll position where possible; if affected block moved, focus nearest matching block.
- `FR-045` Successful `Clear Dataset` must clear transfer-derived UI outputs (`Transfer Editor` and `Schedule Text`).
- `FR-047` Successful `Replace Dataset` must trigger automatic transfer-output regeneration; if regeneration fails, previous transfer outputs remain visible and an actionable error is shown.

### Transfer Editor Read/Review Interaction
- `FR-019` Clicking a conflict entry in right panel must scroll/jump to associated schedule block anchor.
- `FR-043` Conflict-entry jump targets must land with the selected anchor centered at a fixed viewport center position (within pixel-rounding tolerance).
- `FR-020` Clicking highlighted text should set corresponding right-panel conflict entry as active.
- `FR-021` Active conflict selection must have distinct visual emphasis in both panes.
- `FR-022` Transfer editor content must render UTF-8 safely and preserve Hangul text.
- `FR-040` Double-clicking a schedule card must open the matching person in `Person Detail`.
- `FR-041` Schedule cards in transfer editor must remain read-only; data editing happens in `Person Detail`.
- `FR-034` Search must execute as user types (character-by-character) using case-insensitive contains matching on schedule text.
- `FR-035` When query contains matches, transfer editor must auto-scroll to the first match and mark it active.
- `FR-036` Search must support Up/Down keyboard navigation through matches with wrap-around.
- `FR-044` Search first/next/previous jumps must keep the active match anchor in the same viewport center spot without cumulative drift.
- `FR-037` `Ctrl+F` must focus the transfer-editor search bar only when the Transfer Editor tab is active.
- `FR-038` Search highlights must render with:
  - All matches: light sky blue (`#87CEFA`)
  - Active match: light turquoise (`#40E0D0`)
- `FR-039` Search highlight colors must take precedence over conflict line highlight colors for overlapping text spans.
- `FR-046` `Schedule Text` must render all generated schedule block text as one continuous copyable text document with no per-block card wrappers.

## Functional Requirements
- `FR-023` Transfer editor must render schedule blocks in backend-provided deterministic order.
- `FR-024` Zone headers and companionship adjacency in output must be preserved in final rendered document.
- `FR-042` Zone headers must remain visible above grouped schedule cards in rendered order.
- `FR-025` Document refresh after create must be atomic from user perspective (no mixed old/new blocks).
- `FR-026` System must show loading state while schedule build fetch is in progress.
- `FR-027` System must show actionable error banners for build/read failures.
- `FR-028` Right-panel conflict list must include:
  - Person display name(s)
  - Conflict type (time/location/data)
  - Affected location(s)
  - Human-readable message
- `FR-029` Conflict list should be grouped by severity/type with stable ordering.
- `FR-030` If no schedule exists yet, transfer editor must show empty-state guidance to run `Create Schedule`.

## Interaction and Feedback Standards
- `UX-001` Loading indicators must appear for create and initial transfer editor load.
- `UX-002` Success notifications must confirm create completion and conflict totals.
- `UX-003` Error messages must include what failed and next step (retry, check dashboard data, or open data management).
- `UX-004` Destructive or overwriting actions must require explicit confirmation.
- `UX-005` Right panel must avoid dead-end error states; each critical issue includes recovery instruction.
- `UX-007` Transfer editor dark surfaces, text contrast, and scrollbar visuals must remain consistent with the global app theme.

## Accessibility and Usability Requirements
- `ACC-001` Keyboard navigation must support:
  - Tab traversal between controls and panes.
  - Enter/Space activation for create and conflict selection.
  - Up/Down search result traversal when focus is in transfer search bar.
  - `Ctrl+F` shortcut focus for transfer search when Transfer Editor tab is active.
- `ACC-002` Focus must be managed after create completion (focus returned to primary transfer editor region).
- `ACC-003` Highlight colors must meet readable contrast requirements with text/background.
- `ACC-004` Conflict state must not rely on color alone; include icon/label text such as `Time Conflict` and `Location Conflict`.
- `ACC-005` Scroll-jump operations must announce context change for assistive technologies when supported.

## Performance and Responsiveness Requirements
- `PERF-001` Transfer editor document load target: `<= 500ms` for 100-150 schedule blocks.
- `PERF-002` Conflict panel render/refresh target: `<= 200ms` after receiving backend response.
- `PERF-003` Conflict anchor jump target: perceived instant, `<= 100ms` for scroll-to-block action.
- `UX-006` Layout must remain usable at minimum supported app size (`1100x680`).

## Acceptance Criteria

### Schedule Display
- Transfer editor shows generated schedule cards in a scrollable left pane.
- Block separators and line formatting are preserved exactly as generated inside each card.
- Zone grouping and companion adjacency are visible in rendered order.
- Transfer editor surfaces remain dark-themed with readable white text and consistent scrollbar styling.
- Double-clicking a card opens that person in Person Detail.
- Schedule Text tab shows one continuous combined text output in render order for full-document copy/paste.

### Conflict Visibility
- Time conflicts are red inline + red in right panel.
- Location conflicts are yellow inline + yellow in right panel.
- Conflict entries map correctly to highlighted schedule segments.
- Right panel only shows messages for affected schedule blocks.

### Create Workflow
- `Create Schedule` always prompts exact required warning text before overwrite.
- Canceling create does not change existing schedule.
- Confirmed create refreshes schedule and conflict panel to latest version.

### States and Errors
- Empty state instructs user to run `Create Schedule`.
- Loading, success, and error feedback are clear and actionable.
- Read failures, generation failures, and conflict retrieval failures are recoverable via retry.

### Accessibility
- Primary controls and conflict navigation are keyboard-usable.
- Focus and active-selection indicators are visible and consistent.
- Search and conflict jumps land the active anchor at the same center position (within pixel-rounding tolerance).

## Frontend Test Scenarios
1. Empty state:
- No transfer schedule exists -> prompt to run `Create Schedule`.

2. Create confirmation:
- Warning dialog appears with exact required text.
- Cancel path keeps current schedule unchanged.
- Confirm path refreshes document and conflicts.

3. Time conflict rendering:
- Backend `TIME_CONFLICT` anchors produce red inline highlight and red panel entry.

4. Location conflict rendering:
- Backend `LOCATION_CONFLICT` anchors produce yellow inline highlight and yellow panel entry.

5. Anchor synchronization:
- Clicking panel message jumps to matching highlight.
- Selecting highlight activates matching panel message.

6. No-conflict rendering:
- No conflicts returns explicit success/no-conflict panel text.

7. Automatic refresh after edits:
- After successful source-data mutations, transfer content refreshes automatically using current data.
- Manual `Create Schedule` remains available as fallback force-refresh.

8. Large list responsiveness:
- 100-150 blocks remain scrollable and responsive at target thresholds.

9. Encoding safety:
- Hangul and UTF-8 content displays without corruption in document and conflict panel.

10. Keyboard accessibility:
- User can navigate and activate critical actions and conflict entries without mouse.

11. Transfer search live behavior:
- Typing in transfer search updates results per character and auto-jumps to first match.
- Up/Down cycles through matches and wraps from end to start and start to end.
- `Ctrl+F` focuses search entry only while Transfer Editor tab is active.
- Overlapping conflict spans still show search highlight colors for matched text.

12. Card interaction:
- Schedule renders as one boxed card per person block with zone headers retained.
- Double-clicking a card opens that person in Person Detail.

13. Center-lock jump behavior:
- Repeated search next/previous navigation does not drift upward/downward over time.
- Clicking conflict entries lands each target anchor at the fixed center position (bounds permitting).

14. Schedule Text rendering:
- Combined text includes all generated schedule block `raw_text` output in render order.
- After `Clear Dataset`, Schedule Text shows empty-state guidance.
- After successful `Replace Dataset`, Schedule Text refreshes automatically from regenerated schedule output.

## Assumptions and Defaults
- Transfer editor schedule content is backend-authored; frontend does not re-interpret pseudo-code logic.
- Conflict severity/color mapping is backend-driven and frontend-rendered consistently.
- Transfer editor remains read-only for schedule text; corrections happen in dashboard data.
