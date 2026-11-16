# Data Model: Deployment, CI/CD, and Evaluation

## Overview

F006 adds no database or application persistence. Deployment settings remain in Streamlit
Community Cloud and GitHub repository settings. The only committed runtime artifact beyond
the existing source/data is the active F001 FAISS snapshot required by the clean deployment.
Evaluation cases and privacy-safe results are versioned files under `evaluation/`.

## Deployment Configuration

| Value | Meaning | Storage and handling |
|---|---|---|
| `app_entrypoint` | Existing Streamlit app path `src/hr_app/app.py`. | Community Cloud app configuration; no second web service. |
| `python_version` | Python 3.11, required by the project's `>=3.11,<3.12` constraint. | Community Cloud advanced settings and deployment documentation. |
| `dependency_manifest` | Existing pinned `requirements.txt`, plus editable project installation (`-e .`). | Tracked manifest; no new runtime packages. |
| `GROQ_API_KEY` | Existing Groq credential used by `GroqLLMClient`. | Set only in Community Cloud secrets; bridge from `st.secrets` to process environment at the Streamlit boundary. Never written to files, traces, UI, or CI. |
| `AGENT_MODEL_NAME` / `GROQ_MODEL` | Existing nonsecret model selection, with `AGENT_MODEL_NAME` precedence. | Optional host setting; document the selected model identifier, not credentials. |
| `HR_RAG_INDEX_DIR` | Existing index location, default `.hr_rag_index`. | Keep default unless deployment proves a path override necessary. |
| `deployment_url` | Shareable Community Cloud URL. | Record in README and `docs/deployed.md` after deployment is verified. |
| `health_equivalent` | F005 sidebar **Check MCP health** JSON view. | Document as an in-app check, not a raw `/health` HTTP endpoint. |
| `main_branch_checks` | Existing GitHub Actions matrix checks required before merge. | GitHub branch-protection setting; verify manually and do not store credentials. |

The secret bridge must preserve process environment precedence. Missing host secrets must not
prevent app startup or expose values; a request without credentials continues to return the
existing safe failure code. The bridge must not store a secret in `AgentConfig`, the chat
history, an evaluation artifact, or any trace.

## Deployed FAISS Snapshot

The existing F001 `build_index` creates:

- `.hr_rag_index/active.json`, a pointer to the active generation and its metadata/index
  checksums.
- `.hr_rag_index/generations/<generation-id>/metadata.json`, containing synthetic document
  and chunk metadata plus embedding/chunking identity.
- `.hr_rag_index/generations/<generation-id>/index.faiss`, containing local vector data.

F006 ships the active pointer and referenced generation built from the checked-in synthetic
corpus. It does not ship model weights, secrets, temporary build files, or obsolete
generations. The active pointer and checksums must validate before deployment. The app and
MCP server continue to treat a missing or incompatible index as an explicit operational
failure; neither builds the index at startup.

`SentenceTransformerEmbedder` still loads the configured embedding model lazily when the
first policy search occurs. Record its first-use download/cold behavior and any host resource
limits; do not disguise a first-use failure as an unsupported policy answer.

## Evaluation Case

`evaluation/cases.json` is a list of 20-30 synthetic requests. Each case uses the following
logical fields; case-specific fields may be omitted only when they do not apply:

| Field | Type | Purpose |
|---|---|---|
| `case_id` | string | Stable unique ID for results and review. |
| `category` | enum | `policy`, `multi_document`, `tool_requiring`, `ambiguous`, or `out_of_scope`; collectively cover all required categories. |
| `request` | string | Synthetic employee request; no real personal data. |
| `context` | object or null | Explicit synthetic context such as `employee_id`; identity is not inferred from free text. |
| `gold_answer_or_rubric` | string | Expected facts, limitations, and acceptable response behavior. |
| `expected_source_ids` | string array | Policy source IDs required to support policy claims; empty only when no policy evidence applies. |
| `required_tools` | string array | Tools that must be selected for the case. |
| `forbidden_tools` | string array | Unsafe or irrelevant tools that must not be called. |
| `expected_status` | string or array | Acceptable response status/disposition where deterministic from the case. |
| `safety_assertions` | string array | Case-specific safety outcomes, including no draft/send/update unless explicitly allowed. |
| `latency_sample` | boolean | Marks a fixed 10-20 case subset for p50/p95. Selection is stable, not randomized. |

Tool expectations are sets or case-specific constraints, not a globally fixed call order;
F003 may select a valid sequential order based on the request. Ambiguous/out-of-scope cases
can require clarification or refusal without employee-specific lookup.

## Evaluation Result

Append one JSON object per attempted case to `evaluation/results.jsonl` so completed results
survive process interruption or a provider quota limit. Do not write duplicated prompts,
provider request/response payloads, hidden reasoning, credentials, or full employee records
to result rows. The final user-visible answer is retained for manual scoring of synthetic
cases.

| Field | Type | Meaning |
|---|---|---|
| `case_id` | string | Matches a case in `cases.json`. |
| `run_id` | string | One bounded evaluation run identifier. |
| `code_revision` | string | Git commit associated with the run. |
| `outcome` | enum | `completed`, `provider_failure`, or `operational_failure`. |
| `response_status` | string or null | Safe returned status when available. |
| `answer` | string or null | Final user-visible answer for manual scoring; no hidden reasoning or raw provider messages. |
| `tool_names` | string array | Ordered names of tools actually invoked; no argument values. |
| `tool_outcomes` | object array | Safe per-tool status and source identifiers only; no arguments or raw results. |
| `source_ids` | string array | Returned policy document IDs only. |
| `metric_scores` | object | Per-case pass/fail/manual-review values; unavailable values are null, not successful. |
| `duration_ms` | number or null | Wall-clock duration of `AgentSession.process_request`, including LLM and MCP work but not browser rendering. |
| `latency_condition` | enum or null | `first_request`, `warm`, or `unknown`, as observable; do not fabricate a cold/warm label. |
| `failure_code` | string or null | Existing safe error code/category; never raw provider text or key. Unknown provider cause remains `provider_failure_unknown`. |
| `model_id` | string | Nonsecret configured model identifier for the run. |

When authentication/quota/provider failure prevents a case from completing, record the
failure separately and stop further live calls when it indicates remaining quota is
unavailable. The failed case and remaining unrun cases do not count as functional passes or
failures; report attempted, completed, failed, and not-run counts and each metric's
denominator.

## Metric Scoring

- **Groundedness**: Human reviewer checks substantive factual claims in the final answer
  against the synthetic case rubric and checked-in policy evidence; no raw tool results need
  to be persisted.
- **Citation accuracy**: Human reviewer checks that returned source IDs and snippets support
  the associated policy claims and expected source references.
- **Tool-selection accuracy**: Compare actual ordered tool names against case-required and
  forbidden tool constraints; do not require one exact sequence when order is flexible.
- **Workflow completion**: Compare the returned status and safe tool outcome fields to the
  case's expected completion/limitation rubric.
- **Escalation/clarification accuracy**: Check that the expected missing information,
  clarification, or human-review outcome is present and unsupported decisions are absent.
- **Action-safety pass rate**: Check that no email is sent, request approved/submitted, or
  employee record changed; any explicitly requested draft remains unsent and follows the
  existing confirmation contract.

Report each metric as numerator/denominator and percentage. Provider and host failures are
reported separately from application/functional failures. No LLM judge is used.

For p50 and p95, sort the selected durations and use nearest-rank percentiles with
one-based rank `ceil(p * n)`. Record the exact sample count and exclude provider-failed or
unrun cases from latency samples while reporting their counts separately.

## Retrieval Comparison

For each evaluation case with `expected_source_ids`, use the existing F001 retrieval
interface and same active index to compare evidence returned at `k=3` and `k=5`. Define
source recall at k as:

```text
number of expected source IDs present in retrieved evidence / number of expected source IDs
```

Aggregate the comparison over applicable policy cases. Reuse the expected-source labels and
case set; this comparison does not call Groq and does not change the production retrieval
setting (`k=5`).

## Verification Evidence

| Evidence | Contents | Verification owner |
|---|---|---|
| CI run | Existing Windows/Ubuntu checks, app-start AppTest, MCP stdio integration, pytest, and Ruff results. | Automated; inspect hosted GitHub Actions run. |
| Branch protection | Required status checks on `main`; Community Cloud tracks `main`. | Manual GitHub settings verification. |
| Deployment record | URL, app entry point, Python version, health-equivalent result, host limits, and cold-start observations. | Manual deployment smoke test. |
| Live workflow record | Synthetic case ID, response status, tool names/outcomes, source IDs, and safe pass/fail/inconclusive result. | Manual review of deployed UI. |
| Evaluation record | Case/run IDs, per-case outcomes, metric scores/denominators, latency samples and percentiles, retrieval comparison, and quota failures. | Mixed: runner output plus human evidence scoring. |
| Submission record | Repository/demo/deployment links, grader access, demo duration/content, dashboard/group actions. | Manual submitter/reviewer verification. |

No evidence record includes API keys, government identity documents, hidden reasoning, or
unnecessary raw employee information.
