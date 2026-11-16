# Data Model: Chat Interface

## Overview

F005 introduces no database, persistent entities, or changes to F003 public response types.
Browser display state lives only in the active Streamlit session. Agent input/output and
health values reuse existing F003/F002 contracts.

## Session Display State

| Value | Meaning | Lifetime and handling |
|---|---|---|
| `messages` | Ordered user messages and rendered assistant result data for the visible chat. | `st.session_state` only; not written to disk or sent as prior-turn agent context. |
| `employee_id` | Optional synthetic identifier supplied explicitly for an employee-specific F004 request. | Session-local UI input passed as `context.employee_id`; never inferred from message text. |
| `agent_runtime` | Session-owned asynchronous runtime containing the `HRAgent` and its MCP client session. | Kept isolated per browser session; used for current requests and proposal confirmation; no transcript memory. |
| `pending_action` | Caller-carried proposal data returned by F003 for an explicit confirmation flow. | Session-local and valid only with the same `HRAgent` instance; discarded when confirmed/cancelled or the session ends. |

Messages shown in the UI are not a transcript contract for F003. Each
`process_request` call receives only the current submitted message and optional explicit
context. No app state is copied into F003's LLM messages except that current request/context.

## Reused Agent Response

Source: `hr_agent.types.AgentResponse`.

| Field | UI treatment |
|---|---|
| `answer` | Display as the agent's returned answer; do not replace or augment with inferred facts. |
| `status` | Preserve `answered`, `partial`, `clarification_needed`, `confirmation_required`, `out_of_scope`, or `error` as distinct visible states. |
| `citations` | Show returned source type/ID, document ID, title, optional section, claim when present, and snippet. |
| `evidence_limitations` | Show when nonempty as an explicit limitation, not as a separate successful answer. |
| `tool_calls` | Show ordered tool name, outcome/status, allowlisted argument/output summaries, duration, and safe error code. |
| `operational_trace` | Project only approved observable event fields. Never render raw provider messages, internal prompts, or arbitrary unknown trace keys. |
| `clarification_prompt` | Display as a request for the missing information. |
| `confirmation_required`, `confirmation_prompt`, `action_id`, `pending_action` | Display the existing confirmation prompt and use the same session-owned agent for the user's explicit confirm/cancel action. Drafts remain unsent. |
| `error_code` | Display as a safe diagnostic identifier with a user-friendly failure message; never invent a fallback answer. |

The UI must tolerate missing optional citations or tool-call records and display only fields
actually returned. It does not serialize or persist a full `AgentResponse` outside the active
session.

## Health Result

The health view returns a JSON-serializable mapping with these fields:

```json
{
  "app": {"status": "healthy"},
  "mcp": {
    "status": "healthy",
    "tool_count": 6,
    "error_code": null
  }
}
```

| Field | Allowed values / meaning |
|---|---|
| `app.status` | `healthy` when the health view is executing. MCP failure does not falsely mark the app process unavailable. |
| `mcp.status` | `healthy` only after successful MCP initialization and discovery; `failed` when that check fails; `unchecked` when no probe was requested. |
| `mcp.tool_count` | Discovered tool count when healthy; otherwise `null`. |
| `mcp.error_code` | Safe `ClientError.code` when failed; otherwise `null`. Never include raw exception text or credentials. |

The MCP check runs `MCPClient.discover()` only. It does not call the model or any HR tool.
The Streamlit health view renders the result as JSON and is not a raw HTTP JSON endpoint.
