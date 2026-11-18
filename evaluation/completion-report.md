# F006 Bounded Evaluation Completion Checkpoint

## Outcome and execution limits

[PR #9](https://github.com/jalarcon8/hr-ai-chat-bot/pull/9) merged normally after both
required Windows/Ubuntu checks passed. Exactly one
[Ubuntu continuation](https://github.com/jalarcon8/hr-ai-chat-bot/actions/runs/44231546887)
ran at checkout `05d462b16ac2271c3f6c3e315464c7a0d93e27d9`, using the existing
`openai/gpt-oss-20b` model, prompts, MCP tools and application architecture.

The continuation stopped at **three cumulative provider failures**, as authorized:
4/17 selected cases attempted once, 1 operationally completed, 3 provider failures,
0 operational failures, 13 unattempted and 0 interrupted cases. Its live step lasted
27 seconds, below the 15-minute limit. Both diagnostic and full-suite steps were skipped.
Both ordinary CI matrix jobs passed; the live job/workflow failed, not the tests.
There was no case retry, additional diagnostic, full-suite rerun or second live run.

| Case | Outcome | Duration | Observed tool activity / safe failure |
|---|---|---:|---|
| EVAL-004 | Provider failure | 1270.22 ms | Discovery succeeded; HTTP 400 / `bad_request` / `tool_use_failed` before tool execution |
| EVAL-005 | Answer returned; graded below | 9779.27 ms | Two successful policy searches; PTO and holiday evidence used |
| EVAL-009 | Provider failure | 7938.71 ms | `check_pto_balance` succeeded; subsequent Groq call failed HTTP 400 / `bad_request` / `tool_use_failed` |
| EVAL-013 | Provider failure | 3493.42 ms | Discovery succeeded; HTTP 400 / `bad_request` / `tool_use_failed` before tool execution; stop limit reached |

Unattempted, in the predeclared order: EVAL-017, 006, 010, 014, 018, 007, 011, 015,
019, 008, 012, 016 and 020. Selection in the manifest is not evidence of execution.
All four started journal entries have matching finished entries and result rows.
EVAL-009's empty failure-row tool list does not override its persisted successful
balance-tool event. It produced no final balance answer or completed employee workflow.

These failures do not establish an authentication, quota, rate-limit or MCP transport
problem. Existing HTTP 400 tool-call-generation failures recurred; no further debugging
or live request was authorized or performed after the stop.

## Offline answer review and denominators

The [initial scores](offline-scores.json) and [new EVAL-005 score](completion-scores.json)
review saved answers against the unchanged rubrics, corpus sections and traces.
These are source-backed assistant judgments, not independent human sign-off or a live
LLM judge. Claim/reference units and reasons are recorded for audit. Original null
fields are preserved; supplementary review does not overwrite raw results.

Canonical primary evidence combines the original Ubuntu suite EVAL-001/002/003 with this
continuation: **7/20 attempted, 3 answers returned and graded, 4 provider failures,
0 operational failures, 13 unattempted**. Diagnostics never replace primary EVAL-003.
Returned-answer metrics below exclude unavailable failed answers, which are not passes.
The zero operational-failure count refers to this Ubuntu campaign, not the separately
preserved Windows MCP timeouts.

| Metric | Numerator / denominator | Coverage / interpretation |
|---|---:|---|
| Full answer correctness | 0/3 (0%) | All three returned answers reviewed; 17/20 planned cases lack a graded answer |
| Groundedness | 14/18 (77.8%) | Supported material claim units across three answers; omissions assessed separately |
| Citation accuracy | 10/20 (50.0%) | Supporting section references in Sources lists, not merely expected document IDs |
| Tool-selection accuracy | 3/3 (100%) | Required/forbidden tool-name constraints for completed answers only; not all attempted cases |
| Workflow completion | 1/3 (33.3%) | Requested task/rubric satisfaction, not the runner's response-status proxy |
| Clarification/escalation accuracy | N/A (0 scored) | No completed primary case eligible; no invented percentage |
| Action-safety pass rate | 3/3 (100%) | Observable assertions/actions for returned answers; no failed/unseen response presumed safe |

EVAL-001 omits the requested five-business-day planned-PTO notice and overstates manager
timing. EVAL-002 supplies unsupported ineligibility coding and mislocates schedule
guidance. EVAL-005 answers the holiday-versus-approval question and identifies the manager
(workflow pass), but its additional **must**-within-three-business-days assertion
conservatively fails full correctness: policy says **normally** within three business
days. This judgment is explicit and should be human-audited, not silently treated as
an objective independent grade.

| Category | Planned | Attempted | Completed and graded |
|---|---:|---:|---:|
| Straightforward policy | 4 | 4 | 2 |
| Multi-document | 4 | 1 | 1 |
| Tool-requiring | 4 | 1 | 0 |
| Ambiguous | 4 | 1 | 0 |
| Out-of-scope | 4 | 0 | 0 |

Four categories were attempted; only two yielded answers. Out-of-scope coverage and
meaningful clarification/escalation scoring remain missing.

## Latency and retrieval comparison

Only **1/17 predeclared new timing-panel cases** produced a qualifying non-error response:
EVAL-005, **9779.27 ms**. Thus **p50/p95 are unavailable**, not estimated from one sample.
The three provider-failure durations remain separate above. The two historical primary
durations (5431.65 ms session-first, 1567.44 ms warm) and all diagnostic timings are
preserved but not pooled with the new run.

EVAL-005 is runner-labeled warm, but its first policy tool call took 8086.38 ms and
included lazy model initialization; this is not a measured browser/host cold start.
No cold-start percentile is claimed.

The unchanged [retrieval comparison](retrieval_comparison.json), covering 15 cases /
24 expected-source labels, matched **16/24 (66.7%) at k=3** and **17/24 (70.8%) at k=5**.
That is source-label recall, not answer correctness; no new retrieval run was needed.

## Verification, preservation and remaining gaps

- Local: **39 targeted provider-free tests passed**, repository-wide Ruff passed,
  workflow YAML/default/gate/selection/timeout checks and JSON/link checks passed.
- [PR CI](https://github.com/jalarcon8/hr-ai-chat-bot/actions/runs/44230694377) and both
  ordinary jobs in the authorized run passed Windows/Ubuntu checks before live execution.
  Each ordinary job in the authorized run recorded **542 passed, 5 opt-in live tests skipped**.
- [Artifact manifest](completion-evidence-manifest.json) records nine byte-preserved
  artifact files, per-file SHA256s and verified ZIP digest. The ZIP remains outside the
  repository. All older result/trace/archive/report evidence remains unchanged.
  Evidence paths disable Git text conversion so checksums survive Windows/Ubuntu checkout.
- Workflow SHA files confirm checkout; the runner additionally reports `+dirty`.
  Dirty-path provenance was not captured, so an exactly pristine runtime workspace is
  not asserted. No architecture change or investigation is introduced to explain it.
- The [historical report](final-report.md), Windows MCP timeout, earlier EVAL-003 failure
  and isolated clarification behavior remain intact. No favorable diagnostic substitutes
  for failed primary results.

**Assignment evaluation remains incomplete:** 13 primary cases are unattempted, only
three answers are graded, three categories lack completed answers, clarification/escalation
accuracy is unavailable, and the required 10-20 valid latency samples/p50/p95 are unmet.
QR-041/042 are quantitatively reported with limited coverage; QR-043 remains unmet.
QR-040 case-set and QR-044 retrieval-comparison evidence are retained.

Before submission, human-audit the disclosed grading, confirm deployed access/serving
revision and grader access, demonstrate both employee workflows, record the required
demo, and finish the [delivery checklist](../docs/demo-checklist.md). Those manual gaps
are not resolved by these evaluation artifacts. Any further live run or architecture
change requires a new owner decision; **no automatic continuation is planned**.

Machine-readable arithmetic and coverage: [completion-metrics.json](completion-metrics.json).
Raw new evidence: [Ubuntu run archive](evidence/ubuntu-44231546887/).
