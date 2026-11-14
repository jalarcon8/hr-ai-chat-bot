# Quickstart and Validation: MCP Tool Integration

This is the planned validation guide; the commands below depend on F002 being implemented.
Do not treat them as currently runnable or as evidence of completion.

## Prerequisites

- Python 3.11 and a clean virtual environment.
- An F001 index built from the fictional `corpus/`, with the same embedding model configured
  for search. The initial local model download may require network access; no provider key is
  needed for F002's deterministic drafting or routine tests.
- F002's small synthetic employee and PTO JSON data files and the documented example records.
- `mcp==1.28.1` added to the project dependencies during implementation.

From the project root on Windows, after implementation:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\python -m ruff check .
.\.venv\Scripts\python -m pytest -q
```

On Linux, use `python3.11 -m venv .venv` and `.venv/bin/python` for the corresponding
commands. Follow the [F001 setup](../001-HR_Policy_RAG/quickstart.md) to build the index;
do not use real employee information.

## Protocol smoke test

The planned client launches the server over stdio. It exposes a `--discover` command and a
`--example TOOL_NAME` command using documented synthetic examples:

```powershell
.\.venv\Scripts\python -m hr_mcp.client --discover
.\.venv\Scripts\python -m hr_mcp.client --example search_policy_documents
.\.venv\Scripts\python -m hr_mcp.client --example get_policy_section
.\.venv\Scripts\python -m hr_mcp.client --example lookup_employee_profile
.\.venv\Scripts\python -m hr_mcp.client --example check_pto_balance
.\.venv\Scripts\python -m hr_mcp.client --example check_policy_compliance
.\.venv\Scripts\python -m hr_mcp.client --example draft_hr_email
```

Discovery must expose exactly the six agreed names, descriptions, and schemas. Each example
must traverse MCP, return the outcome in [mcp-tools.md](contracts/mcp-tools.md), and produce an
inspectable redacted trace. Configure the trace sink per the implementation README; protocol
stdout must not contain trace messages. The compliance example requires the reviewed HR-004
section in the active snapshot; a different or incomplete section gives `indeterminate`.

## Acceptance checks

1. Exercise every tool via an actual stdio client/server subprocess using deterministic
   embedders and synthetic fixture data; no live model or provider credentials are needed.
2. Verify search candidates, including unrelated results, are not presented as supported
   answers; verify exact section lookup, missing section, citations and generation ID.
3. Verify known and unknown employees, an employee missing PTO, and malformed/unavailable
   data. Missing records are distinct from broken dependencies.
4. Verify approved, not approved, unknown and absent approval; absent, changed, and incomplete
   policy evidence; corrupt index; unsupported check; and no broad eligibility assertion.
5. Verify invalid types, blank input, nonpositive and boolean `k`, unknown arguments, unknown
   tools, and interrupted server connections. Inspect traces for each result/error and confirm
   secrets, raw questions, full employee records, and draft text are absent.
6. Confirm draft generation is deterministic and does not send, persist, mutate, or call
   external services. Repeat the suite on Windows and Linux and record actual results.
