# F006 Coverage-First Continuation: Approved Single Run

Status: owner approved exactly one run after protected-main CI and merge.
No dispatch has occurred at this publication checkpoint; no second run is authorized.
This plan does not supersede any historical result, score, trace or report.

## Exact remaining coverage

The [canonical primary campaign](completion-metrics.json) attempted 001, 002, 003,
004, 005, 009 and 013. Archived live rows and started-attempt journals contain no
attempt of the following thirteen cases. Manifest selection alone is not an attempt.

| Category | Never-attempted case IDs | Count |
|---|---|---:|
| Straightforward policy | None; all four previously attempted | 0 |
| Multi-document | EVAL-006, EVAL-007, EVAL-008 | 3 |
| Tool-requiring | EVAL-010, EVAL-011, EVAL-012 | 3 |
| Ambiguous | EVAL-014, EVAL-015, EVAL-016 | 3 |
| Out-of-scope | EVAL-017, EVAL-018, EVAL-019, EVAL-020 | 4 |

Use the previous run's unattempted order, without reshuffling:
**017, 006, 010, 014, 018, 007, 011, 015, 019, 008, 012, 016, 020**.
Attempt each once, sequentially. The target is 20/20 **attempted**, not 20 successful
answers; fatal stops or time limits can still prevent complete attempt coverage.

## Request budget and unchanged application

- At most **13 agent requests** and **52 Groq completion operations**: the existing
  three-tool limit permits up to three tool-selection completions plus one final
  completion per case. Coverage preflight rejects a different tool limit.
- The pinned Groq 0.18 SDK defaults to two HTTP retries. With that unchanged behavior,
  budget up to **156 SDK HTTP attempts** (52 x 3). This is an upper-bound estimate,
  not a prediction or token-cost guarantee. Early completions/failures reduce usage.
- No evaluation-case retries, extra diagnostic, second run or new retry infrastructure.
  Zero case retries does not promise zero existing SDK-level HTTP retries.
- Keep the existing model, temperature, token setting, prompts, MCP tools, RAG index
  and agent/application architecture. Do not rerun the retrieval comparison.

## Stop policy and timebox

Only the exact pair **HTTP 400 + allowlisted `tool_use_failed`** is exempt from the
existing cumulative failure limit. Persist it as `provider_failure` with duration
and safe diagnostics, then advance to the next case without retrying it.

Retain immediate stops on HTTP 401/403/404/429 or corresponding authentication,
permission, quota/rate-limit and unavailable-model categories/codes. Fatal categories
take precedence even if an inconsistent diagnostic also contains `tool_use_failed`.
Missing provider diagnostics stop fail-closed. Stop at three cumulative **other**
provider/operational failures, preserving the existing conservative repeated-
infrastructure-failure safeguard. These stops apply once errors reach the runner;
existing SDK retries are unchanged.

The entire Ubuntu evaluation job has a **15-minute maximum**, including its dependency
setup, all cases and upload. The coverage step has a **10-minute sublimit**, leaving
time for setup and evidence upload. Required provider-free CI runs before this job
and is outside that live-job budget. This is not a per-case 15-minute allowance.
An interrupted started case is reported separately, never silently called unattempted.

## Separate artifacts and overwrite prevention

- Use `--cover-unattempted --output-dir <new-directory-outside-repository>`.
- The runner rejects output anywhere inside the repository or any existing output
  directory, even an empty one, before creating an agent session.
- Both agent and MCP trace paths must be inside that new directory.
- Preflight rejects selected IDs already present in repository JSONL evidence, including
  a prior started journal entry. A future dispatch must recheck current evidence and use
  one exclusive local dispatch marker; this is not permission for a second run.
- Workflow output: `$RUNNER_TEMP/f006-evaluation/coverage-$GITHUB_RUN_ID-$GITHUB_RUN_ATTEMPT`.
- New files: `coverage-manifest.json`, `coverage-attempts.jsonl`,
  `coverage-results.jsonl`, `coverage-summary.json`, agent/MCP traces and a separate log.
  The manifest records case order, timing panel, failure exemption and request budgets.
- Artifact name contains workflow run ID, attempt and SHA. Upload uses `always()` for
  ordinary failure/step-timeout cleanup. A platform hard kill/outage can prevent upload;
  no hosted filesystem can guarantee recovery in that circumstance.
- Prior raw results, offline grades, metrics, reports and checksummed archives remain
  unchanged. Do not replace a failed primary case with a more favorable diagnostic.

## After owner approval only

1. Publish the evaluation-only change through the existing protected-main PR gate;
   wait for required Windows and Ubuntu CI before normal merge.
2. Verify the approved main SHA and absence of any later attempts of these thirteen.
3. Dispatch exactly once on main:
   `run_live_evaluation=true`, `coverage_unattempted=true`,
   `continue_remaining=false`, `diagnostic_only=false`.
   Diagnostic/full-suite/old-continuation steps must all skip.
4. Preserve/download the new artifact with digest verification. No automatic rerun,
   even if the workflow exits nonzero after recording all selected outcomes.
5. Grade every returned answer offline against unchanged rubrics, retaining the existing
   source-backed claim/reference method and clearly labeling reviewer judgments.
6. Write separate `coverage-scores.json`, `coverage-metrics.json` and `coverage-report.md`;
   keep all earlier grades and aggregates as historical snapshots.
7. Report unique-case attempted coverage, completed/correct/incorrect/ungraded responses,
   provider/operational/interrupted failures and unattempted cases separately. State
   numerators, denominators and category/scored coverage for every quality metric.
8. Predeclare all thirteen new cases as one timing panel. Compute nearest-rank p50/p95
   only if at least ten new non-error completed responses qualify, including incorrect
   answers/clarifications/refusals. Keep failed durations and all older timings separate;
   otherwise explicitly retain the latency gap. Reuse k=3 versus k=5 unchanged.

Preparation verification: **57 provider-free evaluation tests passed**, targeted Ruff passed,
20 workflow YAML/gate/default/timeout checks passed, and 46 historical artifact hashes matched.
Case validation, 30 Markdown links, signature compatibility, Python syntax and protected-path/
whitespace checks passed. Model/prompts/tools/application, dataset and prior results are unchanged.
At the preparation checkpoint, changes were local and no live command was run.
The owner's subsequent approval authorizes publication through protected main and exactly
one coverage dispatch under the limits above; it does not authorize retries or another run.
