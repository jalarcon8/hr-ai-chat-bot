# Specification Summary: Agent Orchestration (Feature 003)

## Document Overview

This specification defines Feature 003 (Agent Orchestration) of the HR AI Chatbot project. 
It provides the functional and behavioral requirements for an LLM-based agent that interprets 
user requests, orchestrates tool use, and generates grounded, cited responses.

**Specification Status:** Draft - Ready for Implementation
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
2. **Route** to Feature 001 (RAG retrieval), Feature 002 (MCP tools), or both.
3. **Orchestrate** multi-step tool invocations with proper sequencing and error handling.
4. **Synthesize** grounded responses with citations and clear evidence limitations.
5. **Trace** all decisions and operations for auditing and debugging.
6. **Safeguard** state-changing operations with explicit user confirmation.

---

## Scope: In and Out

### In Scope ✓

- Intent interpretation (heuristic-based; not LLM classification).
- Dynamic tool discovery via MCP protocol.
- Single-tool (retrieval only or MCP only) and multi-tool orchestration.
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
- LLM-based tool selection (deterministic routing instead).
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

- **LLM Service:** Groq, OpenRouter, or local model (free-tier required).
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
| SC-001 | Agent can be initialized with F001 and F002 clients and discover MCP tools. |
| SC-002 | Policy-only requests use retrieval and do NOT make unnecessary MCP calls. |
| SC-003 | Data-lookup requests invoke MCP tools correctly without excessive retrieval. |
| SC-004 | Multi-step requests invoke both retrieval and MCP in correct sequence. |
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
[Agent Core]
    ├─→ Intent Interpreter
    │   └─→ Determine tools needed
    ├─→ Tool Selector
    │   └─→ Map intent → tools
    ├─→ Tool Invoker
    │   ├─→ Retrieval Client (F001)
    │   └─→ MCP Client (F002)
    ├─→ Evidence Validator
    │   └─→ Verify citations, evidence
    ├─→ Response Synthesizer
    │   └─→ Generate answer + limitations
    └─→ Trace Generator
        └─→ Log decisions (redacted)
            ↓
        AgentResponse
        ├─→ answer
        ├─→ citations
        ├─→ evidence_limitations
        ├─→ tool_calls
        └─→ operational_trace
```

---

## Configuration

### Environment Variables

```bash
AGENT_MODEL_NAME=grok-3                    # LLM model
AGENT_RETRIEVAL_K=5                        # Top-k policy chunks
AGENT_MAX_TOOL_CALLS=10                    # Max MCP invocations
AGENT_TEMPERATURE=0.7                      # LLM sampling
AGENT_TRACE_SINK=logs/traces.jsonl         # Trace destination
GROQ_API_KEY=<key>                         # Groq credentials
```

### Runtime Options

```python
response = agent.process_request(
    user_input="...",
    context={"prior_results": ...},
    options={
        "retrieval_k": 3,
        "max_tool_calls": 5,
        "confirmation_required": True
    }
)
```

---

## Interface Overview

### Main Class: HRAgent

```python
class HRAgent:
    def __init__(retrieval_client, mcp_client, config): ...
    def process_request(user_input, context, options) -> AgentResponse: ...
    def confirm_action(action_id, confirmation, context) -> AgentResponse: ...
```

### Response Structure

```python
@dataclass
class AgentResponse:
    answer: str
    status: Literal["answered", "partial", "clarification_needed", "error", ...]
    citations: List[Citation]
    evidence_limitations: str
    tool_calls: List[ToolInvocationRecord]
    operational_trace: OperationalTrace
    clarification_prompt: Optional[str]
    confirmation_required: bool
    confirmation_prompt: Optional[str]
```

See [contracts/python-interface.md](contracts/python-interface.md) for full signatures and 
types.

---

## Testing Strategy

### Test Coverage

| Category | Scenarios | Status |
|---|---|---|
| Intent classification | Policy, data, multi-step, ambiguous, out-of-scope | Design phase |
| Retrieval-only requests | 3+ acceptance cases | Design phase |
| MCP-only requests | 3+ acceptance cases | Design phase |
| Multi-tool workflows | 3+ acceptance cases | Design phase |
| Error handling | Tool failures, missing info, conflicts | Design phase |
| Evidence validation | Citation grounding, fabrication detection | Design phase |
| State-changing ops | Confirmation, mock labeling | Design phase |
| Trace redaction | Secrets excluded, allowlisted fields present | Design phase |

### Tools and Fixtures

- Mocked RAGClient with representative evidence.
- Mocked MCPClient with synthetic tool results.
- Mocked LLMClient for deterministic synthesis.
- Pytest fixtures for common test data.

### Running Tests

```bash
pytest tests/test_agent_*.py -v
pytest tests/test_agent_acceptance.py::test_policy_lookup -v
pytest tests/ --cov=src/hr_agent --cov-report=term
```

---

## Known Ambiguities and Clarifications Needed

| Issue | Status | Impact |
|---|---|---|
| Conflicting retrieval and tool results | Pending | Response synthesis, evidence limitations |
| Out-of-scope request boundaries | Pending | Safety, user experience |
| Partial workflow cancellation | Pending | Multi-step UX |
| Citation accuracy standards | Pending | Response quality validation |
| Tool retry strategy | Pending | Resilience and latency |
| Dynamic tool discovery | Pending | Flexibility after init |

See [research.md](research.md) for details and current assumptions.

---

## Integration with Other Features

### Feature 001 (RAG)

- Agent calls `retrieval_client.answer()` for policy evidence.
- Retrieval results are used directly; not re-processed.
- Evidence limitations from retrieval flow into agent response.

### Feature 002 (MCP Tools)

- Agent discovers tools via MCP protocol at initialization.
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
| QR-018 | Intent interpretation, tool orchestration, synthesis | Specification defined |
| QR-020 | Operational traces with tool decisions | Specification defined |
| QR-021 | Error and ambiguity handling | Specification defined |
| QR-022 | Mock operations with confirmation | Specification defined |
| QR-026 | MCP protocol invocation | Specification defined |

---

## Next Steps

1. **Review and Approve:** Specification review by project owner and stakeholders.
2. **Resolve Ambiguities:** Clarify outstanding design questions (see research.md).
3. **Plan Detailed Tasks:** Break implementation plan into specific GitHub issues.
4. **Dependency Validation:** Confirm F001 and F002 are stable and ready for integration.
5. **Begin Phase 1 Implementation:** Foundation (agent structure, MCP integration).

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

**Specification Readiness:** DRAFT - Ready for Implementation Review

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
