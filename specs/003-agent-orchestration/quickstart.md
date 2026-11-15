# Quickstart: Feature 003 Agent Orchestration

This guide validates the Feature 003 design after implementation. The agent uses Feature 002's
MCP client and server; it does not instantiate Feature 001 retrieval directly.

## Prerequisites

- Python 3.11 and the repository dependencies are installed.
- Feature 001 and Feature 002 are available, with the F002 MCP server able to start over stdio.
- For a live request, configure a supported tool-calling LLM provider and its API key through
  environment variables. Routine tests use deterministic fakes and need no key.

## Environment

The planned agent configuration is environment-backed:

| Variable | Purpose |
|---|---|
| `AGENT_MODEL_PROVIDER` | LLM provider adapter. |
| `AGENT_MODEL_NAME` | Provider model supporting tool calling. Defaults to `GROQ_MODEL` if set, otherwise `openai/gpt-oss-20b`. |
| `AGENT_TEMPERATURE` | Generation temperature. |
| `AGENT_MAX_TOKENS` | Maximum generated response tokens. |
| `AGENT_TOP_K` | Policy-search result limit passed to F002. |
| `AGENT_MAX_TOOL_CALLS` | Maximum sequential tool calls per request. |
| `AGENT_MCP_SERVER_COMMAND` | Command used by the existing stdio MCP client. |
| `AGENT_MCP_SERVER_ARGS` | Arguments for the F002 server command. |
| `AGENT_TRACE_PATH` | Configured operational trace destination. |
| `GROQ_API_KEY` | Groq credential when Groq is selected; never committed or traced. |

Use the configured model/provider documented for the project. Verify provider availability and
free-tier limits before a live demonstration. Do not copy credentials into source or test
fixtures.

## Install and Verify

From the repository root in PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest
```

The routine suite must use deterministic LLM and MCP doubles. It must not require network access
to a model provider.

## Protocol Integration Validation

Run the Feature 003 MCP integration tests after implementation:

```powershell
python -m pytest tests/integration
```

The integration test connects to the existing Feature 002 stdio server through its MCP client,
checks the six discovered tools and declared schemas, then exercises representative allowed
tool calls through MCP. The Feature 003 agent uses `search_policy_documents` as its sole
policy-evidence path. SC-001's four-tool discovery threshold remains the acceptance minimum;
the integration check verifies all six current tools are discoverable.

## Request Validation Scenarios

1. **Policy question**: Submit a policy question. Verify the model selects
   `search_policy_documents`, the answer cites returned source IDs/sections/snippets, and no
   direct retrieval API or `get_policy_section` call occurs.
2. **Structured-data request**: Submit a request that needs an employee/PTO tool. Verify the
   tool is selected from the discovered catalog and the response is grounded in the MCP result.
3. **Multi-step request**: Submit a request requiring policy and structured data. Verify the
   calls occur sequentially, each result is returned to the next LLM turn, and conflicting
   evidence is reported without an invented resolution.
4. **Missing input or failure**: Omit a required identifier or simulate an unavailable tool.
   Verify the agent asks for clarification or surfaces the failure and does not invent a value.
5. **Email draft**: Request a draft. Verify a proposal is prepared with the existing F002 tool,
   an action-specific confirmation is requested, and the final simulated outcome states that
   no email was sent. Change the proposal and verify it requires new confirmation.
6. **Unsupported action**: Request email sending, approval, or an employee-record update.
   Verify the agent refuses and does not invoke an unsupported operation.

## Trace Inspection

For each completed test, inspect the structured trace for:

- Observable intent category, selected MCP tool names, concise outcome categories, and evidence
  source references.
- Concise selection/answer-basis summaries without hidden reasoning.
- No full request text, API keys, internal prompts, full records, or draft body.

See [data-model.md](data-model.md) for trace fields and
[contracts/python-interface.md](contracts/python-interface.md) for the async agent interface.
