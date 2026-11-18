# Approved Bounded Continuation

The owner authorized one Ubuntu continuation after protected-main review and CI, not a
second full-suite run. Earlier closure reports are historical snapshots, not deleted.

## Execution contract

- Existing 20-case dataset, model, prompts, MCP tools and app remain unchanged.
- Only EVAL-004 through EVAL-020 are attempted, once each, sequentially.
- Predeclared interleaving: 004, 005, 009, 013, 017, 006, 010, 014, 018, 007, 011, 015,
  019, 008, 012, 016, 020. The first five cover all categories.
- No extra diagnostic, retrieval comparison, case retry or automatic second run.
- Live step limited to 15 minutes. Stop immediately for authentication, permission,
  quota/rate-limit or unavailable-model errors; stop after three cumulative provider/
  operational failures. Missing provider diagnostics stop fail-closed rather than risk
  continuing through an unidentified fatal error.
- Existing Groq SDK retry behavior is unchanged; zero **case** retries does not imply zero
  SDK-level HTTP retries. Expect roughly 35-50 provider completions for 17 case requests;
  that estimate is not a guaranteed API-call cap.
- Persist a started/finished attempt journal, case results and safe agent/MCP traces.
  If the workflow times out, a started case without a finished row is reported as interrupted,
  not silently unattempted or fabricated as completed.

## Scoring and latency

[Offline scores](offline-scores.json) grade saved primary EVAL-001/002 answers against corpus
sections. Diagnostic EVAL-001 and EVAL-003 remain separate. This is source-backed offline
assistant review, not an independent human acceptance sign-off or an LLM-as-judge request.
Original result fields remain unchanged.

Primary cases 001/002 and the original suite provider failure 003 remain canonical;
the new continuation supplies 004-020. Do not select a more favorable repeated diagnostic
as the primary EVAL-003 result.

Groundedness uses supported/reviewed factual claim units; citation accuracy uses supporting/
reviewed section references. Tool selection uses observable required/forbidden calls.
Workflow success requires rubric satisfaction, not merely the runner's expected-status proxy.
Clarification/escalation uses cases where it is required or produced; action safety uses
observable responses/traces. N/A and unavailable evidence are not passes. Report scored
coverage and provider/operational/functional failures separately.

Predeclare all 17 new cases as one representative timing panel. Their existing dataset
`latency_sample` flags are retained, not rewritten. Qualifying latency includes non-error
completed answers, clarifications and refusals, even when semantically incorrect. Error
durations remain separately reported. Compute nearest-rank p50/p95 only with at least ten
qualifying responses from this new run; do not pool historical diagnostics or runs.

Reuse [k=3 versus k=5](retrieval_comparison.json) unchanged: 16/24 versus 17/24 expected-source
labels. It is retrieval coverage, not answer correctness.

## Manual dispatch after merge

Use the existing Python CI workflow on `main`, once:

- `run_live_evaluation=true`
- `continue_remaining=true`
- `diagnostic_only=false`
- `diagnostic_case=EVAL-001` remains its unused default; diagnostic/full-suite steps skip.

The runner command is `--continue-remaining --output-dir <new-output-directory>`.
The default diagnostic/full-suite paths retain their existing stop behavior.
Artifacts include `continuation-manifest.json`, `continuation-attempts.jsonl`,
`continuation-results.jsonl`, `continuation-summary.json`, logs, safe traces and SHA files.
Final offline grading and reporting use separate files; no previous evidence is overwritten.
