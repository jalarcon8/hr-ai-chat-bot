"""Validated, read-only fictional employee and PTO records."""

import json
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from hr_rag.models import OperationalError

from .models import (
    Employee,
    EmployeeFound,
    EmployeeInput,
    PTOFound,
    PTORecord,
    RecordNotFound,
)


class DataUnavailableError(OperationalError):
    """Synthetic data is unavailable or invalid."""


class SyntheticData:
    def __init__(self, employees_path: Path, pto_path: Path) -> None:
        self.employees_path = employees_path
        self.pto_path = pto_path

    def _load(self) -> tuple[dict[str, Employee], dict[str, PTORecord]]:
        try:
            employee_values = json.loads(self.employees_path.read_text(encoding="utf-8"))
            pto_values = json.loads(self.pto_path.read_text(encoding="utf-8"))
            employees = TypeAdapter(list[Employee]).validate_python(employee_values)
            pto_records = TypeAdapter(list[PTORecord]).validate_python(pto_values)
        except (OSError, UnicodeError, ValueError, ValidationError) as exc:
            raise DataUnavailableError("Synthetic data is unavailable or invalid.") from exc

        employee_by_id = {employee.employee_id: employee for employee in employees}
        pto_by_id = {record.employee_id: record for record in pto_records}
        if (
            len(employee_by_id) != len(employees)
            or len(pto_by_id) != len(pto_records)
            or not pto_by_id.keys() <= employee_by_id.keys()
        ):
            raise DataUnavailableError("Synthetic data has duplicate or dangling records.")
        return employee_by_id, pto_by_id

    def lookup_employee_profile(self, employee_id: str) -> EmployeeFound | RecordNotFound:
        employee_id = EmployeeInput(employee_id=employee_id).employee_id
        employees, _ = self._load()
        employee = employees.get(employee_id)
        if employee is None:
            return RecordNotFound(missing="employee")
        return EmployeeFound(employee=employee)

    def check_pto_balance(self, employee_id: str) -> PTOFound | RecordNotFound:
        employee_id = EmployeeInput(employee_id=employee_id).employee_id
        employees, pto_records = self._load()
        if employee_id not in employees:
            return RecordNotFound(missing="employee")
        record = pto_records.get(employee_id)
        if record is None:
            return RecordNotFound(missing="pto")
        return PTOFound(pto=record)
