from mission_manager.constants import CANONICAL_HEADERS, PERSON_FIELDS
from mission_manager.services import DashboardService


def test_dashboard_contract_counts() -> None:
    assert len(CANONICAL_HEADERS) == 19
    assert len(PERSON_FIELDS) == 19


def test_transfer_service_contract_methods_exist() -> None:
    required = [
        "create_schedule",
        "fix_schedule",
        "get_schedule_document",
        "list_schedule_conflicts",
    ]
    for method_name in required:
        assert hasattr(DashboardService, method_name)
