# Feature Specification: MCP Tool Integration

**Feature Branch**: Not created

**Created**: 2026-11-11

**Status**: Draft - clarification required

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

- Q: Which policy check should the compliance tool support initially? → A: Check prior written People Operations approval before working from another US state; do not assess overall eligibility.
- Q: How should callers distinguish a valid no-result from a failed tool call? → A: Use structured `found`, `not_found`, and `indeterminate` outcomes; invalid inputs and operational failures are MCP tool errors, while transport, connectivity, and discovery failures are client-side errors.
- Q: Where should the compliance tool obtain the facts it checks? → A: The caller identifies the supported check and supplies synthetic facts; missing or unknown approval is indeterminate, and unsupported checks are invalid.
- Q: What source details should every returned policy excerpt include? → A: Include document ID, title, optional section, exact excerpt, chunk ID, and index generation ID; include a retrieval score for ranked search results only.
- Q: What minimum inputs should each of the six tools require? → A: Require the specified question, identifiers, or drafting details for each tool; use a positive search `k` defaulting to 5 and an optional explicit approval status for compliance.
- Q: How should the policy search tool describe top-k results whose relevance has not been established? → A: Return nonempty retrieval results as candidate evidence with `found`; use `not_found` only for a successful empty retrieval.

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
3. **Given** a successful or failed tool call, **When** the trace is inspected, **Then** it
   identifies the tool, records appropriately redacted inputs and outcome, and excludes secrets
   and unnecessary user input.

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
- Logging failure is surfaced according to the application's documented error handling; it does
  not silently expose credentials or unrestricted user text.
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
  result identifying missing information when necessary facts or evidence are insufficient.
  Initially it MUST check whether prior written People Operations approval is present for
  work in another US state, using the applicable remote-work policy evidence. The caller MUST
  identify the supported check and supply the relevant synthetic facts; the tool MUST NOT
  independently retrieve employee records. With sufficient evidence, explicitly confirmed
  prior written approval yields `compliant`, and explicitly confirmed absence yields
  `noncompliant`; missing or unknown approval yields `indeterminate` and MUST NOT be treated
  as approval. Unsupported check identifiers are invalid input. A `compliant` or
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
  - `check_policy_compliance`: required supported `check_id`; optional `approval_status` of
    `approved`, `not_approved`, or `unknown`. A missing or `unknown` status produces an
    indeterminate conclusion.
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
  distinguishable to the caller; failures MUST NOT appear as successful results. Successful
  results MUST identify `found` when requested information or candidate search evidence is
  returned, `not_found` when a
  completed lookup finds no matching record or evidence, and `indeterminate` when available
  information is insufficient to establish a reliable conclusion. Invalid inputs and
  operational failures MUST produce MCP tool error responses. Transport, connectivity,
  discovery, and unknown-tool failures MUST be surfaced as client-side errors. Detailed
  response schemas and error-code mappings are deferred to planning.
- **FR-007**: Tool-call traces MUST identify each tool and capture allowlisted, concise
  summaries of inputs, outputs, and errors, such as safe argument metadata, source IDs, and
  outcome. By default, traces MUST omit raw questions, email drafts, full records, secrets, and
  unnecessary user input. Successful outcomes, tool errors, and client-side transport,
  connectivity, discovery, and unknown-tool errors MUST be represented in the operational
  trace, identifying the tool when known. Document the allowlist and how to inspect the trace.
- **FR-008**: Tools MUST be read-only by default. Any agreed mutation MUST operate on
  synthetic data only, require explicit user confirmation, and support a documented reversal
  or reset.
- **FR-009**: Automated tests MUST use synthetic fixtures, exercise discovery and invocation
  through an MCP client, cover every agreed tool and its validation and failure cases, and
  replace external services with deterministic test doubles where needed.
- **FR-010**: Documentation MUST cover setup, server and client execution, transport, tool
  schemas, synthetic data, testing, error behavior, and the connection to Feature 001.
- **FR-011**: The server and client MUST support local development and remain compatible with
  a single-service, free-tier deployment; no separately deployed service is required.

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
  They distinguish the three valid outcome statuses, MCP tool errors, and client-side errors.
- **SC-004**: Each successful and failed test invocation produces an inspectable trace with
  tool name, appropriately redacted inputs, and outcome; test secrets are absent from logs.
- **SC-005**: A developer following the documented local setup can run server and client,
  discover the six tools, and reproduce the calls without a real HR system.
- **SC-006**: Automated checks cover the required inputs, search default and `k` validation,
  supported and unsupported compliance checks, all approval statuses including a missing status,
  and draft generation without sending or external actions. Nonempty search results, including
  potentially unrelated chunks, are labeled candidate evidence rather than confirmed support.

## Assumptions

- Feature 001's implemented retrieval interface and indexed synthetic corpus are dependencies
  for end-to-end verification.
- Web UI, deployed application, agent orchestration, and full HR workflows are outside this
  increment and remain required for the overall assignment.
- Feature 003's orchestrator is expected to interpret these outcomes, request clarification or
  recommend escalation where needed, obtain available compliance facts via appropriate tools
  or user clarification, and avoid unsupported conclusions; F002 supplies the distinguishable
  outcomes and traces but does not implement orchestration.
- Detailed response fields, supported-check identifiers, and validation mechanisms are
  deferred to planning. The assignment's example list does not designate a set of six.
- Detailed client/server design is deferred to planning, subject to MCP compatibility and the
  single-service constraint; local transport uses stdio.
