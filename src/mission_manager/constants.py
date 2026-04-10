"""Shared constants for dashboard implementation."""

from __future__ import annotations

APP_NAME = "Mission Manager"
SCHEMA_VERSION = 4

CANONICAL_HEADERS = [
    "First Name",
    "Last Name",
    "Current Companion",
    "New Companion",
    "Current Zone",
    "Current Area",
    "New Zone",
    "New Area",
    "Staying or leaving?",
    "Pre Travel",
    "Departure Terminal",
    "Departure Time",
    "Arrival Terminal",
    "Arrival Time",
    "Second Leg?",
    "2nd Departure Terminal",
    "2nd Departure Time",
    "2nd Arrival Terminal",
    "2nd Arrival Time",
    "Title",
]

# Alias map allows known workbook variants to resolve to canonical headers.
# Keys and values are expected to be normalized (trimmed) exact strings.
HEADER_ALIASES = {
    "Transfer to Zone": "New Zone",
    "Transfer to Area": "New Area",
    "Staying?": "Staying or leaving?",
    "Departing Terminal": "Departure Terminal",
    "Arriving Terminal": "Arrival Terminal",
    "Departing Terminal 2": "2nd Departure Terminal",
    "Departure Time 2": "2nd Departure Time",
    "Arrival Time 2": "2nd Arrival Time",
    "Arriving Terminal 2": "2nd Arrival Terminal",
}

UNSUPPORTED_HEADER_WARNINGS = {
    "Third Leg?": "Unsupported column ignored: Third Leg? (third-leg travel is not supported).",
}

HEADER_TO_FIELD = {
    "First Name": "first_name",
    "Last Name": "last_name",
    "Current Companion": "current_companion",
    "New Companion": "new_companion",
    "Current Zone": "current_zone",
    "Current Area": "current_area",
    "New Zone": "new_zone",
    "New Area": "new_area",
    "Staying or leaving?": "staying",
    "Pre Travel": "pre_travel",
    "Departure Terminal": "departure_terminal",
    "Departure Time": "departure_time",
    "Arrival Terminal": "arrival_terminal",
    "Arrival Time": "arrival_time",
    "Second Leg?": "second_leg",
    "2nd Departure Terminal": "second_departure_terminal",
    "2nd Departure Time": "second_departure_time",
    "2nd Arrival Terminal": "second_arrival_terminal",
    "2nd Arrival Time": "second_arrival_time",
    "Title": "title",
}

FIELD_TO_HEADER = {v: k for k, v in HEADER_TO_FIELD.items()}
PERSON_FIELDS = list(FIELD_TO_HEADER.keys())
DEFAULT_SORT_FIELD = "current_zone"
DEFAULT_SORT_DIR = "asc"

SORT_OPTIONS = {
    "Current Zone (A-Z)": ("current_zone", "asc"),
    "Current Area (A-Z)": ("current_area", "asc"),
    "New Zone (A-Z)": ("new_zone", "asc"),
    "New Area (A-Z)": ("new_area", "asc"),
    "First Name (A-Z)": ("first_name", "asc"),
    "Last Name (A-Z)": ("last_name", "asc"),
    "Departure Time (Earliest-Latest)": ("departure_time", "asc"),
    "Arrival Time (Earliest-Latest)": ("arrival_time", "asc"),
    "Second Leg? (No-Yes)": ("second_leg", "asc"),
    "2nd Departure Time (Earliest-Latest)": ("second_departure_time", "asc"),
    "2nd Arrival Time (Earliest-Latest)": ("second_arrival_time", "asc"),
}

FILTER_FIELDS = ["current_area", "new_zone", "new_area", "second_leg"]
BOOLEAN_TRUE = {"yes", "y", "true", "1"}
BOOLEAN_FALSE = {"no", "n", "false", "0"}
