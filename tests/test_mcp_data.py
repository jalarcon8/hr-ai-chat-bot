import json
from pathlib import Path

import pytest

from hr_mcp.data import DataUnavailableError, SyntheticData

FIXTURES = Path(__file__).parent / "fixtures" / "mcp"
DATA = Path(__file__).parent.parent / "data"


@pytest.mark.parametrize(
    ("directory", "positive_id", "positive_hours", "missing_id", "zero_id"),
    [
        (DATA, "SYN-001", 80, "SYN-002", "SYN-003"),
        (FIXTURES, "TEST-001", 40, "TEST-002", "TEST-003"),
    ],
)
def test_balance_scenarios(directory, positive_id, positive_hours, missing_id, zero_id):
    data = SyntheticData(directory / "employees.json", directory / "pto.json")
    positive = data.check_pto_balance(positive_id)
    assert positive.status == "found"
    assert positive.pto.available_hours == positive_hours
    assert data.check_pto_balance(missing_id).missing == "pto"
    assert data.check_pto_balance("unknown").missing == "employee"

    result = data.check_pto_balance(zero_id)
    assert result.status == "found"
    assert result.pto.employee_id == zero_id
    assert result.pto.available_hours == 0


def test_employee_and_pto_results_and_valid_absences():
    data = SyntheticData(FIXTURES / "employees.json", FIXTURES / "pto.json")
    employee = data.lookup_employee_profile("TEST-001")
    pto = data.check_pto_balance("TEST-001")
    assert employee.status == "found"
    assert employee.employee.model_dump() == {
        "employee_id": "TEST-001",
        "name": "Taylor Fixture",
        "role": "Analyst",
        "department": "Operations",
        "work_arrangement": "hybrid",
        "work_state": "CA",
    }
    assert pto.status == "found"
    assert pto.pto.model_dump() == {
        "employee_id": "TEST-001",
        "available_hours": 40,
        "as_of": "2026-01-01",
    }
    assert data.lookup_employee_profile("test-001").missing == "employee"
    assert data.check_pto_balance("missing").missing == "employee"
    assert data.check_pto_balance("TEST-002").missing == "pto"


@pytest.mark.parametrize(
    ("employees", "pto"),
    [
        ("not json", "[]"),
        ("{}", "[]"),
        (
            ('[{"employee_id":"E","name":"N","role":"R","department":"D",'
            '"work_arrangement":"office","work_state":"CA"},'
            '{"employee_id":"E","name":"N","role":"R","department":"D",'
            '"work_arrangement":"office","work_state":"CA"}]'),
            "[]",
        ),
        (
            ('[{"employee_id":"E","name":"N","role":"R","department":"D",'
            '"work_arrangement":"invalid","work_state":"CA"}]'),
            "[]",
        ),
        (
            "[]",
            '[{"employee_id":"E","available_hours":1,"as_of":"2026-01-01"}]',
        ),
        (
            ('[{"employee_id":"E","name":"N","role":"R","department":"D",'
            '"work_arrangement":"office","work_state":"CA"}]'),
            '[{"employee_id":"E","available_hours":1,"as_of":"2026-02-30"}]',
        ),
        (
            ('[{"employee_id":"E","name":"N","role":"R","department":"D",'
            '"work_arrangement":"office","work_state":"CA"}]'),
            ('[{"employee_id":"E","available_hours":1,"as_of":"2026-01-01"},'
            '{"employee_id":"E","available_hours":2,"as_of":"2026-01-01"}]'),
        ),
    ],
)
def test_invalid_data_is_operational_error(tmp_path, employees, pto):
    employee_file = tmp_path / "employees.json"
    pto_file = tmp_path / "pto.json"
    employee_file.write_text(employees, encoding="utf-8")
    pto_file.write_text(pto, encoding="utf-8")
    with pytest.raises(DataUnavailableError):
        SyntheticData(employee_file, pto_file).check_pto_balance("E")


def test_missing_and_invalid_utf8_files_are_operational_errors(tmp_path):
    employee_file = tmp_path / "employees.json"
    pto_file = tmp_path / "pto.json"
    pto_file.write_text(json.dumps([]), encoding="utf-8")
    with pytest.raises(DataUnavailableError):
        SyntheticData(employee_file, pto_file).lookup_employee_profile("E")
    employee_file.write_bytes(b"\xff")
    with pytest.raises(DataUnavailableError):
        SyntheticData(employee_file, pto_file).lookup_employee_profile("E")
