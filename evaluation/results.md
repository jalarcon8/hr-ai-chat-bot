# F006 Bounded Evaluation Results

- Run: `20261116T064050Z-b78c2489`
- Code revision: `c833b2d59ad05221e44395b0e8d437c2dafc056d+dirty`
- Groq model: `openai/gpt-oss-20b`
- Cases: 20 planned; 1 attempted; 0 successful completions; 0 provider failures; 1 operational failure; 19 not run.
- Stop reason: EVAL-001 ended as operational_failure (mcp_tool_call_failed) after 302201.67 ms.
- Categories: ambiguous=4, multi_document=4, out_of_scope=4, policy=4, tool_requiring=4.
- Workflow status match: 0/0 scored.
- Tool-selection match: 1/1 cases with tool constraints.
- Latency: 0/10 selected cases completed; p50/p95 unavailable (failed attempts are excluded).
- Correctness, groundedness, citation accuracy, escalation quality, and action safety require answer-level rubric review; their per-case fields remain null until scored.

## Retrieval comparison

- Applicable cases: 15; expected source labels: 24.
- k=3 source recall: 16/24 (66.7%).
- k=5 source recall: 17/24 (70.8%).
- Retrieval is measured independently from Groq answers against the checked-in expected-source labels; it makes no provider calls.

## Review and limitations

- Provider and operational errors are stored separately in `results.jsonl`; no case is retried and completed rows are appended immediately.
- Answer-level correctness and safety scores are intentionally not inferred from keyword matching. Review each retained synthetic answer against its case rubric.
- Latency measures `AgentSession.process_request`, including Groq and MCP work but not browser rendering. `first_request` and `warm` refer to this evaluation session.
- No raw provider payloads, tool arguments, credentials, or hidden reasoning are stored.

## Bounded MCP timeout investigation

- The Streamlit application and evaluation runner use the same `AgentSession`, `AgentConfig` defaults, MCP stdio client, Python executable, and `-m hr_mcp.server` command. The evaluation runner obtains its config from the same environment; its separate k-comparison model load is not required by the app.
- From the repository root, the provider-free diagnostic successfully initialized the MCP session and discovered all six tools. Its single `search_policy_documents` call then timed out at 60 seconds with protocol code 408. The client trace has no corresponding server tool-completion event, so the failure is after discovery, during MCP tool execution/response; it does not establish whether the handler or transport is stuck.
- The active FAISS pointer and referenced files exist. The MCP child receives the same nonsecret RAG settings and filtered inherited environment as the client contract; the default HuggingFace cache, including the MiniLM model, is present.
- A no-MCP child-process check using that environment loaded `SentenceTransformerEmbedder` in 8.02 seconds and completed direct FAISS retrieval in 0.08 seconds with five results. Thus the index, cache, and direct embedding/retrieval path work, but the MCP server dispatch/response path remains unverified.
- The MCP stdio implementation explicitly flushes JSON-RPC responses, and startup/discovery responses arrived; generic stdout buffering is not supported by the evidence as the cause. The underlying server/SDK failure remains unresolved. The diagnostic made no Groq request, did not modify evaluation outputs, and did not repeat the live suite.
- Following review, the existing `ci.yml` gained an Ubuntu-only, manually triggered evaluation job gated on the `main` branch, explicit opt-in, and passing tests. Its first completed diagnostic run is recorded separately below; the original local result is unchanged.

## Ubuntu diagnostic investigation (2026-11-17)

- [Actions run #21](https://github.com/jalarcon8/hr-ai-chat-bot/actions/runs/44031373821) checked out `f7b505862480df4779c7696cfee047a05cf221a8`; both revision files agree. Both normal CI matrix jobs passed. The full evaluation step was skipped, and artifact `14305003240` was uploaded.
- The downloaded original ZIP's SHA256 was verified as `db8abd33bc6443963a0980bd0ff0b2713cf0b490e06c776d417bda5d73df8e9f`. Its `diagnostic.jsonl` records `EVAL-001`, `provider_failure`, `llm_request_failed`, model `openai/gpt-oss-20b`, and 5910.86 ms. This is a separate diagnostic, not another completed suite or latency sample.
- The MCP server trace records successful `search_policy_documents` execution at `06:33:48.543663Z`, with source IDs `HR-001`, `HR-002`, and `HR-006`. Thus Groq had already selected a tool, MCP/RAG completed, and the provider failed on a subsequent request. Empty tool lists in the diagnostic failure row reflect the existing exception-only row format, not a missing tool invocation.
- The workflow passes the Actions secret into the evaluation Python process as `GROQ_API_KEY`; the adapter reads it there, not in the MCP subprocess. Reaching tool selection demonstrates an earlier Groq request succeeded. There is no evidence of an absent credential; the key value was neither inspected nor exposed.
- The failure's HTTP status/category cannot be recovered from these artifacts: `AGENT_TRACE_PATH` was unset, so the existing safe agent trace was not persisted; non-400 SDK errors also discarded their category. Authentication, quota, rate limiting, model availability, request-format, and network explanations are not established.
- The targeted correction retains safe HTTP/error categories for all SDK API failures and enables the existing agent trace in both workflow steps. Arbitrary provider messages, request bodies, headers, and credentials remain excluded. It changes no Groq request parameters, provider, or MCP behavior and does not claim to fix the unknown provider rejection.
- The workflow now defaults `diagnostic_only` to true. Pending review, the single next diagnostic action is one manual Ubuntu diagnostic-only run, with `run_live_evaluation=true` and `diagnostic_only=true`, then inspection of `agent-traces.jsonl`. No new live request or workflow was triggered during this investigation. Milestone 3 remains incomplete.

## Attempted cases

| Case | Outcome | Status | Tools | Sources | Workflow match | Failure | Duration |
|---|---|---|---|---|---:|---|---:|
| EVAL-001 | operational_failure | error | search_policy_documents | — | unscored | mcp_tool_call_failed | 302201.67 ms |
