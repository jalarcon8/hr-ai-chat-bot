# Quickstart: Feature 003 Agent Orchestration

Feature 003 uses LLM-native tool selection over the live Feature 002 MCP catalog. It executes
one selected tool at a time in a bounded loop. Policy evidence is retrieved only through
`search_policy_documents`; the agent never calls Feature 001 directly or uses
`get_policy_section` as an alternate evidence path.

## Prerequisites

- Python 3.11 and the repository dependencies are installed.
- Feature 002's MCP server is available over stdio; its policy-search handler uses the existing
  Feature 001 retrieval implementation.
- For live requests, configure Groq tool calling and `GROQ_API_KEY`. Routine tests use
  deterministic LLM/MCP doubles and need no provider credentials.

## Initialize and process a request

`HRAgent.create` performs initial MCP discovery. The catalog is refreshed through MCP before
each request. Pass the configured MCP server arguments as a list to `MCPClient`:

```python
import asyncio

from hr_agent.agent import HRAgent
from hr_agent.config import AgentConfig
from hr_agent.llm import GroqLLMClient
from hr_mcp.client import MCPClient


async def main():
    config = AgentConfig.from_environment()
    async with MCPClient(
        command=config.mcp_server_command,
        args=list(config.mcp_server_args),
    ) as mcp_client:
        agent = await HRAgent.create(mcp_client, GroqLLMClient(), config)
        response = await agent.process_request(
            "What approval is required before out-of-state work travel?"
        )
        print(response.answer)
        for citation in response.citations:
            print(citation.document_id, citation.section, citation.snippet)


asyncio.run(main())
```

The model selects from discovered, supported tools. Calls execute sequentially, with each
structured result returned to the next model turn, until a final response or the configured
`max_tool_calls` limit. Supported tools are policy search, employee profile, PTO balance,
compliance check, and email draft. The agent does not offer `get_policy_section` for policy
evidence.

## Environment

`AgentConfig.from_environment()` reads process environment values first, then a local `.env`
file. Defaults are shown where applicable:

| Variable | Purpose |
|---|---|
| `AGENT_MODEL_PROVIDER` | Provider name; the current adapter supports `groq` (default). |
| `AGENT_MODEL_NAME` | Tool-calling model; defaults to `GROQ_MODEL` when set, otherwise `openai/gpt-oss-20b`. |
| `AGENT_TEMPERATURE` | Generation temperature (default `0`). |
| `AGENT_MAX_TOKENS` | Maximum generated response tokens (default `1024`). |
| `AGENT_TOP_K` | Policy-search result limit passed to Feature 002 (default `5`). |
| `AGENT_MAX_TOOL_CALLS` | Sequential MCP-call bound per request (default `3`). |
| `AGENT_MCP_SERVER_COMMAND` | MCP server process command (default: current Python executable). |
| `AGENT_MCP_SERVER_ARGS` | JSON array of arguments (default `["-m", "hr_mcp.server"]`). |
| `AGENT_TRACE_PATH` | Optional path for the agent's privacy-allowlisted JSONL trace. |
| `GROQ_API_KEY` | Groq credential; read from the environment and never included in traces. |

`AgentConfig.mcp_server_args` is a `tuple[str, ...]`; convert it to a list when constructing
the existing `MCPClient`, as shown above. Agent trace output is controlled by `trace_path`;
the MCP client retains its own trace-sink configuration.

Do not copy credentials into source or test fixtures. Verify current provider availability and
free-tier limits before a live demonstration.

## Install and Verify

From the repository root in PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
```

The live-provider smoke test is opt-in and skipped by default. Routine tests use deterministic
LLM/MCP doubles and do not require network access to a model provider.

## Protocol Integration Validation

Run the Feature 003 MCP protocol integration scenario:

```powershell
python -m pytest -q tests/integration/test_agent_mcp.py
```

The test connects through the existing Feature 002 stdio server and `MCPClient`, checks all six
discovered tools and schemas, and verifies successful `HRAgent` invocation of
`search_policy_documents`, `lookup_employee_profile`, `check_pto_balance`,
`check_policy_compliance`, and `draft_hr_email`. The draft is only prepared and confirmed;
no email is sent. Policy claims are evidenced through `search_policy_documents`.

The deterministic Feature 003 acceptance cases can be run separately:

```powershell
python -m pytest -q tests/test_agent_acceptance.py
```

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
5. **Email draft**: `process_request` returns `confirmation_required`, `action_id`, and
   `pending_action`. The caller carries `pending_action` to `confirm_action`; confirmation is
   bound to that exact proposal. Use the same live `HRAgent` instance for confirmation. A changed
   proposal requires a new request and confirmation. A confirmed result states that no email
   was sent.
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
