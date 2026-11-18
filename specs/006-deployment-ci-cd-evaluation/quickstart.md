# F006 Deployment and Evaluation Runbook

This runbook describes planned F006 checks. Complete them only after implementation is
approved and the project owner confirms Community Cloud account setup is available without
payment information. All example employee data and requests are synthetic.

## 1. Local readiness

From the repository root, install the existing Python 3.11 project and development
dependencies:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
```

Provide local `GROQ_API_KEY` through `.env` only for intentional live testing. Never commit
`.env` or paste a key into a command, issue, chat, or result file.

Run the focused automated checks before configuring deployment:

```powershell
.\.venv\Scripts\python -m pytest tests\test_chat_interface.py tests\integration\test_agent_mcp.py -q
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m ruff check .
```

These are deterministic/provider-free checks. The AppTest UI test starts the Streamlit app in
the test harness; the MCP integration test discovers and invokes the real stdio server with
a scripted model. In the existing GitHub Actions workflow, add a named `Run Streamlit
AppTest startup` step running `python -m pytest tests/test_chat_interface.py -q`; retain
its MCP integration and full pytest steps.

## 2. Prepare the deployment index

The Community Cloud checkout needs the F001 active FAISS snapshot. The application does not
build an index at startup. From the repository root, use the existing F001 API and configured
corpus/model to build `.hr_rag_index`:

```python
from hr_rag import ChunkingConfig, SentenceTransformerEmbedder, build_index

embedder = SentenceTransformerEmbedder("sentence-transformers/all-MiniLM-L6-v2")
build_index(
    ".hr_rag_index",
    corpus_dir="corpus",
    embedder=embedder,
    chunking_config=ChunkingConfig(max_tokens=200, overlap_tokens=30),
)
```

The initial build may download the embedding model and requires network access. Verify that
`.hr_rag_index/active.json` points to one complete generation with matching checksums and
metadata, then include the active pointer and referenced files in the deployment commit.
Do not include model caches, temporary index generations, `.env`, or trace files. A clean
Community Cloud build must not depend on a startup-time index build.

The existing `requirements.txt` will include `-e .` so the pinned dependencies and the
project's `src/` packages are available from the Community Cloud checkout.

## 3. Configure CI and the protected deployment branch

Use the existing `.github/workflows/ci.yml`; do not create a separate deployment workflow.
The workflow must pass on the change before deployment. In GitHub repository settings:

1. Require the existing Ubuntu and Windows matrix checks before merging to `main`.
2. Block direct pushes that would bypass required checks.
3. Configure Community Cloud to track `main`.
4. Verify the required check names against the checks shown by an actual Actions run.

These branch-protection and Community Cloud settings are manual evidence; pytest cannot
verify them. Reuse the current workflow for Ruff, import checks, the stdio MCP integration,
the named AppTest step, and the full pytest suite. Its separate Ubuntu evaluation job is
available only through a manual dispatch after the ordinary test matrix passes.

## 4. Deploy and verify one live vertical slice

In Streamlit Community Cloud, configure:

- Repository root as the app root.
- Python 3.11.
- `src/hr_app/app.py` as the entry point.
- `GROQ_API_KEY` in the app's Secrets settings, with no value stored in the repository.

The user reports the app is deployed at
<https://hr-ai-chat-bot-jonathan-alarcon.streamlit.app/> and that several prompts produced
successful chatbot responses. No per-prompt traces or running deployment commit were retained.

The Streamlit boundary maps the host secret to the existing environment-backed Groq
configuration for the process lifetime. The key must not be printed, persisted, or included
in diagnostics. Keep the existing default model unless deployment validation requires a
nonsecret model setting change; do not add another provider.

After deployment:

1. Open the shareable app URL and verify the chat renders.
2. Use **Check MCP health**. Confirm the JSON result reports app availability and successful
   MCP discovery (six tools). This check does not call Groq and is not sufficient proof that
   the provider is configured.
3. Enter `SYN-001` in the synthetic employee ID field.
4. Ask: `Can I request 8 hours of PTO on 2026-02-01? Check my available balance and explain the policy steps.`
5. Verify the returned answer uses the synthetic employee profile, 80 available hours as of
   `2026-01-01`, an `HR-002` policy citation and snippet, and the visible ordered tool
   activity; it must not claim the request was submitted or approved.
6. Record only the case ID, safe status, tool names/outcomes, source IDs, overall pass/fail/
   inconclusive result, deployment commit, and measured latency if available. Do not retain
   credentials or unnecessary raw content.

The user reports successful hosted prompts and no `llm_request_failed` during those tests.
The exact Groq/RAG/MCP details and the specific SYN-001 scenario are only partially verified.
Do not repeat the hosted smoke request without evidence of a failure. The separate local
F006 evaluation did return an MCP search timeout; it is recorded as an operational failure,
not a provider failure. If a hosted smoke request fails:

- Do not blindly retry or change providers.
- Verify that the host secret exists without printing its value, the app selected the
  expected configured model, and the host has completed app startup.
- Check the UI's safe error code and any already-available sanitized provider diagnostic.
  Do not enable raw provider request/response logging.
- Classify `llm_request_failed` as a provider failure; distinguish authentication, quota, or
  request rejection only when the safe code/diagnostic supports it. Otherwise record an
  unknown provider failure, separate from MCP/index or response-behavior failures.
- Stop and record unresolved or quota failures; do not claim a successful live workflow.

## 5. Run the bounded evaluation once

The local partial attempt is recorded in `evaluation/results.md` and must remain intact. The
existing CI workflow provides a clean Ubuntu run that performs one MCP-backed diagnostic
case before the bounded evaluation. The diagnostic and full suite use separate output files;
the job does not overwrite the checked-in partial results.

- k=3 source recall: 16/24 (66.7%).
- k=5 source recall: 17/24 (70.8%).

1. Add `GROQ_API_KEY` under the repository's **Settings → Secrets and variables → Actions**
   as an Actions secret. Do not put its value in workflow inputs, source, or logs.
2. Commit and push the approved F006 changes to protected `main`; merge only after the
   existing Ubuntu and Windows CI checks pass.
3. In **Actions → Python CI → Run workflow**, select `main` and set
   `run_live_evaluation` to `true`. Leave `diagnostic_only=true` (the default) while
   investigating the provider failure; obtain review before triggering another live run.
   The workflow checks out and records that exact commit, waits for the existing test
   matrix, then runs only the selected `diagnostic_case` (default `EVAL-001`).
   For the authorized isolated remote-work investigation, set
   `diagnostic_case=EVAL-003` and keep `diagnostic_only=true`. This does not run
   `EVAL-001` or the full suite. Dispatch it once after the selector change is merged;
   preserve its artifact separately from previous runs and stop for review.
   The equivalent runner option is
   `--diagnostic --diagnostic-case EVAL-003 --output-dir <new-output-directory>`.
   Unknown IDs or cases without a required MCP tool are rejected before live execution;
   `--diagnostic-case` cannot be combined with `--live` or `--validate-only`.
4. If the diagnostic fails or does not successfully complete its required MCP search, the
   full evaluation step is skipped. The artifact still includes the diagnostic result/log,
   sanitized MCP/agent traces, and checkout revision. `agent-traces.jsonl` retains safe
   provider categories, HTTP status, and allowlisted codes, never raw provider messages.
   Do not rerun after a failure without review or assume quota/credential failure.
5. Only when separately approved, set `diagnostic_only=false`. If the diagnostic succeeds,
   the runner then executes the existing 20 cases sequentially,
   including the fixed 10 latency samples and k=3/k=5 retrieval comparison. It does not retry
   cases. It reports attempted, completed, provider-failed, operational-failed, and unrun
   counts separately; an incomplete run has a failing job status but its outputs are retained.
6. Download the `f006-evaluation-<commit-sha>` Actions artifact. Review `diagnostic.jsonl`,
   `diagnostic.log`, `mcp-traces.jsonl`, `agent-traces.jsonl`, `results.jsonl`, `results.md`,
   `retrieval_comparison.json`, `evaluation.log`, and the recorded revision files. The
   workflow artifact contains no API key. Suite outputs are absent for diagnostic-only runs.
7. Manually score groundedness and citation accuracy against the case evidence/rubric.
   Score tool selection, workflow completion, escalation/clarification, and action safety
   from expected outcomes and the returned safe trace. Report numerator, denominator, and
   percentage for each metric; unavailable/provider-failed cases are not functional passes.
8. Report p50 and p95 for the fixed 10 latency samples from the suite run. Use end-to-end
   `AgentSession.process_request` elapsed time (LLM plus MCP; not browser rendering), and
   identify the first request/cache condition. Use the nearest-rank percentile convention:
   sort durations and select rank `ceil(p * n)` using one-based rank. If a distinct hosted
   cold-start is observed, report it separately; do not fabricate a cold sample.

## 6. Final submission evidence

Record and review:

- Passing GitHub Actions run and required `main` branch checks.
- Shareable Community Cloud URL, in-app health-equivalent result, Python version, cold-start
  observations, and any actual host/account limitations.
- One deployed PTO workflow outcome and safe evidence summary, including any
  `llm_request_failed` or other unresolved status.
- Evaluation case count/categories, per-case results, metric denominators, p50/p95 sample
  count and values, retrieval comparison, model identifier, and provider/quota limitations.
- Updated README and `docs/deployed.md`, `docs/design-and-evaluation.md`, and
  `docs/ai-tooling.md`.
- Repository/demo links, `quantic-grader` access, 7-10 minute demo showing both deployed
  workflows, and dashboard/group submission checks.

Verify presenter and participant requirements manually. Do not store government identity
documents or secrets in the repository.
