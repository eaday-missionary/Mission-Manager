# Transfer Editor Epic project requirements

Transfer Editor epic project requirements:

- This epic is a system that pulls all of the data from the main dashboard, and formats it into an organized travel schedule for each individual on the list. It will provide insight and error messages for any schedules that conflict, or otherwise seem strange, in order for the user to be able to easily spot and fix mistakes in the travel schedule.
-- Users will reach the "transfer editor" page by clicking on a tab located at the top of the screen, next to the "dashboard", "personal details", and "data management" tabs.
-- The transfer editor must pull the data directly located in the dashboard.
-- The dashboard must have a button at the bottom titled "Create Schedule" that generates the schedules list from the data in the dashboard using the pseudo-code instructions located in "docs/transfer editor/transfer editor-pseudo-code.md". 
--- Upon clicking the "Create Schedule" button, a warning message will show with the following text: "WARNING, this will erase the current schedule in the transfer editor and regenerate a new schedule. Do you still want to continue?"
-- Once a schedule is created in the transfer editor, it will scan through all the data and cross reference everybody's schedule with each other. If there are time or location errors that conflict with each other, the areas of concern will be highlighted and and error message next to the highlight will appear, listing all affected locations of the conflict.
-- The transfer editor must render schedules as individual boxed per-person schedule blocks while preserving zone grouping/order from generated output.
-- Double-clicking a schedule block must open that person's record in the `Person Detail` tab for editing.
-- Schedule text blocks remain read-only in transfer editor; users edit data through dashboard/person detail and re-run `Create Schedule`.
-- The transfer editor must include a live search bar above the schedule viewer that updates character-by-character, auto-scrolls to the first match, supports Up/Down navigation through matches with wrap-around, and supports `Ctrl+F` focus when the Transfer Editor tab is active.
-- Search-result jumps and conflict-entry jumps must center the selected schedule anchor at a fixed viewport center spot with no cumulative drift across repeated navigation.
-- The transfer editor visual surface must follow the app dark theme with readable light text and consistent, modern solid scrollbars.
