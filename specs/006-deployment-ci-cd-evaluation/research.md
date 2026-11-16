# Research: Deployment, CI/CD, and Evaluation

## Existing Project Findings

1. **Runtime and dependency installation**
   - The project targets Python `>=3.11,<3.12` and has pinned runtime dependencies in
     `pyproject.toml` and `requirements.txt`.
   - The package uses the `src/` layout. Local setup in `README.md` installs the project
     with `pip install -e ".[dev]"`; `requirements.txt` currently lists dependencies but
     does not install the local project. Community Cloud must be configured so `hr_app`,
     `hr_agent`, and `hr_mcp` are importable; plan to add `-e .` to the existing
     `requirements.txt`.
   - The app entry point is `src/hr_app/app.py`. It starts the existing synchronous
     `AgentSession` bridge and does not expose a raw HTTP health route.

2. **Existing CI and test coverage**
   - `.github/workflows/ci.yml` already runs on push and pull request to `main`, installs
     Python 3.11 dependencies, runs Ruff, checks MCP/agent imports, runs
     `tests/integration/test_agent_mcp.py`, and runs the full pytest suite on Ubuntu and
     Windows.
   - `tests/test_chat_interface.py` uses Streamlit `AppTest.from_file(...).run()` and is
     included in the full pytest run; it supplies app-start coverage without credentials.
   - `tests/integration/test_agent_mcp.py` discovers all six tools and invokes the actual
     MCP stdio server with a scripted LLM. This satisfies routine MCP discovery/call
     coverage without a live provider.
   - Reuse the current workflow and matrix. Add one clearly named AppTest step for an
     explicit app-start result, while retaining the existing full pytest run. Do not add
     another workflow or deployment job.

3. **Secret configuration**
   - `src/hr_agent/config.py:get_agent_setting` reads process environment variables before
     local `.env`, without mutating `os.environ`.
   - `src/hr_agent/llm.py:GroqLLMClient` obtains `GROQ_API_KEY` through that setting lookup.
   - Streamlit Community Cloud stores deployment secrets in its app settings and exposes
     them through `st.secrets`; the current provider lookup does not read `st.secrets`
     directly. A minimal UI-boundary bridge is needed. It must not import Streamlit into the
     core agent package or put the secret into `AgentConfig`.
   - Preserve an explicitly set environment value. If only a host secret exists, expose it
     to the existing environment-backed lookup for the process lifetime; do not persist or
     log it. Test the missing-secret path and ensure the UI still starts.

4. **RAG index and model lifecycle**
   - The current workspace has no `.hr_rag_index/`. `hr_mcp.server` uses the existing
     `Settings.index_dir`, default `.hr_rag_index`, and returns `index_unavailable` if the
     snapshot is absent. It does not build the index.
   - The F005 quickstart explicitly says the Streamlit app must not build or download the
     index at startup. F001's `build_index` creates an active pointer and checksummed
     generation from the synthetic corpus. The simplest hosted solution is to commit only
     the active generated snapshot and referenced generation.
   - `SentenceTransformerEmbedder` loads the model lazily when the first policy search
     occurs. This first-use model download and memory cost are cold-start risks to record;
     do not pre-download or rebuild at app startup.

5. **Provider failure**
   - The F005 quickstart records a prior live browser request that returned
     `llm_request_failed`. The user subsequently reported successful prompts on the deployed
     app; no per-request trace or exact provider diagnostics were retained.
   - `GroqLLMClient` translates bad requests to `ProviderRequestError` with allowlisted
     diagnostics and converts other SDK API errors to the safe `llm_request_failed` code.
     The UI reports a safe error code rather than raw provider text.
   - The single F006 evaluation attempt received a Groq tool selection, then the local
     `search_policy_documents` MCP call timed out after 302.20 seconds. This is recorded as
     an operational failure, not a provider failure. The runner stopped without retrying.
     Do not treat this local timeout as evidence of a hosted defect because the user reports
     successful deployed prompts.

6. **Streamlit Community Cloud**
   - The project owner selected Community Cloud, the existing Streamlit app, and a no-payment
     setup preference. Its official documentation describes free hosting, GitHub repository
     integration, configurable Python version, app secrets, and per-app resource/hibernation
     limits. The platform currently defaults to Python 3.12, so the app must explicitly use
     Python 3.11.
   - At the time of this plan, official Community Cloud documentation lists a 12-hour idle
     hibernation threshold and shared CPU/memory/storage limits. Limits can change; record
     the values shown in the host documentation/settings when deployed, rather than treating
     current figures as an SLA.
   - Verify at account setup that no payment information is required. If it is required,
     stop and ask before selecting another host.

## Decisions

| Topic | Decision | Rationale |
|---|---|---|
| Host | Streamlit Community Cloud, same F005 app, Python 3.11. | Direct fit for Streamlit; no extra service or deployment stack; user-selected free/no-payment target. |
| Dependencies | Reuse pinned requirements and install the project editable with `-e .`. | Ensures the existing `src/` package imports in a clean deployment, matching local setup. |
| Groq secret | Read host `st.secrets` at the Streamlit boundary and expose `GROQ_API_KEY` to existing environment lookup without persistence. | Keeps the existing Groq adapter and agent configuration; avoids broad core-agent changes. |
| Policy index | Generate and commit only the active `.hr_rag_index` snapshot from the current synthetic corpus. | Clean Community Cloud checkout needs an index; F005 prohibits startup-time index building; no storage service is needed. |
| CI | Keep one existing GitHub Actions workflow and matrix; require its test jobs on protected `main`. | Existing CI already covers installs, lint, imports, app startup through AppTest, MCP stdio, and full pytest. |
| Deployment trigger | Community Cloud tracks protected `main`; no separate deployment workflow. | Merges require existing CI checks and Community Cloud handles app deployment. |
| Hosted live test | One deployed PTO request for synthetic `SYN-001`, 8 hours on `2026-02-01`. | Checked-in synthetic data gives SYN-001 an 80-hour balance as of 2026-01-01. The smoke scenario exercises the existing UI-agent-MCP-RAG-Groq path. |
| Evaluation | One sequential 20-30 case Groq run; time a fixed 10-20 subset; append each completed result. | Satisfies assignment counts while preserving completed output if quota is exhausted. |
| Metric scoring | Human rubric for grounding/citations; trace/expected-outcome checks for operational measures; no LLM judge. | Simple, auditable, no second provider or evaluation framework. |
| Comparison | F001 retrieval source recall at k=3 versus k=5 for cases with expected sources. | Existing retrieval API, no additional Groq calls, no production setting change. |

## Alternatives Rejected

- **Build FAISS index or download it on app startup**: conflicts with F005 behavior and makes
  app startup dependent on model download and resource availability.
- **Deploy a separate MCP service or add a database/object store**: unnecessary for the
  existing stdio/single-service architecture and conflicts with the MVP constraints.
- **Add a new CI pipeline or automatic deploy action**: existing workflow already covers the
  automated checks; Community Cloud can deploy from the protected branch.
- **Add an LLM-as-judge or evaluation framework**: consumes additional quota and adds
  tooling; human evidence review plus trace-based scoring is sufficient for the required
  metrics.
- **Parallelize or automatically rerun live evaluations**: risks quota exhaustion and
  obscures which results belong to the approved bounded run.
- **Add another model provider**: user selected the existing Groq integration; ask before any
  provider expansion if a demonstrated blocker remains.

## Remaining Validation Gates

- Confirm Community Cloud account setup is available without payment information.
- Confirm Python 3.11, dependency installation, editable project import, and the active FAISS
  snapshot work in a clean Community Cloud build.
- Confirm the app can start the MCP stdio subprocess, access synthetic JSON fixtures, and
  load the embedding model within the host's current limits.
- User reports successful hosted prompts, but the exact deployed SYN-001 workflow and
  per-request Groq/RAG/MCP evidence were not retained. Do not repeat the hosted smoke test
  absent a failure; document this scope limitation.
- Confirm required GitHub status checks are configured for `main` and that Community Cloud
  tracks that branch.
- The bounded live evaluation was attempted once after local deterministic checks. It stopped
  on the first local MCP search timeout; preserve this partial result and do not rerun without
  review of the operational blocker. No provider failure was observed.

## External Platform References

- [Community Cloud deployment](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)
- [Community Cloud app limits and hibernation](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app)
- [Community Cloud secrets management](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management)
