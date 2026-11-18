# Design and Evaluation

## Architecture

```text
Browser -> Streamlit (src/hr_app/app.py)
              -> AgentSession -> HRAgent -> Groq chat/tool calling
                                   |
                                   v
                              MCPClient
                                   | stdio, one same-service subprocess
                                   v
                       FastMCP (hr_mcp.server)
                         |                 |
                  policy search       synthetic JSON data
                         |             employee / PTO
                  MiniLM embeddings
                         |
                   local FAISS index
```

The LLM chooses one tool per completion; the agent validates and invokes it through MCP,
then supplies its result to the next completion. There is no direct RAG bypass for policy
answers, external HR integration, paid database, or second provider. MCP discovers six
tools; the agent exposes the existing supported subset of five to Groq (`get_policy_section`
remains an MCP developer tool). See the [tool schemas and envelopes](../specs/002-mcp-tool-integration/contracts/mcp-tools.md).

## Why these choices

- **Orchestration:** existing typed Python agent and session bridge fit Streamlit's synchronous
  request handling. One long-lived MCP subprocess/session avoids per-tool initialization.
  Default bound: three executed tool calls per request, sequential rather than parallel.
- **MCP:** stdio keeps discovery, validation and actual tool invocation inside the free-tier
  service; no separately hosted endpoint or network authentication subsystem is required.
- **Schemas:** typed MCP inputs and structured result envelopes separate found, not-found,
  indeterminate and operational failure. Strict arguments and employee-context consistency
  prevent a model from silently selecting another employee.
- **RAG:** local `all-MiniLM-L6-v2` embeddings and FAISS avoid a paid vector service.
  Deterministic 200-token chunks with 30-token overlap retain small excerpts and citation
  metadata. Top-k defaults to five; measured recall was slightly higher than k=3, without a
  claim of improved answer correctness. No reranker or prompt optimization was added.
- **Deployment:** one Community Cloud service reuses Streamlit, the checked-in index and
  existing GitHub Actions protected-main gate. See the [deployment record](deployed.md).
- **Safety:** synthetic records only; search excerpts are candidate evidence, not proof of
  eligibility. Missing balances differ from zero; current work state does not authorize a new
  arrangement. Caller context is not authentication. Unsupported actions are refused; email
  proposals remain unsent and require explicit confirmation. No record mutation or approval.
- **Compliance scope:** `check_policy_compliance` only checks the supported out-of-state
  prior-approval question using caller-provided, unverified facts. The production evidence
  pin is inactive; missing/unreviewed evidence yields `indeterminate`, not authorization.
- **Privacy:** operational traces retain allowlisted events, tool/argument names, safe outcomes
  and source IDs, not hidden reasoning or raw employee records. Provider diagnostics retain
  safe categories/status/allowlisted codes, not raw request/response bodies or credentials.

## Demonstration workflows

These are expected, not guaranteed model call sequences. Order may vary. Older F004 tests
use separate `TEST-*` fixtures; production synthetic demonstrations use **SYN-001**, with
80 available PTO hours as of **2026-01-01** and PTO source **HR-002**.

### PTO guidance

Supply `SYN-001` in the UI employee-ID field, then use the existing PTO sample prompt:
request 8 hours on 2026-02-01 and ask for balance and policy steps.

```text
lookup_employee_profile(employee_id)
check_pto_balance(employee_id)
search_policy_documents(question, k=5)
-> answer citing policy and actual balance/as_of; no approval/submission claim
```

Names in message text are not authoritative context. A missing PTO record is not a zero
balance. A draft is a separate, explicitly requested interaction and is never sent; it is
not a mandatory fourth call beyond the default three-call bound.

### Remote-work guidance or human review

With synthetic employee context, use the existing six-week out-of-state remote-work sample.
Distinguish general policy guidance from deciding a specific employee's eligibility.

```text
lookup_employee_profile(employee_id)
search_policy_documents(question, k=5)
[check_policy_compliance(check_id="out_of_state_prior_approval",
                         approval_facts=<caller-provided facts>) only if applicable]
-> cited guidance; unresolved approval/security gaps -> human review, not authorization
```

Do not invent approval dates or a device security posture. Compliance is not applicable to
international work. A generic policy question without employee context should not be graded
as answered merely because it returned an employee-ID clarification: this was the observed
hosted EVAL-003 limitation.

The [F004 contract](../specs/004-hr-agentic-workflows/contracts/workflows.md) and deterministic
tests cover both compositions. They do not prove the live provider follows them. Both
complete deployed demonstrations remain a manual evidence gap.

## Evaluation method and actual results

The [historical closure report](../evaluation/final-report.md) preserves the initial record; original
results are preserved. Twenty fixed cases and ten latency flags reuse `AgentSession` and
the Groq provider. The runner appends per-case output, stops on provider/operational error,
does not retry cases, and refuses to overwrite an existing suite/diagnostic result.

Correctness, groundedness, citations and safety require rubric review; tool-name constraints
and response-status matching are narrower automated proxies. An `outcome=completed` row is
not proof that its answer is correct. The Ubuntu suite has two completed ungraded answers,
one HTTP 400 `tool_use_failed`, and seventeen unattempted cases. The later isolated hosted
EVAL-003 response completed as clarification but failed its tool/workflow checks.

Only two designated suite latency samples completed, so the required 10-20-sample p50/p95
are unavailable. Timing covers agent/provider/MCP work, not browser rendering; session-first
is not a measured host cold start. Retrieval-only comparison: k=3 16/24 (66.7%), k=5 17/24
(70.8%) expected-source-label recall. No more live evaluations were run during closure.

The subsequent [bounded completion report](../evaluation/completion-report.md) supersedes
that historical snapshot: 7/20 canonical Ubuntu primary cases attempted, 3 answers graded,
4 provider failures, no operational failures and 13 unattempted. The authorized continuation
stopped at three provider failures without a second run.

[Offline](../evaluation/offline-scores.json) and [continuation](../evaluation/completion-scores.json)
review yields grounded claims 14/18, supporting section references 10/20, tool constraints 3/3,
workflow completion 1/3, full correctness 0/3 and observable safety 3/3. Clarification accuracy
is N/A (zero eligible completed primary responses). These source-backed assistant judgments
are not independent human acceptance. Only one new timing-panel response qualified;
percentiles remain unavailable. Raw grades/results, diagnostics and the retrieval comparison
are preserved separately; no provider/model/tool/architecture change was made.

## References and attribution

These are dependency/design references, not claims that upstream documentation validates
this implementation:

- [MCP specification](https://modelcontextprotocol.io/specification)
- [Groq tool-use documentation](https://console.groq.com/docs/tool-use)
- [Streamlit documentation](https://docs.streamlit.io/)
- [Sentence Transformers documentation](https://www.sbert.net/)
- [all-MiniLM-L6-v2 model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
- [FAISS project](https://github.com/facebookresearch/faiss)
- [GitHub protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches)

The [assignment and traceability matrix](requirements/traceability.md) remain authoritative
for project obligations; documented limitations do not remove requirements.
