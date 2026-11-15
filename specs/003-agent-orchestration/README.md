# Specification Summary: Agent Orchestration (Feature 003)

## Document Overview

This specification defines Feature 003 (Agent Orchestration) of the HR AI Chatbot project. 
It provides the functional and behavioral requirements for an LLM-based agent that interprets 
user requests, orchestrates tool use, and generates grounded, cited responses.

**Implementation Status:** Milestones 1-3 and Phase 4A are complete; Phase 4B is in progress.
**Created:** 2026-11-15
**Branch:** `003-agent-orchestration`

---

## Key Specification Documents

| Document | Purpose | Key Content |
|---|---|---|
| [spec.md](spec.md) | Functional specification | Requirements, user stories, acceptance criteria, assumptions |
| [data-model.md](data-model.md) | Data structures | Request/response shapes, intent, tool calls, traces, configuration |
| [contracts/python-interface.md](contracts/python-interface.md) | API contract | Class signatures, method arguments, return types, errors |
| [plan.md](plan.md) | Implementation plan | Phases, tasks, acceptance criteria, risks, testing strategy |
| [quickstart.md](quickstart.md) | Usage guide | Setup, examples, configuration, troubleshooting |
| [research.md](research.md) | Design decisions | Resolved ambiguities, validation needs, open questions |

---

## Core Objective

Enable an LLM-based agent to:
1. **Interpret** natural-language user requests and determine required capabilities.
2. **Select** discovered Feature 002 MCP tools through LLM-native tool calling.
3. **Orchestrate** bounded, sequential tool calls, returning each result to the next model turn.
4. **Retrieve policy evidence** only through Feature 002's `search_policy_documents` tool.
5. **Synthesize** grounded responses with citations and clear evidence limitations.
6. **Trace** observable decisions and operations using allowlisted, privacy-safe summaries.
7. **Safeguard** email-draft proposals with caller-carried, action-specific confirmation.

---

## Scope: In and Out

### In Scope ✓

- LLM interpretation and native tool selection from the dynamically discovered MCP catalog.
- Sequential multi-tool orchestration with a configurable `max_tool_calls` bound.
- Policy-only, structured-data, and combined requests through supported MCP tools.
- Policy evidence retrieved only through `search_policy_documents`.
- Citation grounding and evidence validation.
- Graceful error handling and clarification requests.
- Operational tracing with proper redaction.
- Mock state-changing operations with confirmation.
- Configuration management via environment variables.
- Python interface with structured request/response types.

### Out of Scope ✗

- Real HR system integration (all operations are mock).
- Web interface (Feature 005).
- Dedicated workflow implementations (Feature 004).
- Direct Feature 001 retrieval calls and `get_policy_section` as another policy-evidence path.
- Hardcoded request routing or a separate workflow/orchestration framework.
- Multi-turn conversation history persistence.
- Authentication or authorization.
- Production-grade performance optimization (Feature 006).

---

## Requirements Summary

### Functional Requirements (FR)

| Requirement | Feature | Category | Priority |
|---|---|---|---|
| FR-001 | Intent-driven tool routing | Core | P1 |
| FR-002 | Dynamic MCP tool discovery | Integration | P1 |
| FR-003 | Multi-tool orchestration | Core | P1 |
| FR-004 | Input validation and argument mapping | Core | P1 |
| FR-005 | Tool failure handling and recovery | Resilience | P1 |
| FR-006 | Grounding in evidence and tool results | Core | P1 |
| FR-007 | Evidence limitation identification | Core | P1 |
| FR-008 | Support for multi-step workflows | Core | P2 |
| FR-009 | Operational trace generation | Auditability | P2 |
| FR-010 | Trace redaction and privacy | Auditability | P2 |
| FR-011 | State-changing operation confirmation | Safety | P1 |
| FR-012 | Out-of-scope request rejection | Safety | P1 |
| FR-013 | Python interface | Interface | P1 |
| FR-014 | Explicit MCP initialization | Integration | P1 |
| FR-015 | MCP protocol invocation (not direct calls) | Integration | P1 |
| FR-016 | Environment-based configuration | Operations | P2 |
| FR-017 | Modular, testable design | Architecture | P1 |

### Non-Functional Requirements (from Constitution)

- **Python-First:** Implementation is Python; no additional languages required.
- **Modular:** Separated from retrieval, MCP, and response generation.
- **Testable:** Unit and integration tests without real external services.
- **Reproducible:** Configuration via environment; no hardcoded secrets.
- **Safe:** Mock operations, explicit confirmations, no real side effects.

---

## Dependencies

### Upstream Features (Must Complete First)

- **Feature 001 (RAG):** Policy indexing, retrieval, and citation.
- **Feature 002 (MCP Tools):** FastMCP server with six tools.

### External Dependencies

- **LLM Service:** Groq through the current provider adapter.
- **MCP Protocol:** FastMCP or compatible SDK.
- **Python Libraries:** MCP client, dataclasses, JSON serialization.

### Not Required

- Separate database or persistence layer.
- Additional deployed services.
- Production model inference infrastructure.

---

## Success Criteria

### Specification-Level (SC)

| Criterion | Description |
|---|---|
| SC-001 | Agent initializes with the Feature 002 client and discovers its MCP tools. |
| SC-002 | Policy-only requests use `search_policy_documents` without unrelated tool calls. |
| SC-003 | Data-lookup requests invoke MCP tools correctly without excessive retrieval. |
| SC-004 | Multi-step requests invoke policy search and structured tools sequentially. |
| SC-005 | Ambiguous or missing-info requests trigger clarification, not guessing. |
| SC-006 | Unsupported or absent evidence is identified; no fabricated claims. |
| SC-007 | Tool failures are surfaced clearly with partial response or alternative. |
| SC-008 | Traces include tool names, outcomes, argument summaries, and evidence; exclude secrets. |
| SC-009 | State-changing operations require confirmation and are labeled as mock. |
| SC-010 | All acceptance test scenarios pass; coverage includes intent, tools, synthesis, errors. |

---

## Architecture Overview

```
User Request
    ↓
HRAgent ⇄ LLM (native tool selection; one tool per turn; bounded sequential loop)
    ↓
MCPClient ⇄ Feature 002 MCP Server
              ├─ search_policy_documents → Feature 001 policy retrieval
              ├─ synthetic employee/PTO/compliance tools
              └─ draft_hr_email (proposal + confirmation; no email is sent)
    ↓
Grounded response, citations, evidence limitations, and allowlisted trace
```

---

## Configuration

### Environment Variables

```bash
AGENT_MODEL_PROVIDER=groq
AGENT_MODEL_NAME=openai/gpt-oss-20b
AGENT_TEMPERATURE=0
AGENT_MAX_TOKENS=1024
AGENT_TOP_K=5
AGENT_MAX_TOOL_CALLS=3
AGENT_MCP_SERVER_COMMAND=python
AGENT_MCP_SERVER_ARGS='["-m","hr_mcp.server"]'
AGENT_TRACE_PATH=logs/agent-traces.jsonl
```

Set `GROQ_API_KEY` through the process environment or a local, untracked `.env` file.

### Runtime Options

```python
response = await agent.process_request(
    user_input="What policy applies to this request?",
    context=None,
    options={
        "top_k": 3,
        "max_tool_calls": 5,
    }
)
```

`AGENT_MCP_SERVER_ARGS` is a JSON string array and becomes the `tuple[str, ...]`
`AgentConfig.mcp_server_args`. Convert it to `list[str]` when passing it to `MCPClient`.
`AgentConfig.trace_path` configures the agent JSONL trace; Feature 002's MCP trace sink remains
separately configured.

---

## Interface Overview

### Main Class: HRAgent

```python
class HRAgent:
    @classmethod
    async def create(cls, mcp_client, llm_client, config=None) -> HRAgent: ...
    async def process_request(user_input, context=None, options=None) -> AgentResponse: ...
    async def confirm_action(action_id, confirmation, context) -> AgentResponse: ...
```

### Response Structure

```python
from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class AgentResponse:
    answer: str
    status: Literal[
        "answered", "partial", "clarification_needed", "confirmation_required",
        "out_of_scope", "error",
    ]
    citations: list[Citation] = field(default_factory=list)
    evidence_limitations: str = ""
    tool_calls: list[ToolInvocationRecord] = field(default_factory=list)
    operational_trace: OperationalTrace = field(default_factory=OperationalTrace)
    clarification_prompt: str | None = None
    confirmation_required: bool = False
    confirmation_prompt: str | None = None
    action_id: str | None = None
    pending_action: dict[str, Any] | None = None
    error_code: str | None = None
```

See [contracts/python-interface.md](contracts/python-interface.md) for full signatures and 
types.

---

## Testing Strategy

### Test Coverage

| Category | Scenarios | Status |
|---|---|---|
| LLM-selected policy and data tools | 3 policy-only and 3 structured-data acceptance cases | Verified locally |
| Sequential tool use | 3 deterministic policy-plus-data sequences and protocol integration | Verified locally |
| Clarification, evidence, and errors | Missing IDs, absent/conflicting evidence, failures/timeouts | Verified locally |
| State-changing safety | Caller-carried draft confirmation and unsupported-action refusal | Verified locally |
| Operational trace privacy | Allowlisted fields and private-value exclusion | Verified locally |

### Tools and Fixtures

- Mock MCP policy-search results with representative evidence.
- Mocked MCPClient with synthetic tool results.
- Mocked LLMClient for deterministic synthesis.
- Pytest fixtures for common test data.

### Running Tests

```bash
python -m pytest -q tests/test_agent_acceptance.py
python -m pytest -q tests/integration/test_agent_mcp.py
python -m ruff check .
```

---

## Orchestration and Safety Decisions

- The LLM selects tools from the live MCP discovery result; the agent validates schemas and
  performs one call at a time until a final response or the configured bound.
- Policy claims use candidate excerpts from `search_policy_documents`; missing or conflicting
  evidence is disclosed rather than resolved by guesswork.
- Failed calls are not automatically retried within a request. A new request may try again.
- The only confirmable action is the existing unsent `draft_hr_email` proposal. Confirmation is
  bound to that proposal and carried by the caller; sending, approvals, and record updates are
  refused.

See [plan.md](plan.md) and [research.md](research.md) for implementation decisions and scope.

---

## Integration with Other Features

### Feature 001 (RAG)

- F003 does not call Feature 001 directly.
- Policy evidence is retrieved through Feature 002's `search_policy_documents` MCP tool only.
- Citations and evidence limitations are returned in the structured agent response.

### Feature 002 (MCP Tools)

- Agent discovers tools at initialization and refreshes the catalog for each request.
- Tool invocation is exclusively through MCP (no direct calls).
- Tool errors and results are handled per Feature 002 contracts.
- Synthetic data sources are used as-is.

### Feature 004 (HR Workflows)

- F004 builds on F003's orchestration foundation.
- F004 adds workflow-specific logic (PTO steps, remote-work checks).
- F003 provides the autonomous tool invocation and response synthesis.
- F004 does NOT require changes to F003 core.

### Feature 005 (Chat Interface)

- F005 calls agent via Python interface.
- F005 displays agent responses, citations, and traces.
- F005 handles user confirmations and clarification prompts.
- F005 does NOT require changes to F003 core.

---

## Specification Compliance Matrix

| Quantic Req | F003 Coverage | Status |
|---|---|---|
| QR-018 | LLM-native tool selection, bounded orchestration, grounded synthesis; acceptance and protocol tests | Verified |
| QR-020 | Allowlisted operational traces and privacy tests | Verified |
| QR-021 | Discovery, clarification, evidence-limit, failure, and timeout tests | Verified |
| QR-022 | Draft confirmation and unsupported-action safety tests | Verified |
| QR-026 | Five distinct successful `HRAgent` invocations through the real stdio MCP client | Verified |

---

## Next Steps

1. Obtain and review GitHub Actions results for the current Feature 003 revision on Ubuntu and Windows.
2. Keep Feature 004-specific business workflows outside Feature 003.

---

## Document Status

| Phase | Status | Completeness |
|---|---|---|
| User Stories | ✓ Complete | 4 stories, 16 acceptance scenarios |
| Functional Requirements | ✓ Complete | 17 functional requirements |
| Data Model | ✓ Complete | Request, response, trace, config |
| Interface Contract | ✓ Complete | Class signatures, types, errors |
| Implementation Plan | ✓ Complete | 6 phases, acceptance criteria |
| Design Decisions | ✓ Complete | Resolved ambiguities, validation points |

**Implementation Status:** Milestones 1-3 and Phase 4A are complete; Phase 4B local
verification is in progress. Hosted CI for this branch remains to be verified.

---

## Appendix: Related Documents

- [Quantic Project Requirements](../../docs/requirements/quantic-project-requirements.pdf)
- [Feature Roadmap](../../docs/feature-roadmap.md)
- [Requirements Traceability](../../docs/requirements/traceability.md)
- [Project Constitution](../../.specify/memory/constitution.md)
- [Feature 001 Specification](../001-HR_Policy_RAG/spec.md)
- [Feature 002 Specification](../002-mcp-tool-integration/spec.md)

---

**Document Version:** 1.0
**Last Updated:** 2026-11-15
**Author:** Copilot
**Branch:** 003-agent-orchestration
