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
    assert normalize_time("13:45:59") == "13:45"
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
        "First Name", "Last Name", "Title", "Current Area", "Current Zone", "New Zone", "New Area",
        "Current Companion", "New Companion", "Staying or leaving?", "Pre Travel",
        "Departure Terminal", "Departure Time", "Arrival Terminal", "Arrival Time", "Second Leg?",
        "2nd Departure Terminal", "2nd Departure Time", "2nd Arrival Terminal", "2nd Arrival Time", "Ticket Status"
    ]
    rows = [
        ["John", "Doe", "E", "A1", "Zone1", "NZ", "NA", "", "", "yes", "", "T1", "08:00", "A", "09:00", "no", "", "", "", "", "Issued"],
        ["John", "Doe", "S", "A1", "Zone2", "NZ", "NA", "", "", "no", "", "T2", "10:00", "B", "11:00", "yes", "", "", "", "", "Issued"],
    ]
    parsed = parse_records_from_rows(headers, rows, "file.xlsx")
    assert not parsed.errors
    assert len(parsed.records) == 1
    assert parsed.records[0]["current_zone"] == "Zone2"
    assert parsed.records[0]["title"] == "S"
    assert any("Ignoring unknown columns" in w for w in parsed.warnings)


def test_sample_header_aliases_are_accepted() -> None:
    headers = [
        "First Name",
        "Last Name",
        "Title",
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
        "E",
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
    assert parsed.records[0]["title"] == "E"
    assert parsed.records[0]["new_zone"] == "Zone B"
    assert parsed.records[0]["departure_terminal"] == "ICN"


def test_schema_validation_missing_title_header_fails() -> None:
    headers = [
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
    ]
    parsed = parse_records_from_rows(headers, [["Jane", "Smith"]], "file.xlsx")
    assert parsed.errors
    assert parsed.errors[0].code == "SCHEMA_ERROR"
    assert "Title" in (parsed.errors[0].suggested_action or "")


def test_departure_time_fields_allow_raw_text() -> None:
    headers = [
        "First Name",
        "Last Name",
        "Title",
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
    ]
    rows = [[
        "Jane",
        "Smith",
        "S",
        "",
        "",
        "Zone A",
        "Area A",
        "Zone B",
        "Area B",
        "no",
        "",
        "Suji Subway",
        "yellow",
        "Seoul Subway",
        "09:00",
        "yes",
        "Daejeon Subway",
        "blue",
        "Busan Subway",
        "13:00",
    ]]
    parsed = parse_records_from_rows(headers, rows, "file.xlsx")
    assert not parsed.errors
    assert parsed.records[0]["departure_time"] == "yellow"
    assert parsed.records[0]["second_departure_time"] == "blue"


def test_departure_time_fields_normalize_parseable_times() -> None:
    headers = [
        "First Name",
        "Last Name",
        "Title",
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
    ]
    rows = [[
        "Jane",
        "Smith",
        "S",
        "",
        "",
        "Zone A",
        "Area A",
        "Zone B",
        "Area B",
        "no",
        "",
        "Busan",
        "08:30:00",
        "Seoul",
        "09:00:00",
        "yes",
        "Daejeon",
        "13:15:59",
        "Busan",
        "15:00:01",
    ]]
    parsed = parse_records_from_rows(headers, rows, "file.xlsx")
    assert not parsed.errors
    assert parsed.records[0]["departure_time"] == "08:30"
    assert parsed.records[0]["arrival_time"] == "09:00"
    assert parsed.records[0]["second_departure_time"] == "13:15"
    assert parsed.records[0]["second_arrival_time"] == "15:00"


def test_invalid_arrival_time_still_fails_validation() -> None:
    headers = [
        "First Name",
        "Last Name",
        "Title",
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
    ]
    rows = [[
        "Jane",
        "Smith",
        "E",
        "",
        "",
        "Zone A",
        "Area A",
        "Zone B",
        "Area B",
        "no",
        "",
        "Suji Subway",
        "yellow",
        "Seoul Subway",
        "not-a-time",
        "no",
        "",
        "",
        "",
        "",
    ]]
    parsed = parse_records_from_rows(headers, rows, "file.xlsx")
    assert parsed.errors
    assert parsed.errors[0].code == "ROW_VALIDATION_ERROR"
    assert parsed.errors[0].field == "arrival_time"


def test_unsupported_third_leg_column_is_explicitly_flagged() -> None:
    headers = [
        "First Name",
        "Last Name",
        "Title",
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
        "Third Leg?",
    ]
    rows = [[
        "Jane",
        "Smith",
        "E",
        "",
        "",
        "Zone A",
        "Area A",
        "Zone B",
        "Area B",
        "yes",
        "",
        "ICN",
        "08:00",
        "GMP",
        "09:00",
        "no",
        "",
        "",
        "",
        "",
        "yes",
    ]]

    parsed = parse_records_from_rows(headers, rows, "sample.xlsm")
    assert not parsed.errors
    assert any("Unsupported column ignored: Third Leg?" in warning for warning in parsed.warnings)
