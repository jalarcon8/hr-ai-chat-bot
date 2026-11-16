# F005 Local Validation Quickstart

## Prerequisites

- Python 3.11 and the project's development dependencies installed.
- Run commands from the repository root.
- A local F001 policy index is required for live policy retrieval; follow the README's
  existing index setup. The Streamlit app must not build or download the index at startup.
- Routine UI tests use deterministic responses and do not require provider credentials.
- A live browser-to-agent request requires the configured provider credentials and an
  available local MCP server. Do not use real employee data.

## Run the application

Start Streamlit from the repository root:

```powershell
.\.venv\Scripts\python -m streamlit run src\hr_app\app.py
```

Use the browser chat or select either the PTO request or remote-work sample prompt. For
employee-specific requests, provide a synthetic employee ID in the dedicated field; an ID in
the message alone is not authoritative. The UI displays prior messages only for the active
browser session and does not send them as agent memory. Draft confirmation and cancellation
use the same session-owned agent and never send email.

## Inspect health

Use **Check MCP health** in the sidebar to inspect the JSON-compatible app/MCP status. A
healthy MCP result means the existing client connected and discovered the tool catalog; a
failed result includes only a safe error code. The probe calls `MCPClient.discover()` only; it
does not call the model or invoke an HR tool. Before probing, MCP is reported as `unchecked`.

The health view is a Streamlit equivalent for QR-031, not a separately exposed raw HTTP
`/health` endpoint.

## Deterministic tests

The focused deterministic F005 UI checks are:

```powershell
.\.venv\Scripts\python -m pytest tests\test_chat_interface.py -q
.\.venv\Scripts\python -m ruff check src\hr_app tests\test_chat_interface.py
```

Both commands passed on 2026-11-15 (`12 passed`; Ruff reported all checks passed). Tests use
controlled responses and fake MCP clients. They verify the real F003 request path, explicit
employee context, display-only history, citation/snippet display, ordered allowlisted
tool/trace output, both sample prompts, blank-input rejection, agent/dependency/timeout
errors, MCP `healthy`/`failed`/`unchecked` JSON, and draft confirmation/cancellation on the
same agent runtime. The health tests verify discovery only, with no model or HR-tool call.

The full local verification also passed:

```powershell
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m ruff check .
```

Result: **488 passed, 5 skipped, 0 failed**; Ruff reported **All checks passed**. This full
suite includes existing F001-F004 tests. The five skips are reported as pytest skips; live
provider behavior remains separately unverified.

The local server returned HTTP 200 during the Milestone 2 checkpoint. Its live browser
question reached the provider but returned the safe `llm_request_failed` error; a successful
live-provider response remains unverified and was not retried in later milestones.

The active `.github/workflows/ci.yml` workflow has no hosted run for the current
`005-chat-interface` branch. Hosted CI is unverified and remains with F006. No deployment,
project-wide evaluation, or live-provider run is part of F005 verification.
