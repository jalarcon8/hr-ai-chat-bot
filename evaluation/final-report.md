# F006 Final Evaluation Report

## Decision and scope

Milestone 4 checkpoint, 2026-11-18 UTC. The owner paused further live evaluation and
EVAL-003 debugging. No Groq requests, live workflow dispatches, or retrieval reruns were
made for this checkpoint. The academic MVP is deployed by user report, but the required
evaluation and two deployed workflow demonstrations are **not fully verified**.

Model: `openai/gpt-oss-20b`; existing Groq adapter, prompts, MCP tools and runner unchanged.
There are [20 fixed cases](cases.json), four in each of five categories: policy,
multi-document, tool-requiring, ambiguous, and out-of-scope. Ten cases are designated for
latency measurement. Temperature zero and fixed cases do not guarantee deterministic
provider behavior.

## Preserved runs

Diagnostics are separate from suite cases; do not pool repeated EVAL-001/EVAL-003 attempts
or count them as extra evaluation coverage.

| Record | Result | Duration | Evidence |
|---|---|---:|---|
| Original Windows suite, EVAL-001 | MCP search timed out; operational failure; 19 not run | 302201.67 ms | Unchanged [original row](results.jsonl) and [historical report](results.md) |
| Ubuntu run 44031373821, EVAL-001 diagnostic | MCP policy search succeeded; subsequent Groq request failed, cause unknown | 5910.86 ms | [Result](evidence/ubuntu-44031373821/diagnostic.jsonl), [MCP trace](evidence/ubuntu-44031373821/mcp-traces.jsonl) |
| Ubuntu run 44211752259, EVAL-001 diagnostic | Required policy search and final cited response completed; diagnostic passed; answer ungraded | 8742.00 ms | [Diagnostic](evidence/ubuntu-44211752259/diagnostic.jsonl) |
| Same run, suite EVAL-001 | Completed; policy-search tool succeeded; answer ungraded | 5431.65 ms | [Suite rows](evidence/ubuntu-44211752259/results.jsonl) |
| Same run, suite EVAL-002 | Completed; policy-search tool succeeded; answer ungraded | 1567.44 ms | Same suite rows |
| Same run, suite EVAL-003 | Groq rejected initial tool-call generation: HTTP 400, `bad_request`, `tool_use_failed`; no MCP call | 2148.87 ms | [Safe agent trace](evidence/ubuntu-44211752259/agent-traces.jsonl) |
| Isolated Windows EVAL-003 | Groq generated a policy-search call; MCP execution timed out; no sources returned | 302588.55 ms | [Diagnostic](evidence/windows-eval003/diagnostic.jsonl), [trace](evidence/windows-eval003/agent-traces.jsonl) |
| Ubuntu run 44220869982, isolated EVAL-003 | Accepted clarification completion, requesting employee ID; no tool call; diagnostic failed | 1787.45 ms | [Diagnostic](evidence/ubuntu-44220869982/diagnostic.jsonl), [trace](evidence/ubuntu-44220869982/agent-traces.jsonl) |

The bounded Ubuntu suite attempted **3/20**: **2 completed, 1 provider failure,
0 operational failures, 17 unattempted**. Its process exited 1 deliberately after the
failure. The successful preflight diagnostic is not a third completed suite case.

Run links: [44031373821](https://github.com/jalarcon8/hr-ai-chat-bot/actions/runs/44031373821),
[44211752259](https://github.com/jalarcon8/hr-ai-chat-bot/actions/runs/44211752259),
[44220869982](https://github.com/jalarcon8/hr-ai-chat-bot/actions/runs/44220869982).
The [evidence manifest](evidence/manifest.json) records checksums of byte-preserved artifact
copies. Original ZIPs remain separately preserved by the project owner. Archived revision
files identify the checked-out SHA; original JSONL `+dirty` suffixes are intentionally
retained, not rewritten as clean-run claims.

## Quality and behavior: measured versus ungraded

| Measure | Available result | Qualification |
|---|---|---|
| Correctness, groundedness, citation accuracy | **Unscored** | Both completed suite answers retain null answer-level grades; no accuracy percentage claimed |
| Suite tool-constraint match | 2/2 scored rows (100%); 1 attempted failure unscored | Checks required/forbidden tool names, not semantic suitability across all 20 cases |
| Suite expected-status match | 2/2 scored rows (100%); 1 attempted failure unscored | Runner field `workflow_completion` is a response-status proxy, not proof of correct end-to-end HR guidance |
| Suite operational completion | 2/3 attempted; 17 unattempted | Not an answer-correctness or full-suite pass rate |
| Escalation/clarification accuracy | **Unscored** | No ambiguous/out-of-scope suite case was reached |
| Action-safety pass rate | **Unscored** | Deterministic guardrail tests pass, but no live answer-level safety percentage was graded |
| Isolated hosted EVAL-003 | Tool and workflow checks both false | `outcome=completed` means a response was returned; `clarification_needed` does not meet its policy-answer rubric |

EVAL-001 cites HR-001/HR-002/HR-006; EVAL-002 cites HR-002/HR-003. Citation presence and
successful retrieval do not prove that every answer claim is supported. EVAL-002's expected
source labels include HR-001, which was absent; this requires review, not an automatic pass.
Use the case rubrics to review claims against the actual policy sections, sources, expected
behavior and safety constraints before replacing any null grades. Do not silently drop
failed or unattempted cases from coverage reporting.

## Retrieval comparison and latency

The unchanged [retrieval comparison](retrieval_comparison.json) covers 15 applicable
queries with 24 expected-source labels:

- k=3: 16/24 source-label matches, **66.7% recall**.
- k=5: 17/24, **70.8% recall**.
- Difference: one additional matched label, **4.2 percentage points**. This measures
  retrieval coverage only, not answer quality or precision, and does not justify a broader
  model/prompt change.

Only **2/10** designated suite latency samples completed: 5431.65 ms (`first_request`)
and 1567.44 ms (`warm`). **Required 10-20-sample p50/p95 are unavailable.** Failed durations
and separate diagnostics are reported above but excluded from that sample. Do not pool
different runs or the unrelated provider-free model-load/retrieval timings to fill it.
`first_request` is a session label, not a measured Community Cloud cold start.

## Failure categories and unresolved limits

- **Groq:** observed HTTP 400 `bad_request` / allowlisted `tool_use_failed` on EVAL-003.
  Exact rejected tool payload was not retained. No evidence establishes authentication,
  quota, rate limiting, or unavailable model as its cause. Run 44031373821 predates the
  safe provider trace and has no recoverable HTTP category.
- **Local Windows MCP:** initialization and discovery work; production-index policy search
  timed out. A separate provider-free child loaded MiniLM in 8.02 s and retrieved in 0.08 s.
  The handler/transport execution-response fault remains unresolved; these timings are
  diagnostics, not suite latency or evidence of hosted failure.
- **Hosted EVAL-003:** discovered six MCP tools but generated a clarification instead of
  invoking one. HTTP 400 did not recur, but successful policy retrieval and a grounded answer
  were not demonstrated. This is a functional selection/clarification failure, not a
  recorded provider or MCP execution error.
- **Deployment:** the owner reports successful Streamlit prompts. Exact serving SHA,
  public grader access, a specific SYN-001 PTO transcript, both deployed workflow sequences,
  and real cold-start duration remain unverified.

## Final automated verification

At code baseline `e22dc700b8d9a7ccab0b22310fe4e0c506ccd5d4`, local Windows Python 3.11:

- Full pytest: **527 passed, 5 skipped, 0 failed**. The five skips are explicitly opt-in
  live checks: one provider smoke and four F004 live scenarios, not passes.
- Includes 16 Streamlit AppTest tests and 3 agent/MCP integration tests; scripted fixtures
  do not prove live-provider correctness.
- Repository-wide Ruff passed; workflow YAML and case validation passed (20 cases,
  five categories, 10 designated latency cases).
- All **33 original evidence-file hashes** matched after archival.
- [PR CI](https://github.com/jalarcon8/hr-ai-chat-bot/actions/runs/44220209930)
  passed Windows and Ubuntu before PR #8 merged. Both ordinary matrix jobs also passed at
  the merged SHA in run 44220869982. That run's separate live diagnostic job **failed**;
  its full-suite step was **skipped**. The overall run is not described as passing.

These hosted results cover the code baseline, not a future commit containing this final
documentation/evidence package. Review and merge it only after normal protected-main CI.
No new clean local installation or live workflow was attempted during closure.

## Outstanding assignment evidence

See the [33 F006 requirement rows](../docs/requirements/traceability.md),
[deployment record](../docs/deployed.md), and [demonstration checklist](../docs/demo-checklist.md).
The incomplete 20-case execution, ungraded quality/safety/clarification metrics,
insufficient latency sample, two unrecorded deployed workflows, demo/access/submission
checks, and unresolved local policy-search timeout are disclosed limitations, not waivers of
the assignment. Do not restart debugging or live evaluation without fresh owner approval.
