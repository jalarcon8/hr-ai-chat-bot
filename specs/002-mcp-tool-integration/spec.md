# Feature Specification: MCP Tool Integration

**Feature Branch**: Not created

**Created**: 2026-11-11

**Status**: Draft - clarification required

**Input**: Provide a FastMCP server exposing six proposed tools, synthetic employee and PTO
data, and an MCP client that discovers and invokes the tools. Wrap Feature 001's RAG
capabilities instead of building another retrieval system.

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
- A known employee has no PTO record: report missing data rather than assuming a zero balance.
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
- **FR-002**: [NEEDS CLARIFICATION: What are the names and intended behaviors of the six
  proposed tools? No definitive six-tool list was found in the available project documents.]
- **FR-003**: The provided MCP client MUST discover tools and invoke them through MCP rather
  than directly calling server functions.
- **FR-004**: At least one policy-evidence tool MUST use Feature 001's retrieval capabilities
  and preserve source identifiers, sections when available, and supporting snippets. This
  feature MUST NOT create a second index, embedding pipeline, or retrieval system.
- **FR-005**: The system MUST provide clearly identified synthetic employee and PTO data and
  expose access to that data through one or more of the agreed tools. No real HR integration
  or real employee data is permitted.
- **FR-006**: Each tool MUST validate its declared arguments. Unknown tools, invalid inputs,
  missing records, insufficient policy evidence, and operational failures MUST be
  distinguishable to the caller; failures MUST NOT appear as successful results.
- **FR-007**: Tool-call traces MUST identify each tool and capture inputs, outputs, and errors
  with secrets and unnecessary user input redacted. Document what is logged and how to inspect
  the trace.
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
- **SC-004**: Each successful and failed test invocation produces an inspectable trace with
  tool name, appropriately redacted inputs, and outcome; test secrets are absent from logs.
- **SC-005**: A developer following the documented local setup can run server and client,
  discover the six tools, and reproduce the calls without a real HR system.

## Assumptions

- Feature 001 is specified but has not yet been implemented in this project; its retrieval
  interface and indexed synthetic corpus are dependencies for end-to-end verification.
- Web UI, deployed application, agent orchestration, and full HR workflows are outside this
  increment and remain required for the overall assignment.
- Tool-specific contracts and any mutation requirements remain unresolved until the six
  proposed tools are identified. The assignment's example list does not designate a set of six.
- Local transport and detailed client/server design are deferred to planning, subject to MCP
  compatibility and the single-service constraint.
