import socket
from pathlib import Path

import pytest
from pydantic import ValidationError

from hr_mcp.tools import draft_hr_email


def test_draft_is_deterministic_and_does_not_use_network(monkeypatch, tmp_path):
    fixtures = Path(__file__).parent / "fixtures" / "mcp"
    records = [fixtures / "employees.json", fixtures / "pto.json"]
    before = [path.read_bytes() for path in records]

    def forbid_network(*args, **kwargs):
        pytest.fail("drafting must not use the network")

    monkeypatch.setattr(socket, "socket", forbid_network)
    monkeypatch.chdir(tmp_path)
    first = draft_hr_email("Alex Example", "PTO request", "May 10")
    second = draft_hr_email("Alex Example", "PTO request", "May 10")
    assert first == second
    assert first.status == "found"
    assert "PTO request" in first.draft.subject
    assert "Alex Example" in first.draft.body
    assert "May 10" in first.draft.body
    assert list(tmp_path.iterdir()) == []
    assert [path.read_bytes() for path in records] == before


@pytest.mark.parametrize(
    ("recipient", "purpose", "details"),
    [("", "PTO", ""), ("Alex", " ", ""), ("Alex", "PTO", None)],
)
def test_draft_rejects_invalid_input(recipient, purpose, details):
    with pytest.raises(ValidationError):
        draft_hr_email(recipient, purpose, details)


def test_draft_allows_omitted_details():
    result = draft_hr_email("Alex", "PTO")
    assert result.status == "found"
    assert "Alex" in result.draft.body
