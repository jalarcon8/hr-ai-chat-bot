# Quickstart and Validation: MCP Tool Integration

The implemented client starts the implemented FastMCP server over stdio. The server delegates
policy retrieval to F001 and employee/PTO lookups to fictional JSON data. See the
[tool contract](contracts/mcp-tools.md) for all six descriptions, input schemas, results,
errors, tracing, and compliance rules. Agent orchestration is future F003 work.

## Standard setup prerequisites

- Python 3.11 and a clean virtual environment.
- An F001 index built from the fictional `corpus/`, with the same embedding model configured
  for search. The initial local model download may require network access; no provider key is
  needed for F002's deterministic drafting or routine tests.
- F002's synthetic employee and PTO JSON files. A reviewed document-level baseline for
  HR-004 and HR-001 is needed only for definitive production compliance results; review and
  activation are pending and the old section-only baseline is insufficient.
- `mcp==1.28.1` is declared in the project dependencies.

From the project root on Windows:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\python -m ruff check .
.\.venv\Scripts\python -m pytest -q
```

On Linux, use `python3.11 -m venv .venv` and `.venv/bin/python` for the corresponding
commands. Follow the [F001 setup](../001-HR_Policy_RAG/quickstart.md) to build the index;
do not use real employee information.

## Fictional employee scenarios

The local JSON data contains fictional examples only:

| Employee ID | PTO scenario |
|---|---|
| `SYN-001` | 80 hours |
| `SYN-002` | No PTO record |
| `SYN-003` | Zero hours |

An unlisted employee ID tests an unknown employee. Balances are static examples as of
2026-01-01, not current employee data. The separate test fixtures use `TEST-` IDs.

## Credential-free local/test configuration

With the dependencies already installed, run the real stdio client and server with the
test-only deterministic embedder, isolated F001 snapshot, fictional records, local trace sink,
and synthetic baseline and pin:

Run the following in a **new PowerShell process** from the project root. It removes all inherited
environment variables except the listed OS execution variables for that process only and sets
an empty temporary home and provider configuration. It does not change the user's persistent
environment. Do not copy credential files into the temporary directory.

```powershell
$python = (Resolve-Path '.\.venv\Scripts\python.exe').Path
$sandbox = Join-Path $env:TEMP ('hr-mcp-isolated-' + [guid]::NewGuid().ToString())
New-Item -ItemType Directory -Path $sandbox | Out-Null
$keep = @('PATH', 'PATHEXT', 'SYSTEMROOT', 'WINDIR', 'SYSTEMDRIVE', 'COMSPEC')
Get-ChildItem Env: | Where-Object { $keep -notcontains $_.Name } | ForEach-Object {
    Remove-Item -LiteralPath ('Env:' + $_.Name)
}
$env:HOME = $sandbox
$env:USERPROFILE = $sandbox
$env:APPDATA = $sandbox
$env:LOCALAPPDATA = $sandbox
$env:TEMP = $sandbox
$env:TMP = $sandbox
$env:HF_HOME = Join-Path $sandbox 'huggingface'
$env:XDG_CONFIG_HOME = Join-Path $sandbox 'config'
& $python -m pytest -q --basetemp (Join-Path $sandbox 'pytest') tests\test_mcp_stdio.py::test_six_real_tools_and_source_metadata tests\test_mcp_stdio.py::test_compliance_outcomes_and_citations_over_stdio tests\test_mcp_integration.py::test_default_server_uses_configured_snapshot_and_fails_closed
$result = $LASTEXITCODE
Remove-Item -LiteralPath $sandbox -Recurse -Force
exit $result
```

The parametrized tests use both the provided and raw MCP clients. The fixture server blocks
non-loopback socket connections (Windows asyncio requires loopback for internal wakeups) and
injects a deterministic embedder instead of a hosted service or live model. No model download,
hosted runtime or production baseline is needed. The test
baseline is injected only by `tests/fixtures/mcp/integration_server.py` and cannot activate
production. Local packages or unauthenticated public package sources are permitted for setup.
Record the environment isolation and dependency review as well as execution results before
claiming SC-009; this local test is not deployed free-tier verification. F006 owns deployed
resource, quota, runtime-limit, cost and integrated deployment verification.

## Protocol smoke test

The client launches the server over stdio. It exposes a `--discover` command and a
`--example TOOL_NAME` command using documented synthetic examples:

```powershell
.\.venv\Scripts\python -m hr_mcp.client --discover
.\.venv\Scripts\python -m hr_mcp.client --example search_policy_documents
.\.venv\Scripts\python -m hr_mcp.client --example get_policy_section
.\.venv\Scripts\python -m hr_mcp.client --example lookup_employee_profile
.\.venv\Scripts\python -m hr_mcp.client --example check_pto_balance
.\.venv\Scripts\python -m hr_mcp.client --example check_policy_compliance
.\.venv\Scripts\python -m hr_mcp.client --example draft_hr_email
```

The server reads the existing `HR_RAG_*` settings listed in the README and uses the
project-root `data/employees.json` and `data/pto.json` files. The client forwards these
nonsecret RAG settings to its subprocess; build the F001 index before calling policy tools.
The embedding model loads only when policy search is invoked. Production compliance remains
indeterminate until the independently reviewed full-document baseline is activated.
The client uses a five-minute per-call timeout, configurable through `MCPClient(call_timeout=...)`.

The built-in examples send the following arguments; output objects are in `structuredContent`.
Policy outcomes assume a successfully built, matching F001 index.

| Tool | Example arguments | Expected outcome |
|---|---|---|
| `search_policy_documents` | `{"question":"What approval is required before out-of-state travel?"}` | `found` candidate evidence, or `not_found` on an empty retrieval |
| `get_policy_section` | `{"document_id":"HR-004","section":"2.2 Working from another state"}` | `found` indexed excerpts and generation ID |
| `lookup_employee_profile` | `{"employee_id":"SYN-001"}` | `found`, employee Alex Example |
| `check_pto_balance` | `{"employee_id":"SYN-001"}` | `found`, 80 available hours |
| `check_policy_compliance` | `{"check_id":"out_of_state_prior_approval"}` | `indeterminate`, with limitations; the production pin is inactive and no facts are supplied |
| `draft_hr_email` | `{"recipient_name":"Alex Example","purpose":"PTO request"}` | `found`, draft subject `PTO request` and body |

Discovery must expose exactly the six agreed names, descriptions, and schemas. Each example
must traverse MCP and return the outcome in [mcp-tools.md](contracts/mcp-tools.md). Tracing produces an inspectable persisted redacted trace when the configured sink is
operational. Configure the
trace sink per the implementation README; protocol stdout must not contain trace messages. A
trace persistence failure is an operational error, not a successful tool result, and need not
itself have a persisted trace. A definitive compliance result requires the reviewed HR-004 section
in the active snapshot, both complete governing source documents bound to that snapshot,
sufficient supplied facts, and a valid approved document-level baseline matching the active pin.
Missing or changed governing
documents, insufficient indexed citations, or a missing, invalid, unreviewed, or mismatched
baseline give `indeterminate`. Governing policy changes require a new version and explicit
review before the active pin is updated; see [research.md](research.md).

## Acceptance checks

The QR-027 documentation check (T032) follows this setup and protocol smoke test against the
implemented client and server: compare all six discovered names, descriptions and input schemas
with the tool contract, inspect the architecture and transport description against the code, and
invoke the documented synthetic `lookup_employee_profile` example over MCP. Record the platform,
commands and results or unavailable prerequisites; do not treat an unrun check as passed.

1. Exercise every tool via an actual stdio client/server subprocess using deterministic
   embedders and synthetic fixture data; no live model or provider credentials are needed.
2. Verify search candidates, including unrelated results, are not presented as supported
   answers; verify exact section lookup, missing section, citations and generation ID.
3. Verify known and unknown employees, an employee missing PTO, and malformed/unavailable
   data. Missing records are distinct from broken dependencies.
4. Through MCP, verify timely written People Operations approval, known absence, late and
   equal-time approval, verbal approval, wrong authority, missing and unknown facts, timezone
   offsets and invalid timestamps. For unknown status with each disqualifying candidate fact,
   verify `noncompliant` when the caller asserts no other approval and `indeterminate` when a
   separate qualifying approval remains possible. Verify limitations disclose that caller
   assertions are unauthenticated and the result is not an overall eligibility decision.
   Verify unchanged and changed governing
   documents, including a new subsection with an unchanged original chunk; an unrelated document
   change; missing or unverifiable sources and indexed citations; missing, malformed, unreviewed,
   and mismatched baselines; newline and Unicode normalization; corrupt index; unsupported check;
   and no broad eligibility assertion.
5. Verify invalid types, blank input, nonpositive and boolean `k`, unknown arguments, unknown
   tools, and interrupted server connections. Through standard and raw MCP clients, verify
   structured classifications for invalid arguments, dependency failures, and unexpected
   exceptions without parsing error text. Verify ambiguous errors are reported by the provided
   client as `UNCLASSIFIED_ERROR` with no asserted origin, regardless of message text or missing
   trace information. With an operational sink, inspect persisted traces for each invocation
   reaching the server adapter and confirm secrets, raw questions, full
   employee records, and draft text are absent. Verify malformed protocol requests rejected by
   the SDK before dispatch do not reach the adapter or require a server execution trace; the
   provided client separately traces protocol failures it observes. Simulate trace persistence
   failure and verify an explicit operational error and no successful tool result without
   requiring a trace of the failed write.
6. Confirm draft generation is deterministic and does not send, persist, mutate, or call
   external services. Repeat the suite on Windows and Linux and record actual results.

## Recorded verification

### Local synthetic execution (T033 / SC-009)

Windows 11 Pro 10.0.26200, Python 3.11.9, existing `.venv`: the exact isolation script above
passed **5 tests in 11.66s**. The first run with a stricter socket guard failed because Windows
asyncio uses loopback sockets; the fixture guard was corrected to allow loopback and the
documented command was rerun successfully. The guard blocks non-loopback connections in the
synthetic server; it is not an OS-level firewall and does not block loopback services.

The script allows only OS execution variables to survive from the original environment, then
sets isolated home and cache paths. Thus `GROQ_API_KEY`, `OPENAI_API_KEY`,
`ANTHROPIC_API_KEY`, `HF_TOKEN`, `HUGGING_FACE_HUB_TOKEN`, `AWS_ACCESS_KEY_ID`,
`AWS_SECRET_ACCESS_KEY`, `AZURE_OPENAI_API_KEY`, and `GOOGLE_APPLICATION_CREDENTIALS` are
absent without recording their values. The SDK merges its Windows environment allowlist with
explicit server settings; the isolated `USERPROFILE`, `APPDATA`, `LOCALAPPDATA`, and `TEMP`
are inherited. No existing home/provider files were copied into the empty directory.

The first selector discovers exactly six tools through both clients and verifies these real
handler calls:

| Tool | Synthetic input | Actual result |
|---|---|---|
| `search_policy_documents` | question `travel approval` | `found` candidate evidence with source and generation metadata |
| `get_policy_section` | HR-004, `2.2 Out-of-State Work` | `found`, exact indexed citations |
| `lookup_employee_profile` | `TEST-001` | `found`, Taylor Fixture |
| `check_pto_balance` | `TEST-001` | `found`, matching PTO record |
| `check_policy_compliance` | timely written People Operations approval and synthetic pin | `found` with verified citations; the second selector additionally verifies compliant, noncompliant and indeterminate outcomes |
| `draft_hr_email` | Taylor, PTO request | `found`, draft subject `PTO request` |

The third selector uses the default production server with an isolated F001 snapshot and
confirms a favorable approval assertion still yields `indeterminate` and empty evidence.
These fixtures and their pin are not production approval. The provided-client CLI's separate
standard-configuration discovery and employee example also passed; see T032 below.

Dependency review: `pyproject.toml` and `requirements.txt` declare local FAISS, NumPy, MCP,
Groq and Sentence Transformers; `.[dev]` adds pytest and Ruff. `python -m pip check` returned
`No broken requirements found.` The installed Windows runtime/dev dependency graph was
enumerated from local `importlib.metadata` with PEP 508 markers and extras: annotated-types,
anyio, attrs, certifi, cffi, charset-normalizer, click, cloudpickle, colorama, cryptography,
distro, faiss-cpu, filelock, fsspec, groq, h11, httpcore, httpx, httpx-sse, huggingface-hub,
idna, iniconfig, jinja2, joblib, jsonschema, jsonschema-specifications, markupsafe, mcp,
mpmath, narwhals, networkx, numpy, packaging, pillow, pluggy, pycparser, pydantic,
pydantic-core, pydantic-settings, pyjwt, pytest, python-dotenv, python-multipart, pywin32,
pyyaml, referencing, regex, requests, rpds-py, ruff, safetensors, scikit-learn, scipy,
sentence-transformers, setuptools, sniffio, sse-starlette, starlette, sympy, threadpoolctl,
tokenizers, torch, tqdm, transformers, typing-extensions, typing-inspection, urllib3 and
uvicorn. All 68 reachable distributions were installed locally under `.venv/Lib/site-packages`;
their original package-source provenance was not recorded in `direct_url.json` and is
unverified. No missing or incompatible installed requirements were found. No external service
or credential is mandatory for the documented synthetic run. Live Groq generation is separate
and requires `GROQ_API_KEY`; the standard embedding model may need a download. This is not a
clean-install or deployed cost, resource, quota or availability verification.

### Earlier documentation discovery

On the same Windows interpreter, with `HR_MCP_TRACE_PATH` set to an isolated local JSONL file,
these commands exited 0 from the project root:

```powershell
.\.venv\Scripts\python -m hr_mcp.client --discover
.\.venv\Scripts\python -m hr_mcp.client --example lookup_employee_profile
```

Live discovery matched all six contract names, published descriptions, input property types,
required fields, defaults, enums and nested facts constraints, including rejection of additional
properties. The example returned `isError: false`, `status: found` and the documented SYN-001
profile. The README and this guide describe the actual stdio client/server, F001 and JSON-data
connections; synthetic and standard configurations are distinct. A non-fatal Pydantic
`IncompleteFieldDefinitionWarning` appeared on stderr. Linux, clean installation, and live
embedding/model execution were not checked by this documentation review. The documented clean
standard setup and F001 index prerequisite were not reproduced in that earlier check. The
subsequent clean-environment check below addresses those T032 prerequisites.

### FR-009 and error/trace evidence

The Windows full-suite command `.\.venv\Scripts\python -m pytest -q` exercises the following
test identifiers with both provided and raw clients where parametrized. All passed in the full
run; no tests were skipped. These are local results, not observed CI or Linux results.

| Matrix row | Executed evidence |
|---|---|
| Search | `test_mcp_stdio.py::test_six_real_tools_and_source_metadata`; `test_mcp_errors.py::test_six_tool_invalid_and_domain_matrix` and `::test_operational_and_adapter_failures` |
| Section lookup | The same three tests; missing section, invalid identifiers and unavailable index are checked |
| Employee lookup | The same three tests; missing/blank ID, unknown record and unavailable data are checked |
| PTO lookup | The same three tests; missing/blank ID, missing employee/PTO and unavailable data are checked |
| Compliance | Those tests plus `test_mcp_stdio.py::test_compliance_outcomes_and_citations_over_stdio`, `::test_added_subsection_invalidates_unchanged_citation`, `::test_changed_governing_document_is_indeterminate`, and `test_mcp_integration.py::test_default_server_uses_configured_snapshot_and_fails_closed` |
| Email draft | The first three tests; invalid inputs and injected unexpected execution failure are checked, and `test_mcp_draft.py::test_draft_is_deterministic_and_does_not_use_network` checks no external action |

`test_mcp_errors.py::test_client_does_not_infer_ambiguous_error_origin` verifies ambiguous
errors remain unclassified. `test_mcp_trace.py` exercises persisted redacted success,
validation and failure events, client failures, pre-dispatch protocol rejection, and fail-closed
server/client sink failures. Direct handler tests also cover malformed synthetic data and
additional baseline and citation cases. Fixture-driven live MCP tests cover unavailable data;
malformed data is covered directly by `test_mcp_data.py::test_invalid_data_is_operational_error`,
not independently injected through MCP.

### Requirements and repository review (T031; incomplete)

| Feature requirement | Implementation and verification | Status / dependency |
|---|---|---|
| FR-001-003 | Server registrations and client; stdio discovery and six-call tests T018-T021, T032 | Local protocol behavior verified |
| FR-004, FR-004a | F001 adapters; policy and stdio tests T014-T015, T020-T021 | Candidate evidence and source metadata locally verified |
| FR-002a-002d | Compliance, section and draft handlers and tests T011-T021 | Synthetic behavior verified; definitive production compliance blocked on T016 review/activation |
| FR-005 | Fictional JSON and fixture tests T004, T013, T020-T021 | Locally verified; files untracked |
| FR-006-007 | Server/client adapter and traces; T022-T027 tests above | Locally verified, with SDK pre-dispatch boundary and sink-failure limits |
| FR-008 | Read-only handlers and no-send draft tests T013-T021 | Locally verified |
| FR-009 | Six-tool matrix and trace evidence above, T020-T027 | Local matrix passed; malformed data through MCP is not separately demonstrated |
| FR-010 | README, quickstart and contract; T028/T032 live review | Windows clean-setup discovery and documented employee example verified; Linux not checked |
| FR-011 | T033 isolated test and dependency review | Local synthetic configuration verified; deployed compatibility remains F006 |
| FR-012 | File inventory below, T031 | Blocked: untracked artifacts and absent production v2 baseline |

Recommend updating project-wide QR-002 and QR-023-025 with local evidence, QR-027 with the
Windows documentation review, and QR-052 with this **partial** inventory after review;
do not treat these as project-wide final verification. QR-020-022, QR-026, QR-038 and deployment,
cost and submission acceptance retain their assigned F003-F006 dependencies. T016's independent
production approval, T030's both-platform acceptance and T031/SC-008 remain open. No governance
status has been changed.

#### Per-file presence and tracking inventory

Branch `002-mcp-tool-integration`, HEAD `a05fb2fe8b7b6c47e6016a46d94f38469b19d07c`;
no staged changes. The README, workflow, manifests, contract, quickstart and task list are
tracked with unstaged edits; other pre-existing tracked changes also exist. `git status --short
--untracked-files=all`, `Test-Path -PathType Leaf`, and `git ls-files --error-unmatch -- <path>`
were used for each item. Tracking does not establish a commit or submission. Runtime-generated
indexes, caches and traces are excluded. The pin configuration is `src/hr_mcp/tools.py`,
present but untracked, and `_ACTIVE_BASELINE_PIN` is `None`.

```text
present, untracked: src/hr_mcp/__init__.py
present, untracked: src/hr_mcp/server.py
present, untracked: src/hr_mcp/client.py
present, untracked: src/hr_mcp/policy.py
present, untracked: src/hr_mcp/data.py
present, untracked: src/hr_mcp/tools.py
present, untracked: src/hr_mcp/models.py
present, untracked: src/hr_mcp/trace.py
present, untracked: data/employees.json
present, untracked: data/pto.json
missing, untracked: data/compliance-baselines/out-of-state-prior-approval-v2.json
present, untracked: tests/fixtures/mcp/__init__.py
present, untracked: tests/fixtures/mcp/baseline-pin.json
present, untracked: tests/fixtures/mcp/baseline.json
present, untracked: tests/fixtures/mcp/doubles.py
present, untracked: tests/fixtures/mcp/employees.json
present, untracked: tests/fixtures/mcp/harness.py
present, untracked: tests/fixtures/mcp/integration_server.py
present, untracked: tests/fixtures/mcp/policies/hr-001.md
present, untracked: tests/fixtures/mcp/policies/hr-004.md
present, untracked: tests/fixtures/mcp/protocol_server.py
present, untracked: tests/fixtures/mcp/pto.json
present, untracked: tests/fixtures/mcp/variants/changed-hr-004.md
present, untracked: tests/fixtures/mcp/variants/missing-governing/hr-004.md
present, untracked: tests/test_mcp_compliance.py
present, untracked: tests/test_mcp_data.py
present, untracked: tests/test_mcp_discovery.py
present, untracked: tests/test_mcp_draft.py
present, untracked: tests/test_mcp_errors.py
present, untracked: tests/test_mcp_fixtures.py
present, untracked: tests/test_mcp_integration.py
present, untracked: tests/test_mcp_models.py
present, untracked: tests/test_mcp_policy.py
present, untracked: tests/test_mcp_stdio.py
present, untracked: tests/test_mcp_trace.py
present, tracked: src/hr_rag/__init__.py
present, tracked: src/hr_rag/answers.py
present, tracked: src/hr_rag/config.py
present, tracked: src/hr_rag/documents.py
present, tracked: src/hr_rag/index.py
present, tracked: src/hr_rag/models.py
present, tracked: tests/fixtures/doubles.py
present, tracked: README.md
present, tracked: specs/002-mcp-tool-integration/spec.md
present, tracked: specs/002-mcp-tool-integration/plan.md
present, tracked: specs/002-mcp-tool-integration/research.md
present, tracked: specs/002-mcp-tool-integration/data-model.md
present, tracked: specs/002-mcp-tool-integration/quickstart.md
present, tracked: specs/002-mcp-tool-integration/tasks.md
present, tracked: specs/002-mcp-tool-integration/contracts/mcp-tools.md
present, tracked: pyproject.toml
present, tracked: requirements.txt
present, tracked: .github/workflows/ci.yml
```

At the time of this inventory, no staging had been performed. The missing production baseline
and then-untracked required items prevented SC-008 from passing. Feature 006 owns final
project-wide repository and submission verification.

### Clean Windows acceptance and CI review, 2026-11-15

On Windows 11 Pro, Python 3.11.9, a new virtual environment with
`include-system-site-packages = false` was created for a local project snapshot. The snapshot
kept generated installation metadata and indexes out of the working tree; its virtual
environment was named `venv` rather than `.venv`. Before installation,
`venv\Scripts\python -m pytest --version` failed with `No module named pytest`. From the
snapshot root, the following commands then ran:

```powershell
python -m venv venv
.\venv\Scripts\python -m pip install --isolated --no-input --index-url https://pypi.org/simple -e ".[dev]"
.\venv\Scripts\python -m pip check
.\venv\Scripts\python -m ruff check .
.\venv\Scripts\python -m pytest -q
```

The install and `pip check` succeeded. After synchronizing the timeout fix and its tests into
the snapshot, Ruff passed and pytest reported **306 passed, 0 skipped** in 66.44s. The
credential-isolated script above was rerun with the snapshot's `venv\Scripts\python.exe`
substituted for `.venv\Scripts\python.exe`: **5 passed in 11.27s**. A later identical isolated
run after the timeout fix also exited 0.

Using the locally cached standard Sentence Transformers model, the documented F001
`build_index` example succeeded offline with 12 corpus documents and 298 chunks. The real
client's `--discover` command returned the six documented names, descriptions and schemas;
`--example lookup_employee_profile` returned the documented synthetic result. The section,
PTO, bounded-compliance and draft examples also returned their expected structures; the
compliance result remained `indeterminate`. This completes the Windows T032/SC-007 review.
The standard `--example search_policy_documents` call did **not** complete: it reached the
five-minute client timeout while the server was loading the model. A separate local-model
probe measured 121.44 seconds in model initialization before its 120-second timeout; the
cause of the variable initialization time is not established. Synthetic stdio search passed,
but the real-model CLI search remains unverified. A timeout previously escaped the CLI wrapped
in an AnyIO exception group; the client cleanup now preserves the structured client error,
with regression tests for asynchronous and blocking handlers and unexpected cleanup failures.

Linux and Windows/Linux CI for these changes remain unverified. No WSL distribution or
container runtime was available. The [older Actions run](https://github.com/jalarcon8/hr-ai-chat-bot/actions/runs/43384875313)
passed on Ubuntu for main commit `4224c5e4656ceefc32d374bd8627a42a29c5963f`; it predates
these uncommitted changes and is not their acceptance evidence. The current workflow triggers
on pushes or pull requests targeting `main`; after an authorized commit and push or pull request,
inspect both matrix jobs in Actions. This feature does not verify deployed free-tier limits.

### Approved staging set

The following 42 existing Feature 002 artifacts were approved and staged on 2026-11-15:

```text
.github/workflows/ci.yml
.gitignore
README.md
pyproject.toml
requirements.txt
specs/002-mcp-tool-integration/contracts/mcp-tools.md
specs/002-mcp-tool-integration/quickstart.md
specs/002-mcp-tool-integration/tasks.md
data/employees.json
data/pto.json
src/hr_mcp/__init__.py
src/hr_mcp/client.py
src/hr_mcp/data.py
src/hr_mcp/models.py
src/hr_mcp/policy.py
src/hr_mcp/server.py
src/hr_mcp/tools.py
src/hr_mcp/trace.py
tests/fixtures/mcp/__init__.py
tests/fixtures/mcp/baseline-pin.json
tests/fixtures/mcp/baseline.json
tests/fixtures/mcp/doubles.py
tests/fixtures/mcp/employees.json
tests/fixtures/mcp/harness.py
tests/fixtures/mcp/integration_server.py
tests/fixtures/mcp/policies/hr-001.md
tests/fixtures/mcp/policies/hr-004.md
tests/fixtures/mcp/protocol_server.py
tests/fixtures/mcp/pto.json
tests/fixtures/mcp/variants/changed-hr-004.md
tests/fixtures/mcp/variants/missing-governing/hr-004.md
tests/test_mcp_compliance.py
tests/test_mcp_data.py
tests/test_mcp_discovery.py
tests/test_mcp_draft.py
tests/test_mcp_errors.py
tests/test_mcp_fixtures.py
tests/test_mcp_integration.py
tests/test_mcp_models.py
tests/test_mcp_policy.py
tests/test_mcp_stdio.py
tests/test_mcp_trace.py
```

Generated `src/hr_policy_rag.egg-info/` changes remain unstaged; environments, indexes, caches,
traces, credentials and editor state were excluded. A scoped secret/private-data scan found only synthetic test
credential-pattern literals; such a scan cannot prove the absence of sensitive material.
The required production v2 baseline is absent and must not be invented. Even after the listed
artifacts are tracked, T031/SC-008 remain blocked on that independently approved baseline.
Post-staging `git diff --cached --name-only`, `Test-Path -PathType Leaf`, and
`git ls-files --error-unmatch -- <path>` confirmed all 42 staged paths exist and are tracked;
the additional F001 sources, shared fixture and feature planning documents listed in the
earlier inventory remain tracked. The v2 baseline is still missing and untracked, and the
production pin is still `None`. Staging is not a commit or submission.
