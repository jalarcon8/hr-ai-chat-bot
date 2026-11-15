"""Test-only server using isolated deterministic handlers."""

from typing import Any

from hr_mcp.server import TOOL_NAMES, Handler, create_server

MOCK_RESULTS: dict[str, dict[str, Any]] = {
    "search_policy_documents": {
        "status": "not_found",
        "evidence": [],
        "generation_id": "search_policy_documents",
    },
    "get_policy_section": {
        "status": "not_found",
        "evidence": [],
        "generation_id": "get_policy_section",
    },
    "lookup_employee_profile": {
        "status": "found",
        "employee": {
            "employee_id": "lookup_employee_profile",
            "name": "Fictional",
            "role": "Tester",
            "department": "Testing",
            "work_arrangement": "remote",
            "work_state": "CA",
        },
    },
    "check_pto_balance": {
        "status": "found",
        "pto": {"employee_id": "check_pto_balance", "available_hours": 1.0, "as_of": "2026-01-01"},
    },
    "check_policy_compliance": {
        "status": "indeterminate",
        "check_id": "out_of_state_prior_approval",
        "conclusion": "indeterminate",
        "evidence": [],
        "limitations": ["check_policy_compliance"],
    },
    "draft_hr_email": {
        "status": "found",
        "draft": {"subject": "draft_hr_email", "body": "Fictional draft"},
    },
}


def make_handler(name: str) -> Handler:
    def handler(arguments: dict[str, Any]) -> dict[str, Any]:
        return MOCK_RESULTS[name]

    return handler


if __name__ == "__main__":
    create_server({name: make_handler(name) for name in TOOL_NAMES}).run(transport="stdio")
