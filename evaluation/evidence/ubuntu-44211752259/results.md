# F006 Bounded Evaluation Results

- Run: `20261118T010154Z-3d480837`
- Code revision: `3ad5090efe202df84c3df1e520f492874d059508+dirty`
- Groq model: `openai/gpt-oss-20b`
- Cases: 20 planned; 3 attempted; 2 successful completions; 1 provider failures; 0 operational failures; 17 not run.
- Stop reason: EVAL-003 ended as provider_failure (llm_request_failed) after 2148.87 ms.
- Categories: ambiguous=4, multi_document=4, out_of_scope=4, policy=4, tool_requiring=4.
- Workflow status match: 2/2 scored.
- Tool-selection match: 2/2 cases with tool constraints.
- Latency: 2/10 selected cases completed; p50=1567.44 ms, p95=5431.65 ms (nearest rank; agent request duration).
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

## Attempted cases

| Case | Outcome | Status | Tools | Sources | Workflow match | Failure | Duration |
|---|---|---|---|---|---:|---|---:|
| EVAL-001 | completed | answered | search_policy_documents | HR-001, HR-002, HR-006 | True | — | 5431.65 ms |
| EVAL-002 | completed | answered | search_policy_documents | HR-002, HR-003 | True | — | 1567.44 ms |
| EVAL-003 | provider_failure | — | — | — | unscored | llm_request_failed | 2148.87 ms |
