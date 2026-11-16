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
- Following review, the existing `ci.yml` now has an Ubuntu-only, manually triggered evaluation job gated on the `main` branch, explicit opt-in, and passing tests. It writes diagnostic and suite outputs under the runner temp directory and uploads them even on failure, leaving this local partial result untouched. The workflow has not been triggered; no Linux or Groq evaluation result has been collected.

## Attempted cases

| Case | Outcome | Status | Tools | Sources | Workflow match | Failure | Duration |
|---|---|---|---|---|---:|---|---:|
| EVAL-001 | operational_failure | error | search_policy_documents | — | unscored | mcp_tool_call_failed | 302201.67 ms |
