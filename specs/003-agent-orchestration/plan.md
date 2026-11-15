# Implementation Plan: Agent Orchestration

**Branch**: `003-agent-orchestration` | **Date**: 2026-11-15 | **Spec**: [spec.md](spec.md)

## Summary

Implement a Python LLM agent that receives the Feature 002 MCP tool catalog, lets the LLM
interpret each request and select tools through native tool calling, then executes at most one
tool call per model turn in a bounded sequential loop. MCP calls use the existing asynchronous
Feature 002 client and protocol; policy evidence is obtained only through
`search_policy_documents`. The agent passes each tool result back to the LLM, which may request
another tool or produce the final grounded response. No heuristic router, workflow engine,
direct Feature 001 client, or additional business tool is introduced.

The loop has a configurable `max_tool_calls` bound. Each invocation is checked against the
discovered MCP schema and the Feature 003 safety boundary. The existing email-drafting tool may
prepare an unpersisted draft; the agent presents that proposal and requires action-specific
confirmation before reporting the simulated outcome. Confirmation context is carried by the
caller between requests; the agent adds no database, session store, or persistent action state.

## Technical Context

**Language/Version**: Python 3.11 (from `pyproject.toml`)  
**Primary Dependencies**: Existing `mcp` SDK/F002 `MCPClient`, existing `groq` SDK for LLM
tool calling, and the project’s existing Pydantic/data-model conventions. No orchestration
framework.  
**Storage**: None for agent state. Existing F001 index and F002 synthetic fixtures remain
owned by their features; traces use the project’s configured trace mechanism.  
**Testing**: pytest; deterministic LLM and MCP doubles for unit tests; protocol integration
tests against the existing F002 stdio server.  
**Target Platform**: Local Python application within the single-service project.  
**Project Type**: Python library/module consumed by later F004/F005 features.  
**Performance Goals**: No new latency target; bound model/tool iterations with
`max_tool_calls`.  
**Constraints**: Free-tier-compatible configurable model; environment-supplied credentials;
MCP protocol only; sequential tool execution; synthetic data; no real email sending or
unsupported mutations.  
**Scale/Scope**: One request at a time; the six existing F002 tools; representative generic
multi-step orchestration, not the dedicated F004 business workflows.

## Constitution Check

| Principle / constraint | Plan decision | Gate |
|---|---|---|
| I. Simplicity first | One bounded LLM tool-calling loop; no LangChain, LangGraph, workflow engine, or persistence layer. | Pass |
| II. Python first | Implement the agent and tests in Python 3.11. | Pass |
| III. Modular separation | Keep orchestration, MCP client, response synthesis, and trace generation behind separable interfaces. | Pass |
| IV. Grounded responses | Ground policy claims in MCP policy-search evidence and employee claims in MCP results; disclose missing or conflicting evidence. | Pass |
| V. MCP integration | Discover schemas and invoke tools through the existing MCP client/protocol; no in-memory tool calls. | Pass |
| VI. Synthetic data and safe operations | Keep F002 data synthetic; only propose the existing unsent email draft; require specific confirmation; refuse sending, approvals, and record updates. No persistent state mutation is added. | Pass |
| VII. Testing and reproducibility | Use deterministic test doubles and MCP integration tests; document environment configuration and validation. | Pass |
| Single-service / cost limits | Reuse existing dependencies and stdio transport; no service or paid infrastructure is required by the design. | Pass |

**Pre-design gate**: Pass. The approved specification and F002 dependency establish the
architecture; model and free-tier availability are runtime configuration checks, not unresolved
architectural choices.

## Architecture

1. **Agent interface**: An asynchronous Python `HRAgent` accepts a request and optional
   caller-provided context, returning a structured `AgentResponse`.
2. **Discovery**: Use the existing `MCPClient.discover()` over MCP during initialization and
   refresh the catalog before each request. Record the full discovered catalog; do not assume
   schemas that were not returned by the server. SC-001 remains a minimum of four discovered
   tools. Integration validation checks all six F002 tools.
3. **LLM orchestration**: Convert discovered, in-scope MCP tool definitions and schemas to the
   configured provider’s native tool-calling format. The model interprets intent and selects
   tools; no keyword classifier or hardcoded workflow sequence controls routing. The system
   instructions establish the feature boundary, grounding requirements, use of
   `search_policy_documents` as the sole policy-evidence path, and refusal of unsupported
   actions.
4. **Bounded sequential execution**: Request one tool call per LLM turn (`n=1` and
   `parallel_tool_calls=False` for the Groq adapter). Validate its name and arguments against
   the current discovery result, enforce the confirmation/safety boundary, invoke it via
   `MCPClient.call()`, and return its structured result to the LLM. Reject a provider response
   containing multiple calls rather than executing them concurrently. Repeat until the model
   returns a final response or the configured call limit is reached. Surface the limit and
   tool/transport failures explicitly; never convert a failed call into success.
5. **Grounded synthesis**: Give the model only the request, permitted context, and relevant
   tool results. Validate citation references against returned policy evidence; preserve
   conflicting evidence as a conflict rather than choosing an unsupported winner.
6. **Email-draft confirmation**: The existing `draft_hr_email` tool prepares a mock,
   unpersisted proposal. Return the proposal with a confirmation prompt and action identifier.
   On a later request, accept confirmation only for the same proposal; a new or materially
   changed draft requires new confirmation. Caller-carried context supports this exchange
   without agent-side persistence. The final message states that no email was sent. Refuse
   actual sending, approvals, employee-record updates, and other unsupported mutations.
7. **Operational trace**: Emit concise allowlisted summaries: intent category, selected tool
   names, brief observable selection/outcome categories, duration, evidence identifiers and
   sections, final-answer basis category, and clarification/escalation/failure outcome. Do not
   record chain-of-thought, internal prompts, full user text, credentials, full records, or
   email-body content.

The existing F002 `MCPClient` is asynchronous, exposes `discover()` and `call()`, and uses the
MCP SDK session methods for `tools/list` and `tools/call`. The Feature 003 interface therefore
uses async request and confirmation methods rather than wrapping protocol calls in a second
synchronous client.

## Design and Validation Stages

These are plan-level implementation boundaries, not implementation tasks:

1. **Agent foundation**: define configuration, structured responses, errors, MCP/LLM interfaces,
   and safe trace types; verify connection readiness and dynamic discovery.
2. **LLM/MCP loop**: translate discovered schemas, accept one model-selected call at a time,
   validate and invoke through MCP, feed results back, and enforce the iteration bound.
3. **Grounding and response behavior**: synthesize from tool evidence, validate citations,
   preserve conflicts, and return clarification, refusal, partial, and failure outcomes.
4. **Confirmation and traces**: implement the caller-carried email-draft proposal/confirmation
   exchange, per-action binding, unsupported-action refusal, and trace redaction.
5. **Verification and developer guide**: complete deterministic unit coverage, F002 protocol
   integration checks, and runnable quickstart validation scenarios.

## Requirements-to-Design Traceability

| Requirement | Design element | Verification evidence planned |
|---|---|---|
| QR-018 / FR-001, FR-003, FR-006, FR-008 | LLM interprets and selects discovered MCP tools; bounded result-feedback loop; grounded final synthesis. | Mocked model selects tools from schemas; at least two representative multi-step sequences complete through successive calls. |
| QR-019 | Dedicated PTO and remote-work workflows remain owned by F004; F003 supplies the general orchestration capability. | F003 verifies representative multi-step tool sequences, not F004-specific business logic. |
| QR-020 / FR-009, FR-010 | Allowlisted observable decision and outcome trace with evidence references; no hidden reasoning or sensitive raw data. | Inspect traces for selected tools, outcome categories, sources, redaction, and absence of prompts/reasoning. |
| QR-021 / FR-004, FR-005 | Schema validation, missing-input clarification, explicit tool/transport failures, partial response where evidence permits. | Deterministic tests for missing IDs, invalid arguments, unavailable tools, timeouts, and incomplete evidence. |
| QR-022 / FR-011, FR-012 | Existing mock email-drafting proposal with action-specific confirmation; refuse unsupported operations and avoid persistent changes. | Confirm/cancel, changed-proposal reconfirmation, unsent labeling, and refusal tests. |
| QR-026 / FR-014, FR-015 | F002 client discovery/call over actual MCP protocol; no direct Feature 001 or in-memory server calls. | Integration test against the F002 stdio server and protocol call evidence. |
| QR-015, QR-016 (supporting F003) / FR-006, FR-007 | Policy citations and explicit unsupported/out-of-corpus handling. | Citation/source validation and unsupported/conflicting-evidence tests. |
| QR-027 (F002-owned; F003 support) | Document the agent’s actual MCP client integration and protocol usage. | Contract and quickstart describe discovery, schema handling, and invocation; F002 remains owner of server/tool documentation. |

**Coverage result**: All requirements assigned to F003 (QR-018, QR-020–QR-022, QR-026)
have a design and verification path. QR-019’s full named business workflows are assigned to
F004; the F003 specification’s general multi-step behavior is covered without taking ownership
of those workflows. No assigned requirement is identified as unsupported by this design.

## Testing Strategy

- **Unit tests**: deterministic LLM tool-call sequences; refreshed discovery/schema conversion;
  one-call
  sequencing and loop bound; valid/invalid schemas and arguments; missing-context clarification;
  tool and model errors; citations and conflicting evidence; refusal behavior; action-specific
  email confirmation; trace allowlist/redaction.
- **Protocol integration tests**: start the existing F002 server over stdio, initialize the
  actual MCP client, verify discovery of all six existing tools and their declared schemas, and
  exercise permitted policy-search and structured-data calls through MCP. The Feature 003 agent
  does not call Feature 001 directly or use `get_policy_section` as a second policy-evidence
  path.
- **Acceptance validation**: cover SC-001 through SC-010, retaining the SC-001 minimum of four
  discovered tools while separately asserting the six-tool integration baseline.
- **External calls**: routine tests use deterministic doubles for both LLM and MCP; no API
  credentials, external model calls, or real HR data are required.

## Project Structure

```text
src/hr_agent/
  agent.py       # asynchronous orchestration loop and public HRAgent
  config.py      # environment-backed model, token, MCP, and loop settings
  types.py       # request/response, citation, tool-call, and trace data
  errors.py      # explicit initialization and runtime failures
  llm.py         # minimal provider adapter for native tool calling

tests/
  unit/          # deterministic orchestration, safety, and trace tests
  integration/   # F002 MCP stdio protocol integration

specs/003-agent-orchestration/
  plan.md
  research.md
  data-model.md
  quickstart.md
  contracts/python-interface.md
```

**Structure decision**: Add a focused `src/hr_agent/` package and corresponding tests to the
existing Python project. Keep the provider adapter small and use existing Groq/MCP dependencies;
do not create a separate service or workflow package.

## Configuration and Dependencies

Use the existing pinned dependencies in `pyproject.toml`/`requirements.txt`. Configure the LLM
provider/model, temperature, maximum output tokens, policy-search top-k, `max_tool_calls`, MCP
server command/transport, and trace settings through environment-backed `AgentConfig`.
Credentials remain environment-only. Validate during implementation that the selected configured
model supports native tool calling and that its current free-tier limits are usable. The model
name is not hardcoded as an architectural dependency.

## Post-design Constitution Check

Pass. The design has no constitution exception, no new state-changing operation, no direct
retrieval bypass, no separate deployment, and no new orchestration dependency. It preserves
traceable MCP use and deterministic tests. F004 business workflows remain outside this plan.

## Blocking Decisions and Risks

**Blocking architectural decisions**: None. The approved specification and user decisions
resolve the orchestration, sequential execution, evidence-conflict, confirmation, and trace
choices.

**Implementation-time validation**: Confirm the configured Groq-compatible model and free-tier
limits support tool calling; provide a clear explicit error if the configured provider/model is
unavailable. This does not block the architecture because the provider is configurable and unit
tests use a deterministic fake.
