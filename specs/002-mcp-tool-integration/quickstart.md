# Quickstart and Validation: MCP Tool Integration

This is the planned validation guide; the commands below depend on F002 being implemented.
Do not treat them as currently runnable or as evidence of completion.

## Prerequisites

- Python 3.11 and a clean virtual environment.
- An F001 index built from the fictional `corpus/`, with the same embedding model configured
  for search. The initial local model download may require network access; no provider key is
  needed for F002's deterministic drafting or routine tests.
- F002's small synthetic employee and PTO JSON data files, documented example records, and
  the planned explicitly reviewed document-level baseline for HR-004 and HR-001. Full-document
  review and activation are pending; the old section-only baseline is not sufficient.
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
inspectable persisted redacted trace when the configured sink is operational. Configure the
trace sink per the implementation README; protocol stdout must not contain trace messages. A
trace persistence failure is an operational error, not a successful tool result, and need not
itself have a persisted trace. The compliance example requires the reviewed HR-004 section in
the active snapshot, both complete governing source documents bound to that snapshot, and a
valid approved document-level baseline matching the active pin. Missing or changed governing
documents, insufficient indexed citations, or a missing, invalid, unreviewed, or mismatched
baseline give `indeterminate`. Governing policy changes require a new version and explicit
review before the active pin is updated; see [research.md](research.md).

## Acceptance checks

The QR-027 documentation check (T032) follows this setup and protocol smoke test against the
implemented client and server: compare all six discovered names, descriptions and input schemas
with the tool contract, inspect the architecture and transport description against the code, and
invoke the documented synthetic `lookup_employee_profile` example over MCP. Record the platform,
commands and results or unavailable prerequisites; do not treat an unrun check as passed.

1. Exercise every tool via an actual stdio client/server subprocess using deterministic
   embedders and synthetic fixture data; no live model or provider credentials are needed.
2. Verify search candidates, including unrelated results, are not presented as supported
   answers; verify exact section lookup, missing section, citations and generation ID.
3. Verify known and unknown employees, an employee missing PTO, and malformed/unavailable
   data. Missing records are distinct from broken dependencies.
4. Through MCP, verify timely written People Operations approval, known absence, late and
   equal-time approval, verbal approval, wrong authority, missing and unknown facts, timezone
   offsets and invalid timestamps. For unknown status with each disqualifying candidate fact,
   verify `noncompliant` when the caller asserts no other approval and `indeterminate` when a
   separate qualifying approval remains possible. Verify limitations disclose that caller
   assertions are unauthenticated and the result is not an overall eligibility decision.
   Verify unchanged and changed governing
   documents, including a new subsection with an unchanged original chunk; an unrelated document
   change; missing or unverifiable sources and indexed citations; missing, malformed, unreviewed,
   and mismatched baselines; newline and Unicode normalization; corrupt index; unsupported check;
   and no broad eligibility assertion.
5. Verify invalid types, blank input, nonpositive and boolean `k`, unknown arguments, unknown
   tools, and interrupted server connections. Through standard and raw MCP clients, verify
   structured classifications for invalid arguments, dependency failures, and unexpected
   exceptions without parsing error text. Verify ambiguous errors are reported by the provided
   client as `UNCLASSIFIED_ERROR` with no asserted origin, regardless of message text or missing
   trace information. With an operational sink, inspect persisted traces for each invocation
   reaching the server adapter and confirm secrets, raw questions, full
   employee records, and draft text are absent. Verify malformed protocol requests rejected by
   the SDK before dispatch do not reach the adapter or require a server execution trace; the
   provided client separately traces protocol failures it observes. Simulate trace persistence
   failure and verify an explicit operational error and no successful tool result without
   requiring a trace of the failed write.
6. Confirm draft generation is deterministic and does not send, persist, mutate, or call
   external services. Repeat the suite on Windows and Linux and record actual results.
