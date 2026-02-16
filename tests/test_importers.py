import pytest

from mission_manager.importers import normalize_boolean, normalize_time, parse_records_from_rows


def test_normalize_boolean_variants() -> None:
    assert normalize_boolean("yes")[0] is True
    assert normalize_boolean("Y")[0] is True
    assert normalize_boolean("no")[0] is False
    assert normalize_boolean("0")[0] is False
    assert normalize_boolean("")[0] is None
    assert normalize_boolean("maybe")[0] is None


def test_normalize_time_variants() -> None:
    assert normalize_time("13:45") == "13:45"
    assert normalize_time("1345") == "13:45"
    assert normalize_time(0.5) == "12:00"
    assert normalize_time("bad") is None


def test_schema_validation_missing_header() -> None:
    headers = ["First Name", "Last Name"]
    rows = [["A", "B"]]
    parsed = parse_records_from_rows(headers, rows, "file.xlsx")
    assert parsed.errors
    assert parsed.errors[0].code == "SCHEMA_ERROR"


def test_extra_columns_allowed_and_duplicates_last_row_wins() -> None:
    headers = [
        "First Name", "Last Name", "Current Area", "Current Zone", "New Zone", "New Area",
        "Current Companion", "New Companion", "Staying or leaving?", "Pre Travel",
        "Departure Terminal", "Departure Time", "Arrival Terminal", "Arrival Time", "Second Leg?",
        "2nd Departure Terminal", "2nd Departure Time", "2nd Arrival Terminal", "2nd Arrival Time", "Ticket Status"
    ]
    rows = [
        ["John", "Doe", "A1", "Zone1", "NZ", "NA", "", "", "yes", "", "T1", "08:00", "A", "09:00", "no", "", "", "", "", "Issued"],
        ["John", "Doe", "A1", "Zone2", "NZ", "NA", "", "", "no", "", "T2", "10:00", "B", "11:00", "yes", "", "", "", "", "Issued"],
    ]
    parsed = parse_records_from_rows(headers, rows, "file.xlsx")
    assert not parsed.errors
    assert len(parsed.records) == 1
    assert parsed.records[0]["current_zone"] == "Zone2"
    assert any("Ignoring unknown columns" in w for w in parsed.warnings)


def test_sample_header_aliases_are_accepted() -> None:
    headers = [
        "First Name",
        "Last Name",
        "Current Companion",
        "New Companion",
        "Current Zone",
        "Current Area",
        "Transfer to Zone",
        "Transfer to Area",
        "Staying?",
        "Pre Travel",
        "Departing Terminal",
        "Departure Time",
        "Arrival Time",
        "Arriving Terminal",
        "Second Leg?",
        "Departing Terminal 2",
        "Departure Time 2",
        "Arrival Time 2",
        "Arriving Terminal 2",
    ]
    rows = [[
        "Jane",
        "Smith",
        "",
        "",
        "Zone A",
        "Area A",
        "Zone B",
        "Area B",
        "y",
        "",
        "ICN",
        "08:00",
        "09:00",
        "GMP",
        "no",
        "",
        "",
        "",
        "",
    ]]

    parsed = parse_records_from_rows(headers, rows, "sample.xlsm")
    assert not parsed.errors
    assert len(parsed.records) == 1
    assert parsed.records[0]["new_zone"] == "Zone B"
    assert parsed.records[0]["departure_terminal"] == "ICN"
