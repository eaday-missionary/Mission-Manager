from mission_manager.constants import CANONICAL_HEADERS, PERSON_FIELDS


def test_dashboard_contract_counts() -> None:
    assert len(CANONICAL_HEADERS) == 19
    assert len(PERSON_FIELDS) == 19
