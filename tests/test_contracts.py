from mission_manager.constants import CANONICAL_HEADERS, PERSON_FIELDS
from mission_manager.services import DashboardService


def test_dashboard_contract_counts() -> None:
    assert len(CANONICAL_HEADERS) == 20
    assert len(PERSON_FIELDS) == 20
    assert CANONICAL_HEADERS[-1] == "Title"
    assert PERSON_FIELDS[-1] == "title"


def test_transfer_service_contract_methods_exist() -> None:
    required = [
        "create_person",
        "create_schedule",
        "get_schedule_document",
        "list_schedule_conflicts",
    ]
    for method_name in required:
        assert hasattr(DashboardService, method_name)
