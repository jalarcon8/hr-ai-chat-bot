# Deployment Record

## URLs and verification scope

- Application: <https://hr-ai-chat-bot-jonathan-alarcon.streamlit.app/>
- Repository: <https://github.com/jalarcon8/hr-ai-chat-bot>
- Recorded demo: **pending; no recording link supplied**.
- Health equivalent: open the app and use **Check MCP health**. It returns JSON app status
  and MCP discovery/connectivity status; there is no separate application HTTP health API.
  Discovery does not execute HR tools or call Groq.

The owner reported successful manual prompts. This is user-reported deployment evidence,
not an independently retained hosted transcript. Public grader access, exact serving
revision, the SYN-001 PTO workflow, both complete deployed tasks and cold-start timing
still need manual confirmation. No application request was made for Milestone 4.

## Reproducible Community Cloud configuration

Use the existing single Streamlit service, without a paid database or separately hosted MCP:

1. Select the repository above, protected branch `main`, and Python **3.11**.
2. The tracked main-file path is **`src/hr_app/app.py`**, also used by the local command
   below. Earlier owner messages called the entry point `app.py`; no root-level `app.py`
   exists in this checkout. Confirm the full configured path in Community Cloud before
   final submission rather than assuming a root wrapper exists.
3. Keep `requirements.txt` with `-e .` and the existing dependency pins in `pyproject.toml`.
4. Configure `GROQ_API_KEY` in Community Cloud **Secrets**, never in source or workflow
   inputs. The app maps it to the process environment if no explicit value already exists.
   Missing secrets do not crash UI startup; live provider requests still require a valid key.
5. Keep the existing default Groq model `openai/gpt-oss-20b`. Locally, an exported variable
   takes priority over `.env`; model aliases use `AGENT_MODEL_NAME` before `GROQ_MODEL`
   within each source. Do not publish secret values when checking configuration.
6. Deploy the checked-in `.hr_rag_index/active.json` and referenced FAISS generation with
   the synthetic `corpus/` and `data/`. The deployment does not rebuild an index at startup.
   The initial snapshot is 12 documents, 298 chunks and 600,764 bytes.

The app's `AgentSession` launches `python -m hr_mcp.server` as a same-service stdio child.
There is no MCP URL to configure; QR-035's separate-server URL condition is not applicable.
Run from the repository root so corpus, data and index paths resolve correctly.

```powershell
.\.venv\Scripts\python -m streamlit run src\hr_app\app.py
```

For intentional local use only, copy `.env.example` to `.env` and set your key there;
the Groq adapter reads it from the current working directory. Nonsecret RAG settings are
process environment variables, not automatically loaded from that file by every component.
The [README](../README.md) lists defaults and provider-free test commands.

## CI and release gate

Retain `.github/workflows/ci.yml`, the Windows/Ubuntu Python 3.11 matrix, Ruff/import checks,
named AppTest, MCP integration and full pytest. Require `test (windows-latest)` and
`test (ubuntu-latest)` before merge to `main`; the owner reported branch protection enabled.
Community Cloud is intended to track that protected branch, not a development branch.

[PR #8 CI](https://github.com/jalarcon8/hr-ai-chat-bot/actions/runs/44220209930) passed before
normal merge. At merged code SHA `e22dc700b8d9a7ccab0b22310fe4e0c506ccd5d4`,
[run 44220869982](https://github.com/jalarcon8/hr-ai-chat-bot/actions/runs/44220869982)
passed both ordinary matrix jobs; its opt-in EVAL-003 diagnostic failed functional checks.
Do not treat that overall run as green or infer the current Streamlit serving SHA from it.
[PR #9](https://github.com/jalarcon8/hr-ai-chat-bot/pull/9) subsequently merged after both
required checks passed. At checkout `05d462b16ac2271c3f6c3e315464c7a0d93e27d9`,
[run 44231546887](https://github.com/jalarcon8/hr-ai-chat-bot/actions/runs/44231546887)
passed both ordinary jobs (542 tests passed / 5 opt-in live tests skipped per platform).
Its one authorized continuation stopped at three HTTP 400 provider failures. Diagnostic
and full-suite steps were skipped; the overall live workflow failed. This still does not
identify the current deployed serving revision.

## Cold starts, costs and limits

The owner confirmed free Community Cloud hosting; exact current resource ceilings were not
measured. An idle/restarted service may need time to start Python, import dependencies,
launch MCP, and load the local embedding model. First retrieval may require a model download
if the cache is absent. Do not promise a cold-start duration, persistent cache, availability,
or a stable free-tier quota; no hosted cold start was timed.

Groq requires network access and available provider capacity. An HTTP 400 tool-use rejection,
Windows MCP timeouts and hosted clarification mismatch are recorded in the
[historical report](../evaluation/final-report.md) and
[bounded completion report](../evaluation/completion-report.md). The hosted app appeared functional
to the owner; these findings do not establish that both deployed HR tasks reliably pass.
No retry infrastructure or alternate provider was added.

The subsequent [coverage run](../evaluation/coverage-report.md) also observed a fatal
HTTP 429 `rate_limit_exceeded` and stopped without another run. This confirms rate
limiting for that request, not the limit window, a credentials problem or deployed
application failure. Coverage is 15/20 with six returned/graded answers; provider and
quality limitations remain explicit. No new deployed-app request was made.

## Before submission

Confirm URL access as the intended grader, the full entry-point path, current serving SHA
and protected-main tracking. Review already available screenshots/traces for both tasks
first; **additional live prompts remain paused** until the owner separately authorizes
demonstration recording. Use the [demo checklist](demo-checklist.md), retain only synthetic
information, and never capture secrets or hidden reasoning.

Reference: [official Community Cloud deployment documentation](https://docs.streamlit.io/deploy/streamlit-community-cloud).
