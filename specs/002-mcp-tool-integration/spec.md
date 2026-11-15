# Feature Specification: MCP Tool Integration

**Feature Branch**: `002-mcp-tool-integration`

**Created**: 2026-11-11

**Status**: Draft - ready for implementation

**Input**: Provide a FastMCP server exposing six proposed tools, synthetic employee and PTO
data, and an MCP client that discovers and invokes the tools. Wrap Feature 001's RAG
capabilities instead of building another retrieval system.

## Clarifications

### Session 2026-11-13

- Q: Which six tools should Feature 002 expose? → A: Use the six tools named in the feature roadmap.
- Q: How should the policy compliance tool reach a conclusion? → A: Evaluate a limited, documented set of checks using synthetic facts and cited policy evidence; return indeterminate when facts or evidence are insufficient.
- Q: What information should tool-call traces retain about arguments and results? → A: Record allowlisted concise summaries and omit raw questions, email drafts, and full records by default.
- Q: What should the policy section lookup return when a caller names a document and section? → A: Return matching indexed excerpts with source metadata; report an absent document or section.
- Q: How should the HR email drafting tool create a draft? → A: Fill a deterministic template using supplied synthetic details and return the draft without sending or storing it.

### Session 2026-11-14

- Q: Which policy check should the compliance tool support initially? → A: Check written People Operations approval before travel for work in another US state; do not assess overall eligibility.
- Q: How should callers distinguish a valid no-result from a failed tool call? → A: Use structured `found`, `not_found`, and `indeterminate` outcomes; invalid inputs and operational failures are MCP tool errors, while transport, connectivity, and discovery failures are client-side errors.
- Q: Where should the compliance tool obtain the facts it checks? → A: The caller identifies the supported check and supplies synthetic facts; insufficient facts are indeterminate, and unsupported checks are invalid.
- Q: What source details should every returned policy excerpt include? → A: Include document ID, title, optional section, exact excerpt, chunk ID, and index generation ID; include a retrieval score for ranked search results only.
- Q: What minimum inputs should each of the six tools require? → A: Require the specified question, identifiers, or drafting details for each tool; use a positive search `k` defaulting to 5 and optional structured approval facts for compliance.
- Q: How should the policy search tool describe top-k results whose relevance has not been established? → A: Return nonempty retrieval results as candidate evidence with `found`; use `not_found` only for a successful empty retrieval.

### Session 2026-11-14: Approval timing correction

- Q: What establishes the approval requirement? → A: Caller-supplied synthetic facts must
  establish written People Operations approval strictly before travel; a generic approval
  status alone is insufficient. Facts are not independently authenticated.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Discover and invoke MCP tools (Priority: P1)

As an AI agent, I want to discover available tools and invoke them through MCP so that I can
use a consistent interface to obtain policy evidence and synthetic employee information.

**Why this priority**: Tool discovery and actual protocol invocation are the foundation of
the integration.

**Independent Test**: Start the server, connect a real MCP client, discover the published
tools, and invoke each with valid synthetic test inputs.

**Acceptance Scenarios**:

1. **Given** a running server, **When** an MCP client discovers tools, **Then** it receives
   the six agreed tool names, descriptions, and input schemas.
2. **Given** valid inputs for each tool, **When** the client calls each through MCP, **Then**
   each returns the corresponding result without bypassing the MCP interface.
3. **Given** the server is unavailable, **When** a client attempts discovery or invocation,
   **Then** the failure is surfaced to the caller rather than reported as success.

---

### User Story 2 - Retrieve policy evidence and employee data (Priority: P1)

As an AI agent, I want policy evidence and synthetic employee and PTO information so that
later HR workflows can use traceable sources and structured data.

**Why this priority**: Both policy evidence and structured mock data are required for the
assignment's agent workflows.

**Independent Test**: Through MCP, call a policy evidence tool with an indexed synthetic
policy and a structured-data tool with a known synthetic employee.

**Acceptance Scenarios**:

1. **Given** Feature 001's indexed policy corpus, **When** a valid policy evidence tool call
   is made, **Then** the result is derived from Feature 001 and includes source identifiers,
   section when available, and supporting excerpts.
2. **Given** known synthetic employee and PTO records, **When** the appropriate tools are
   called through MCP, **Then** their returned information matches those records.
3. **Given** policy evidence is absent or an employee identifier is unknown, **When** the
   appropriate tool is called, **Then** the result clearly identifies the absence and does
   not invent evidence or employee information.

---

### User Story 3 - Diagnose and safely handle tool calls (Priority: P2)

As a developer, I want validated inputs, visible failures, and usable call traces so that I can
verify agent tool use and diagnose problems safely.

**Why this priority**: Traceability and explicit failures are necessary for reliable tool use.

**Independent Test**: Invoke tools with invalid arguments and induce a dependency failure;
inspect the MCP results and recorded, appropriately redacted tool-call trace.

**Acceptance Scenarios**:

1. **Given** invalid, missing, or incorrectly typed arguments, **When** a tool is called,
   **Then** the call fails with an actionable error and does not perform its operation.
2. **Given** Feature 001 or the synthetic data source is unavailable, **When** a dependent
   tool is called, **Then** it reports an operational failure distinct from a valid no-result.
3. **Given** an operational trace sink and a tool invocation that reaches the server's tracing
   boundary, **When** the persisted trace is inspected, **Then** it identifies the tool when
   known, records appropriately redacted inputs and outcome, and excludes secrets and
   unnecessary user input. This includes invalid tool arguments rejected at that boundary.
4. **Given** trace persistence fails, **When** a tool call completes, **Then** the caller
   receives an explicit operational error rather than a successful tool result; a persisted
   trace of that failure is not guaranteed.
5. **Given** a malformed MCP protocol request that the SDK rejects before tool dispatch,
   **When** it cannot reach the server's tracing boundary, **Then** it is handled as a protocol
   failure, not a tool execution failure, and no server tool execution trace is guaranteed.

### Edge Cases

- Tool discovery succeeds but a requested tool name is unavailable: report the missing tool.
- Policy retrieval returns fewer results than requested or no supporting evidence: preserve the
  Feature 001 result without manufacturing sources.
- A requested document or section is absent from the active index: report the absence without
  manufacturing excerpts.
- A known employee has no PTO record: report missing data rather than assuming a zero balance.
- A compliance check lacks necessary facts or supporting policy evidence: return an
  indeterminate result and identify the missing information.
- Malformed or unavailable synthetic data, invalid policy index, and transport failures are
  reported explicitly and are not represented as valid empty results.
- A malformed protocol request rejected by the SDK before tool dispatch is distinct from
  invalid tool arguments received and traced at the server's tracing boundary.
- Trace persistence failure is surfaced as an operational error without exposing credentials or
  unrestricted user text; the failed trace itself need not be persisted.
- Any agreed state-changing tool must affect synthetic data only, require explicit user
  confirmation, and have a documented reversal or reset.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST expose exactly the six agreed tools via a FastMCP server, with
  descriptions and declared input schemas discoverable by an MCP client.
- **FR-002**: The six tools MUST be `search_policy_documents`, `get_policy_section`,
  `lookup_employee_profile`, `check_pto_balance`, `check_policy_compliance`, and
  `draft_hr_email`. Email drafting MUST NOT send an email.
- **FR-002a**: `check_policy_compliance` MUST evaluate a limited, documented set of supported
  checks against synthetic facts and cited policy evidence. It MUST return an indeterminate
  result identifying missing information when necessary facts or evidence are insufficient,
  including a missing, invalid, unreviewed, or mismatched compliance baseline; missing,
  inconsistent, unapproved, or unverifiable baseline approval metadata; or a missing, changed,
  or unverifiable complete governing policy document. A definitive determination MUST verify
  the baseline's approval metadata separately from complete document integrity and retain
  nonempty, verified section-level supporting evidence and citations for both `compliant` and
  `noncompliant` conclusions. An `indeterminate` result MUST explain in `limitations` why a
  definitive determination could not be made; it MAY have empty evidence when verified
  supporting policy evidence is unavailable. Any verified policy evidence used to explain an
  indeterminate result MUST include its corresponding citations. Validation and operational
  errors do not require policy citations. Invalid required citation offsets or inability to
  reconstruct F001's indexed text representation MUST yield `indeterminate`; a missing or
  corrupt index remains an operational error.
  Initially it MUST check whether written People Operations approval was obtained strictly
  before travel for work in another US state, using the applicable remote-work policy evidence.
  The caller MUST identify the supported check and may supply the relevant synthetic approval status,
  authority, format, approval timestamp, travel start timestamp, and whether other approvals
  have been granted, as defined in the contract. The tool MUST NOT independently retrieve
  employee records or represent caller assertions as authenticated.
  Approval status MUST describe whether an approval was granted, independently of its timing,
  format, authority, or policy validity: `approved` means granted, `not_approved` means no
  approval was granted for the trip, and `unknown` means the assessed approval's status is not
  established. A late approval MUST be represented as `approved` with its actual grant timestamp.
  Malformed or contradictory facts, including a grant timestamp supplied with `not_approved`,
  MUST be rejected as invalid input.
  With the required baseline and cited evidence verified, a confirmed written People Operations
  approval strictly before travel yields `compliant` for this requirement. A known absence of
  any approval yields `noncompliant`. A verbal, late, or wrong-authority approval by itself
  does not establish that a separate qualifying approval is absent. If the caller asserts no
  other approval was granted for the trip, such a disqualifier establishes `noncompliant`
  even when the assessed approval's status is unknown. Otherwise, when another qualifying
  approval remains possible and no qualifying approval is established, the result MUST be
  `indeterminate`. Only conclusive facts take precedence over missing information. For an
  upcoming trip, a known absence means the requirement is unmet under the supplied facts, not
  that travel has occurred or that approval cannot be granted later. The result describes only
  the supplied facts and MUST NOT imply that other possible approvals, policy conditions, or
  overall eligibility were independently checked.
  Every result MUST disclose that approval facts are caller assertions and are not independently
  authenticated.
  Unsupported check identifiers are invalid input. A `compliant` or
  `noncompliant` conclusion uses the `found` outcome; an `indeterminate` conclusion uses the
  `indeterminate` outcome. The result covers this requirement only and MUST NOT be presented
  as overall eligibility or approval. Full HR workflow orchestration remains outside this
  feature.
- **FR-002b**: `get_policy_section` MUST accept a document identifier and section and return
  matching excerpts from Feature 001's active index with source metadata. An absent document
  or section MUST be reported as a no-result, not a fabricated excerpt.
- **FR-002c**: `draft_hr_email` MUST fill a deterministic template using supplied synthetic
  details and return the draft without sending or storing it.
- **FR-002d**: The minimum tool inputs and defaults MUST be:
  - `search_policy_documents`: required nonblank `question`; optional positive integer `k`,
    defaulting to 5.
  - `get_policy_section`: required nonblank `document_id` and `section`.
  - `lookup_employee_profile` and `check_pto_balance`: required nonblank `employee_id`.
  - `check_policy_compliance`: required supported `check_id`; optional structured
    `approval_facts` containing status, authority, format, approval timestamp, travel start
    timestamp, and `no_other_approvals` as defined in the contract. Missing or unknown necessary
    facts are indeterminate unless another supplied fact conclusively shows the asserted
    requirement is unmet.
  - `draft_hr_email`: required nonblank `recipient_name` and `purpose`; optional
    `supporting_details`. It MUST NOT send email or perform external actions.
  Required string inputs MUST be nonblank. Invalid types, unsupported check identifiers, and
  invalid values MUST produce MCP tool errors. Unknown employee IDs and absent policy
  documents or sections remain valid `not_found` outcomes.
- **FR-003**: The provided MCP client MUST discover tools and invoke them through MCP over
  stdio rather than directly calling server functions.
- **FR-004**: At least one policy-evidence tool MUST use Feature 001's retrieval capabilities
  and preserve source identifiers, sections when available, and supporting snippets. This
  feature MUST NOT create a second index, embedding pipeline, or retrieval system. Each
  returned policy excerpt, including cited compliance evidence, MUST identify its document ID,
  title, section when present, exact source excerpt, chunk ID, and index generation ID.
  Ranked search results MUST also include their retrieval scores; section lookup and compliance
  evidence MUST NOT present an unranked excerpt as scored. A retrieval score is not proof of
  relevance or support.
- **FR-004a**: `search_policy_documents` MUST preserve Feature 001's top-k retrieval behavior
  and label returned chunks as candidate evidence. A successful nonempty retrieval returns
  `found`, which does not establish relevance, answer sufficiency, or factual support. A
  successful empty retrieval returns `not_found`; invalid input and retrieval failures are
  errors. Feature 003 evaluates relevance and sufficiency during answer synthesis.
- **FR-005**: The system MUST provide clearly identified synthetic employee and PTO data and
  expose access to that data through one or more of the agreed tools. No real HR integration
  or real employee data is permitted.
- **FR-006**: Each tool MUST validate its declared arguments. Unknown tools, invalid inputs,
  missing records, insufficient policy evidence, and operational failures MUST be
  distinguishable to the caller when reliable machine-readable evidence supports that
  distinction; failures MUST NOT appear as successful results. Successful
  results MUST identify `found` when requested information or candidate search evidence is
  returned, `not_found` when a
  completed lookup finds no matching record or evidence, and `indeterminate` when available
  information is insufficient to establish a reliable conclusion. Invalid tool arguments
  reaching dispatch and recognized operational failures MUST produce MCP tool error responses.
  For valid MCP tool-call envelopes targeting the six supported tools, errors MUST have
  machine-readable `INVALID_ARGUMENT`, `OPERATIONAL_ERROR`, or `UNKNOWN_ERROR` classifications
  where the server has reliable evidence. When an error lacks reliable classification metadata, the
  provided client MUST report `UNCLASSIFIED_ERROR` without asserting a pre-dispatch, SDK
  validation, or tool execution origin. Neither error-message text nor missing execution traces
  may be used to infer an error's category or origin. Transport, connectivity, discovery, and
  unknown-tool failures MUST be surfaced as client-side errors by the provided client when
  independently established. Detailed response schemas and mappings are defined in the
  contract.
- **FR-007**: Tool-call traces MUST identify each tool and capture allowlisted, concise
  summaries of inputs, outputs, and errors, such as safe argument metadata, source IDs, and
  outcome. By default, traces MUST omit raw questions, email drafts, full records, secrets, and
  unnecessary user input. The server's tracing boundary is its tool-request dispatch adapter,
  reached after the SDK accepts the MCP request envelope and before application argument
  validation and handler execution. With an operational sink, every tool invocation reaching
  that boundary MUST have a persisted operational trace, including successes, execution errors,
  and invalid arguments, identifying the tool when known. A malformed protocol request is
  exempt from the server tool execution trace guarantee only when the SDK rejects it before
  dispatch and it cannot reach that boundary; it is not a tool execution failure. The provided
  client MUST persist separate traces for client-side transport, connectivity, discovery, and
  unknown-tool errors, and protocol failures it observes, when its sink is operational. If
  required trace persistence fails, the caller MUST receive an explicit operational error; the
  tool MUST NOT report success, and a persisted trace of the persistence failure is not
  guaranteed. Document the boundary, allowlist, sink failure behavior, and how to inspect traces.
- **FR-008**: Tools MUST be read-only by default. Any agreed mutation MUST operate on
  synthetic data only, require explicit user confirmation, and support a documented reversal
  or reset.
- **FR-009**: Automated tests MUST use synthetic fixtures, exercise discovery and invocation
  through an MCP client, cover every agreed tool and its validation and failure cases, and
  replace external services with deterministic test doubles where needed.
- **FR-010**: Documentation MUST cover setup, server and client execution, transport, tool
  schemas, synthetic data, testing, error behavior, and the connection to Feature 001. It MUST
  describe the implemented MCP architecture and the responsibilities and connections of the
  client, server, Feature 001 retrieval, and synthetic data; explain the transport choice; and
  explain how the client discovers tool names and schemas and invokes tools through MCP, with
  reproducible synthetic examples. Document the implemented behavior accurately and distinguish
  the provided client from the future agent integration. Reuse linked documentation rather
  than duplicating schemas or instructions.
- **FR-011**: The server and client MUST support local development and remain compatible with
  a single-service, free-tier deployment; no separately deployed service is required. The
  documented local/test configuration MUST require no paid services, subscriptions,
  infrastructure, or API credentials and MUST support all six tools through MCP using the
  local and deterministic dependencies described in SC-009. Feature 006 owns verification of
  deployed resource usage, provider quotas, runtime limits, operating costs, and integrated
  free-tier compliance; the local check does not establish deployed compliance.
- **FR-012**: Feature 002 MUST verify that its required source, synthetic data and baseline,
  tests and persistent fixtures, MCP contract, documentation, and configuration are present
  at their planned repository locations and tracked by Git. T031 defines the required inventory
  and evidence. This verifies only Feature 002's contribution to QR-052; Feature 006 retains
  final project-wide repository completeness and submission verification.

### Key Entities

- **MCP tool**: A named operation with a description, input schema, and defined result or error.
- **Policy evidence**: A Feature 001 retrieval result with traceable source metadata and snippet.
- **Synthetic employee**: A clearly fictional employee record with a stable identifier.
- **Synthetic PTO record**: A fictional employee's PTO information associated with an identifier.
- **Tool-call trace**: A record of a tool name, appropriately redacted inputs, and result or error.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An MCP client discovers all six agreed tools and successfully invokes each using
  documented valid synthetic examples.
- **SC-002**: At least one invocation returns traceable policy evidence from Feature 001, and
  structured-data invocations return matching synthetic employee and PTO information.
- **SC-003**: Automated checks verify invalid inputs, unknown employee identifiers, missing
  evidence, unavailable dependencies, and unknown tool names without fabricated results.
  Standard and raw MCP clients distinguish the three server classifications for supported
  calls, including invalid tool arguments in SDK-accepted envelopes, dependency failures, and
  unexpected exceptions. The provided client reports ambiguous errors as `UNCLASSIFIED_ERROR`
  without asserting their origin or relying on error text or missing traces; valid outcomes and
  independently established client-side failures remain distinct.
- **SC-004**: With an operational trace sink, every test tool invocation reaching the server's
  tracing boundary produces a persisted, inspectable trace with tool name when known,
  appropriately redacted inputs, and outcome, including successful calls, execution failures,
  and invalid arguments; test secrets are absent from logs. Malformed protocol requests are
  exempt from this server trace guarantee only when the SDK rejects them before dispatch,
  preventing them from reaching the boundary. Observable client-side protocol failures are
  traced separately by the provided client. When trace persistence fails, automated checks
  verify an explicit operational error and no successful tool result, without requiring the
  failed persistence attempt to have a persisted trace.
- **SC-005**: A developer following the documented local setup can run server and client,
  discover the six tools, and reproduce the calls without a real HR system.
- **SC-006**: Automated checks cover the required inputs, search default and `k` validation,
  supported and unsupported compliance checks, valid and missing approval facts, late, verbal,
  and wrong-authority approvals with and without a caller assertion excluding other approvals,
  unknown status, timestamp boundaries, and draft generation without sending or
  external actions. Nonempty search results, including
  potentially unrelated chunks, are labeled candidate evidence rather than confirmed support.
- **SC-007**: A developer using the documented local setup can launch the MCP server through
  the documented client, discover all six tool names, descriptions, and input schemas, and
  invoke at least one documented synthetic example through MCP with the documented result.
  The architecture and transport documentation matches the implemented component connections;
  all six documented tool names, descriptions, and input schemas match live discovery. Record
  the commands and results; an incomplete check remains unverified with its limitation recorded.
- **SC-008**: Every applicable file in T031's Feature 002 repository inventory exists at its
  expected location and is tracked by Git; all required persistent fixture files are likewise
  present and tracked. Record the inventory, commands, actual results and any missing or
  untracked files. A missing, untracked or unverified required item prevents this criterion
  from passing. Git tracking alone does not establish that files are committed or submitted.
- **SC-009**: In the documented local/test configuration, review the required dependencies and
  setup to confirm that no paid service, subscription, infrastructure, or API credential is
  mandatory. With API credentials absent from the test and server environments and accessible
  credential configuration, start the real MCP server through stdio, discover exactly the six
  agreed tools, and successfully invoke each real handler at least once through MCP with valid
  synthetic inputs and contract-conformant
  results. Use the existing deterministic F001 embedder and isolated index, synthetic employee
  and PTO data, local trace sink, and synthetic test-approved compliance baseline; do not activate
  an unreviewed production baseline. Locally installed packages and unauthenticated free public
  package sources are permitted; a live model, hosted runtime service, or credential is not
  required. Record the configuration, dependency review, commands, platform, per-tool results,
  and any limitations. Any missing or failed check prevents SC-009 from passing. This verifies
  local architectural compatibility only, not deployed free-tier compliance; Feature 006 owns
  deployed resource, quota, runtime-limit, cost, and integrated deployment verification.

## Assignment Requirements Traceability

The [assignment](../../docs/requirements/quantic-project-requirements.pdf),
[requirements matrix](../../docs/requirements/traceability.md), and
[roadmap](../../docs/feature-roadmap.md) define the requirements and feature ownership below.
Mappings identify existing specification coverage, not implemented or verified behavior.
Where coverage is partial, the missing portion is stated rather than implied by an FR or SC.

### Feature 002 requirements

| Assignment requirement | Existing FR coverage | Existing SC coverage | Coverage and remaining gap |
|---|---|---|---|
| QR-002: Synthetic structured data | FR-005, FR-009 | SC-001, SC-002 | Synthetic employee and PTO records and their use are covered. |
| QR-023: MCP server and compatible transport | FR-001, FR-003 | SC-001, SC-005 | Six tools are exposed and invoked over MCP stdio. |
| QR-024: At least five tools, including policy evidence and structured data or a mock operation | FR-001, FR-002, FR-004, FR-005 | SC-001, SC-002 | Six tools include both evidence and structured-data operations. |
| QR-025: Representative policy, employee, compliance, and drafting tools | FR-002, FR-002a, FR-002b, FR-002c, FR-002d | SC-001, SC-006 | The six selected tools and their inputs are specified. The assignment's names are examples, not mandatory names. |
| QR-027: MCP architecture, transport, schemas, discovery, and invocation documentation | FR-010 | SC-005, SC-007 | T028 documents the F002 implementation and T032 verifies it against the live server and provided client. Verification remains pending; F003 must document its actual agent-client integration. |
| QR-052: Repository contains developed code, synthetic mock data, and MCP definitions | FR-001, FR-002, FR-005, FR-012 | SC-001, SC-002, SC-008 | Partial: T031 checks the presence and Git tracking of F002's repository contribution and records evidence. Verification is pending; F006 owns project-wide completeness and final submission verification. |

### Supporting and shared requirements

These are owned primarily by other features in the requirements matrix. The mappings describe
only F002's contribution; the remaining assignment-level obligations are not F002 acceptance.

| Assignment requirement | Existing FR coverage | Existing SC coverage | Coverage and remaining gap |
|---|---|---|---|
| QR-003: Free or zero-cost options and modest resources | FR-011 | SC-009 | Partial: T033 verifies the credential-free local/test configuration, dependency review, and all six MCP invocations. This does not measure deployed resources, provider quotas, runtime limits, or costs; F006 owns integrated free-tier deployment verification. |
| QR-004: Reproducible environment and dependency list | FR-010 | SC-005 | Partial: local setup is documented and reproducible; an environment setup and dependency list are not explicitly required or checked. F006 owns final reproducibility. |
| QR-005: README setup, local run, deployment, and evaluation instructions | FR-010 | SC-005 | Partial: F002 setup and local execution are covered; the README location and deployment and evaluation instructions are not specified. F006 owns final documentation. |
| QR-007: Secrets in environment variables and not committed | FR-007 | SC-004 | Partial: secrets must not appear in traces; environment-based secret configuration and repository checks are not specified. F006 owns project-wide verification. |
| QR-018: Agent orchestration and tool selection | FR-003 | SC-001 | Partial: a client invokes tools over MCP; agent intent, selection, and synthesis remain F003. |
| QR-020: Operational traces | FR-007 | SC-004 | Partial: F002 captures redacted tool inputs, outputs, errors, and source IDs; SC-004 does not explicitly check output summaries or source IDs. Agent selection, answer basis, and escalation remain F003. |
| QR-021: Failures, missing information, and clarification | FR-002a, FR-006 | SC-003, SC-006 | Partial: F002 reports failures and insufficient facts; agent clarification remains F003. |
| QR-022: Prevent irreversible actions | FR-002c, FR-008 | SC-006 | Drafting has no external action; conditional mutation safeguards are specified, but no mutation is agreed or tested in this feature. F003/F004 own workflow-level action safety. |
| QR-026: Agent calls MCP tools during execution | FR-003 | SC-001 | Partial: real client calls are required, but agent-driven calls remain F003. |
| QR-034: Single-service deployment and no paid database requirement | FR-011 | SC-009 | Partial: T033 checks that the local/test configuration requires no paid infrastructure or hosted runtime service. Deployed configuration and database cost remain F006 responsibilities. |
| QR-035: Environment-configured URL if MCP is separately deployed | FR-011 | None | Conditional: F002 requires no separate service; URL configuration is not specified. F006 owns this obligation if separate deployment is introduced. |
| QR-037: CI installation, build/start/import check, and tests before deployment | FR-009 | SC-003, SC-006 | Partial: F002 requires automated tests; CI triggers, installation, build/start/import checks, and deployment gating are not specified. F006 owns CI/CD. |
| QR-038: Application-start and MCP discovery or call tests | FR-009 | SC-001 | Partial: MCP discovery and invocation are covered; application-start testing and CI execution remain F006. |
| QR-045: Justification of design choices | FR-010 | None | Partial: F002 documents transport, schemas, and its F001 connection, but does not explicitly require design rationale. F006 owns final design documentation. |
| QR-046: Overall architecture diagram or text | FR-010 | None | Partial: F002 documents component execution, transport, and its F001 connection, but does not require the complete application architecture. F006 owns the integrated description. |
| QR-053: Required submission documentation | FR-010 | SC-005 | Partial: F002 setup, execution, schemas, and testing are documented; the required submission files and their complete contents remain F006. |
| QR-056: Attribution and AI-tooling disclosure | None | None | No explicit F002 FR or SC covers attribution or AI-tooling disclosure; F006 owns submission-level verification. |
| QR-057: Integrated agentic HR system and evaluation | FR-001, FR-003, FR-004, FR-005 | SC-001, SC-002 | Partial: F002 provides MCP tools, evidence, and synthetic data; the integrated agent, grounded answers, and evaluation remain later features. |
| QR-058: Local operation of the agentic system | FR-003, FR-010, FR-011 | SC-005 | Partial: F002's server and client run locally; the complete agentic system remains F006. |

Partial or absent mappings are recorded without transferring their project-level ownership
to this feature.

## Assumptions

- Feature 001's implemented retrieval interface and indexed synthetic corpus are dependencies
  for end-to-end verification.
- Web UI, deployed application, agent orchestration, and full HR workflows are outside this
  increment and remain required for the overall assignment.
- Feature 003's orchestrator is expected to interpret these outcomes, request clarification or
  recommend escalation where needed, obtain available compliance facts via appropriate tools
  or user clarification, and avoid unsupported conclusions; F002 supplies the distinguishable
  outcomes and traces but does not implement orchestration.
- Tool contracts and client/server design are documented in the feature's plan and MCP
  contract. They remain proposed until implemented and verified. MCP uses stdio; the
  assignment's examples do not prescribe the six-tool list.
