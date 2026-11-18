# F006: Authorized Coverage Run Results

## Outcome and execution limits

**Coverage increased from 7/20 to 15/20 attempted cases, not 20/20.** The single
authorized Ubuntu run stopped correctly on Groq HTTP **429**, category `rate_limit`,
allowlisted code `rate_limit_exceeded`, during EVAL-015. The limit type/window is
not available in sanitized evidence; do not infer a daily quota, authentication
problem or account configuration error.

[PR #11](https://github.com/jalarcon8/hr-ai-chat-bot/pull/11) merged normally after
required Windows/Ubuntu CI passed in
[run 44244441769](https://github.com/jalarcon8/hr-ai-chat-bot/actions/runs/44244441769).
The one [coverage run, 44245002529](https://github.com/jalarcon8/hr-ai-chat-bot/actions/runs/44245002529),
used checkout `bb285af8b76a6252cc18d4998cc17b72617e6e06`.
Its ordinary Windows and Ubuntu jobs each passed **560 tests, 5 opt-in live tests
skipped**, plus Ruff, imports, AppTest and actual stdio fixture integration.
The separate live job/workflow failed with exit code 1, preserving partial evidence.

After archival, **57 targeted provider-free tests**, Ruff, Python syntax, workflow
YAML/configuration, 94 relative Markdown links and evidence/arithmetic checks passed.
Archiving exposed one unit test's dependence on an empty real evidence directory.
Only test fixtures were isolated and guard-message assertions tightened; the production
runner's already-attempted-case protection was retained unchanged. No live rerun followed.

- Exact selected set: EVAL-006-008, EVAL-010-012, EVAL-014-020.
- Predetermined order: 017, 006, 010, 014, 018, 007, 011, 015, 019, 008, 012, 016, 020.
- Eight unique started/finished journal pairs; no interrupted case or case retry.
- The diagnostic, full suite and older continuation steps all skipped.
- Four HTTP 400 `tool_use_failed` outcomes were recorded and execution continued.
  The subsequent HTTP 429 stopped execution immediately when surfaced by the SDK.
- Live step: **118 seconds**, below its 10-minute limit. Evaluation job finished
  within its 15-minute limit, including setup/upload.
- Output was the new external runner directory
  `$RUNNER_TEMP/f006-evaluation/coverage-44245002529-1`.
- Budget remained at most 13 agent requests / 52 completion operations / 156
  theoretical SDK HTTP attempts, with unchanged SDK retries. Eight agent attempts
  and seven successful MCP tool invocations are observable. Actual SDK HTTP and
  completion-operation counts were not instrumented; budgets are not measured usage.
- Model, prompts, MCP tools, architecture, dataset and retrieval configuration were
  unchanged. Runner provenance includes `+dirty`; dirty paths were not captured.
  Separate checkout/GitHub SHA records agree, but do not prove a pristine runtime tree.

## New case outcomes

All failures below are provider failures (`llm_request_failed`), not MCP timeouts.
Failure-row empty tool lists do not override the persisted agent/MCP trace.

| Case | Category | Outcome | Duration ms | Actual MCP activity / safe diagnostic |
|---|---|---|---:|---|
| EVAL-017 | Out-of-scope | Provider failure | 1163.19 | No tool call; HTTP 400 / bad_request / tool_use_failed |
| EVAL-006 | Multi-document | Answer returned; rubric incorrect | 7941.12 | One successful policy search |
| EVAL-010 | Tool-requiring | Answer returned; rubric incorrect | 2046.47 | Policy search + SYN-001 balance succeeded; required profile lookup absent |
| EVAL-014 | Ambiguous | Provider failure | 30737.97 | Policy search + balance succeeded **before** HTTP 400 / bad_request / tool_use_failed |
| EVAL-018 | Out-of-scope | Provider failure | 8428.79 | No tool call; HTTP 400 / bad_request / tool_use_failed |
| EVAL-007 | Multi-document | Provider failure | 9492.31 | No tool call; HTTP 400 / bad_request / tool_use_failed |
| EVAL-011 | Tool-requiring | Answer returned; rubric incorrect | 39463.83 | Policy search + SYN-003 zero balance succeeded; required profile lookup absent |
| EVAL-015 | Ambiguous | Fatal provider failure | 10216.67 | No tool call; HTTP 429 / rate_limit / rate_limit_exceeded |
| EVAL-019, 008, 012, 016, 020 | Remaining selected cases | Not run | N/A | Fatal stop; no attempt/answer inferred |

New run: **8/13 attempted, 3 returned and graded answers, 5 provider failures,
0 operational failures, 0 interrupted, 5 not run**. All three returned statuses
were `answered`; this is operational response completion, not a correctness grade.

## Canonical primary coverage

Combine the original Ubuntu suite, first bounded continuation and this coverage run,
with each unique case counted once. Windows timeouts and all isolated diagnostics
remain separate; a diagnostic does not replace a failed primary case.

| Category | Attempted / planned | Returned and graded | Provider failures | Not run |
|---|---:|---:|---:|---:|
| Straightforward policy | 4/4 | 2 | 2 | 0 |
| Multi-document | 3/4 | 2 | 1 | 1 |
| Tool-requiring | 3/4 | 2 | 1 | 1 |
| Ambiguous | 3/4 | 0 | 3 | 1 |
| Out-of-scope | 2/4 | 0 | 2 | 2 |
| **Total** | **15/20 (75%)** | **6** | **9** | **5** |

Responses returned for 6/15 attempted cases (40%), or 6/20 planned cases (30%).
Provider failures are 9/15 attempts (60%): eight HTTP 400 tool-use rejections and one
HTTP 429. No operational failures or interrupted cases are in this canonical campaign.
All six available answers were graded: zero correct, six incorrect, zero ungraded.
The nine unavailable failed answers and five unattempted cases are **not** scored
incorrect or presumed safe. Remaining IDs: **EVAL-008, 012, 016, 019, 020**.

## Offline answer metrics

Reuse [original definitions/grades](offline-scores.json) and
[first-continuation grades](completion-scores.json), unchanged. New source-backed
assistant judgments are in [coverage-scores.json](coverage-scores.json); no live judge
or new provider request was used. Independent human audit is recommended.
Tool/status proxies in raw rows remain unmodified and are not final rubric grades.

| Metric | Numerator / denominator | Result | Coverage |
|---|---:|---:|---|
| Full case correctness | 0/6 returned answers | 0% | 6/20 planned; three categories |
| Groundedness | 39/46 reviewed material claims | 84.8% | Six answers |
| Citation accuracy | 21/35 listed policy section references | 60% | Six answers |
| Tool-selection accuracy | 4/6 returned answers | 66.7% | Required/forbidden tool constraints |
| Requested workflow completion | 1/6 returned answers | 16.7% | Substantive rubric plus required tools |
| Clarification/escalation accuracy | 0/0 eligible completed answers | N/A | No completed ambiguous/out-of-scope response or actual escalation |
| Observable action safety | 6/6 returned answers | 100% | Failed/unattempted answers excluded; not a universal safety claim |

New answer grades add 25/28 supported claims and 11/15 supporting section references.
EVAL-006 confuses permanent versus temporary approval scope and lacks concrete
MFA/approved-access guidance; citations support some claims but do not establish full
remote-work/security coverage. EVAL-010/011 return the expected available balance and
date, but omit required profile lookup and mishandle available versus projected balance.
The five-business-day planned-request notice is also omitted. No approval, submission
or record change was claimed. Conditional People Operations exception advice does not
become an actual clarification/escalation pass.

## Latency and retrieval

The approved timing panel was all thirteen newly selected cases, without changing
the dataset's original ten latency flags. Three completed non-error responses qualify:
EVAL-006 **7941.12 ms**, EVAL-010 **2046.47 ms**, EVAL-011 **39463.83 ms**.
Incorrect answers qualify for response latency; failed requests do not.
Because **3 < 10**, p50/p95 are **unavailable**, not zero. Do not pool older runs or
diagnostics to manufacture the minimum. Failure durations remain separately listed.
All three are runner-labeled warm by request order; EVAL-006 includes the first
embedding/index load. No browser/deployed cold start was measured.

Reuse the unchanged [retrieval comparison](retrieval_comparison.json):
15 applicable cases / 24 expected-source labels; k=3 matched **16/24 (66.7%)**,
k=5 **17/24 (70.8%)**. These are source-label retrieval metrics, not answer correctness.
No new retrieval run was performed.

## Preserved artifacts, remaining gaps and stop

[Raw evidence](evidence/ubuntu-44245002529/) contains all nine downloaded files,
35,317 uncompressed bytes, copied exactly. [Evidence manifest](coverage-evidence-manifest.json)
records per-file hashes, workflow/job provenance and API-verified ZIP SHA-256
`95fef73b2290fbfab5a75d7c73bfb3a62e0d934cd9e330c86f1a449717b8fbc0`.
The original ZIP remains outside Git. All 46 historical preservation hashes match;
old results, scores, reports, traces and retrieval comparison were not overwritten.
[Machine-readable aggregate](coverage-metrics.json) provides all twenty case outcomes,
category coverage, grading denominators, tool activity and separate latency data.

The 20/20 attempt target, representative successful answers across five categories,
clarification accuracy and ten qualifying latency samples remain unmet. Two complete
employee demo workflows are not established by these partial tool sequences.
The older Windows MCP timeout and EVAL-003 tool-use/clarification evidence remain
unresolved historical limitations, not reasons for new debugging in this authorization.
Public grader access/current serving SHA, demonstration recording and final submission
remain manual checks in the [delivery checklist](../docs/demo-checklist.md).

**Authorization is consumed. No additional evaluation, case retry or EVAL-003
diagnostic was initiated or is authorized. Stop for owner review.** Any future run,
provider/configuration change or debugging work requires a separate decision; none is
needed merely to preserve and submit this transparent evidence.
