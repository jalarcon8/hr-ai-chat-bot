# Feature Specification: HR Agentic Workflows

**Feature ID**: F004

**Feature Branch**: `004-hr-agentic-workflows`

**Created**: 2026-11-15

**Status**: Draft - ready for user review

**Input**: Deliver cited PTO-request and remote-work guidance by combining policy evidence with synthetic employee data through the existing HR agent.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Get PTO request guidance (Priority: P1)

As an employee, I want guidance about a PTO request based on my synthetic employee record, available balance, and the applicable policy so that I understand the relevant request steps and limitations.

**Why this priority**: PTO is one of the two required end-to-end workflows and depends on both employee-specific data and policy evidence.

**Independent Test**: Submit a request for a known synthetic employee and verify that the response uses the employee profile, PTO balance, and cited PTO policy evidence.

**Acceptance Scenarios**:

1. **Given** a known employee with a PTO record and a request that provides the employee ID and relevant dates or hours, **When** the employee asks whether the request appears supportable, **Then** the agent checks the employee profile, available PTO balance, and relevant policy evidence, and explains the request and approval process without claiming that the request has been submitted or approved.
2. **Given** the employee ID is missing or ambiguous, **When** the request needs employee-specific information, **Then** the agent asks for the identifier before looking up or attributing a record.
3. **Given** the employee exists but has no PTO record, **When** the workflow checks the balance, **Then** the agent reports that the balance is unavailable rather than treating it as zero.
4. **Given** the requested hours exceed the available balance or relevant policy evidence is insufficient, **When** the agent responds, **Then** it identifies the limitation and directs the employee to the appropriate human decision-maker without promising an exception.
5. **Given** the user explicitly requests a manager email draft and supplies any missing recipient or purpose details, **When** the workflow completes, **Then** the agent presents an unsent draft and does not send an email or represent the draft as a submitted request.

### User Story 2 - Get remote-work guidance or escalation (Priority: P1)

As an employee, I want remote-work guidance based on my synthetic profile and the applicable location and security policies so that I know which requirements are supported and which need review.

**Why this priority**: The remote-work workflow is the second required end-to-end agentic task and includes policy checks that cannot be established from the employee profile alone.

**Independent Test**: Submit a remote-work request for a known synthetic employee and verify that the response combines profile facts with cited location and security policy evidence, while clearly identifying unknown approval or security facts.

**Acceptance Scenarios**:

1. **Given** a known employee and a request concerning a work location or arrangement, **When** the workflow runs, **Then** the agent retrieves the employee profile and relevant remote-work and security policy evidence, and distinguishes current profile information from approval for a proposed change.
2. **Given** the request concerns work from another US state and the user supplies the facts needed for the supported prior-approval check, **When** the workflow evaluates those facts, **Then** the agent reports the compliance tool's conclusion and limitations with the returned policy citations.
3. **Given** approval facts or employee-specific security facts are absent, **When** they are needed to determine eligibility, **Then** the agent asks for the missing facts or escalates for review rather than assuming compliance or noncompliance.
4. **Given** the request concerns international work, an unsupported approval check, or conflicting or insufficient policy evidence, **When** the workflow responds, **Then** it cites what is known and directs the user to the responsible human reviewer without presenting an eligibility decision.

### User Story 3 - Inspect workflow evidence and outcomes (Priority: P2)

As a developer or reviewer, I want to reproduce both workflows and inspect concise operational traces so that I can verify tool use, evidence, and escalation without exposing hidden reasoning or unnecessary personal data.

**Why this priority**: Verifiable MCP call sequences and safe traces are required for acceptance, review, and demonstration.

**Independent Test**: Run the documented PTO and remote-work scenarios against synthetic fixtures and inspect each response and trace.

**Acceptance Scenarios**:

1. **Given** either documented workflow is run, **When** its result is inspected, **Then** the response includes cited policy evidence where policy claims are made, and the trace shows the ordered tool names, allowlisted argument and output summaries, outcomes, evidence references, answer basis, and any clarification or escalation.
2. **Given** a tool is unavailable, returns an error, or provides an inconclusive result, **When** the workflow encounters it, **Then** the agent surfaces the failure or limitation and does not present a success-shaped answer.
3. **Given** a user requests an approval, record update, email sending, or other unsupported action, **When** the agent processes the request, **Then** it refuses the action and does not simulate its completion.
4. **Given** a reviewer follows the documented demo scenarios, **When** they compare the workflow descriptions with observed results, **Then** they can identify each task's expected tool-call sequence, relevant inputs and outputs, citations, and escalation outcome.

### Edge Cases

- An employee name matches no record or more than one record; the agent requests an employee ID and does not choose a record.
- A known employee has no PTO record; the agent does not infer a zero balance or a policy exception.
- PTO availability is reported as of a past date; the agent labels the date and does not present it as a current or projected balance.
- Requested dates, hours, location, or manager-draft details are missing; the agent asks only for the information required to continue.
- A PTO request may involve protected leave, a local-law exception, or a balance correction; the agent routes the question to People Operations instead of making a legal or payroll determination.
- A manager email draft is requested without a recipient or purpose; the agent asks for the missing detail and never sends the email.
- A profile's current work arrangement or state is mistaken for authorization to change work location; the agent distinguishes the existing profile from proposed-work approval.
- Employee-specific security posture is unavailable; the agent describes applicable policy requirements but does not claim that a device, network, or account satisfies them.
- Prior-approval facts are missing, contradictory, or unauthenticated; the agent reports an indeterminate result or requests clarification and does not convert an assertion into verified approval.
- An MCP call fails, a policy search returns no useful evidence, or returned sources conflict; the agent surfaces the problem and does not invent a result or citation.
- Trace or response content would expose hidden reasoning, credentials, full records, or unnecessary sensitive details; such content is excluded.

## Scope Boundaries

**In scope**: The PTO request-guidance workflow; the remote-work guidance-or-escalation workflow; sequential use of existing MCP tools; cited policy and synthetic-record grounding; concise, privacy-safe operational traces; repeatable scenarios for both workflows.

**Out of scope**: Real HR systems or employee data; a web interface; email sending; submitting or approving requests; changing employee records; new compliance checks beyond the existing supported prior-approval check; legal, payroll, or employee-specific security determinations unsupported by available evidence; unrelated HR workflows.

## Dependencies

- **F001 - Policy ingestion and retrieval**: supplies the indexed synthetic policy corpus and traceable evidence.
- **F002 - MCP tools**: supplies policy search, synthetic employee and PTO records, the limited prior-approval check, and the unsent email-draft capability.
- **F003 - Agent orchestration**: supplies intent interpretation, bounded sequential tool use, grounded synthesis, operational traces, explicit failure handling, and action-specific confirmation. F004 adds the two dedicated workflows rather than duplicating this general behavior.
- **F005 - Chat interface**: consumes the F004 workflows and supplies the grader-facing UI or API route for QR-032; this is a downstream feature, not a prerequisite for implementing F004.
- **F006 - Evaluation and delivery**: owns the project-wide evaluation and final demo obligations; F004 supplies workflows and documentation that those later activities can evaluate and demonstrate.

## MVP Classification

**Required for F004**

- Complete both roadmap workflows: PTO request guidance and remote-work guidance or escalation.
- Combine relevant employee-specific synthetic facts with cited policy evidence, preserving missing or inconclusive outcomes.
- Preserve sequential tool use, operational traces, explicit failures, and safe-action behavior from F003.
- Clarify missing or ambiguous employee IDs and other necessary facts; report unavailable records and escalate when evidence cannot support a decision.
- Provide repeatable scenarios and workflow documentation needed for QR-032 and QR-047.
- Draft a manager message only when requested, using the existing unsent draft capability and confirmation behavior.

**Supporting**

- Reuse existing F001-F003 capabilities and synthetic fixtures; use the existing human-review paths for unsupported legal, payroll, approval, or employee-specific security decisions.

**Deferred from F004, not dropped from the project**

- The grader-facing UI/API and deployed reproduction flow are owned by F005.
- The evaluation set and reported metrics, recorded demo, and final presentation requirements are owned by F006. F004 must not add evaluation infrastructure or presentation features.
- Benefits, expenses, HR case handling, real HR integrations, email sending, record updates, and new compliance checks are outside F004.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The agent MUST support the PTO and remote-work workflows as distinct user goals and MUST use the existing agent orchestration capability to choose and execute the required sequential tool calls.
- **FR-002**: For PTO guidance, the agent MUST use the employee profile, available PTO balance, and relevant policy evidence when those facts are needed. It MUST identify the balance's as-of date and MUST NOT treat a missing balance as zero or an available balance as a projected balance.
- **FR-003**: PTO guidance MUST explain relevant policy requirements, request and approval steps, and the limits of available data. The agent MUST NOT claim that it submitted, approved, denied, or guaranteed a request, balance exception, or legal entitlement.
- **FR-004**: The agent MUST request a missing or ambiguous employee identifier before attributing employee or PTO data to a person. It MUST request missing dates, hours, or draft details when they are necessary to answer the request.
- **FR-005**: The agent MUST create a manager email draft only when explicitly requested, using the existing draft capability and supplied or confirmed details. It MUST keep the draft unsent, honor the existing action-specific confirmation behavior, and state that no email was sent.
- **FR-006**: For remote-work guidance, the agent MUST use the employee profile and relevant location, remote-work, and security policy evidence. It MUST distinguish current profile facts from authorization for a proposed work arrangement or location.
- **FR-007**: The agent MUST use the existing compliance capability only for its supported out-of-state prior-approval check, and only with facts provided by the caller. Missing or inconclusive facts MUST result in clarification or an indeterminate outcome; caller assertions MUST NOT be described as independently verified.
- **FR-008**: When eligibility depends on unavailable employee-specific security facts, unsupported approval rules, international-work review, legal interpretation, or other missing evidence, the agent MUST identify the gap and recommend review by the responsible human function instead of deciding eligibility.
- **FR-009**: Factual policy statements MUST be grounded in relevant returned evidence and cite its document ID, title, section when available, and supporting snippet. Employee-specific statements MUST be grounded in the corresponding tool result. The agent MUST distinguish facts, recommendations, and unresolved questions.
- **FR-010**: Each workflow MUST execute tool calls sequentially through MCP and produce an inspectable trace of the ordered tool names, allowlisted argument and output summaries, outcomes, evidence references, final-answer basis, and clarification, escalation, or failure outcome. Traces MUST exclude hidden chain-of-thought, internal prompts, credentials, and unnecessary raw user or employee data.
- **FR-011**: The agent MUST surface MCP, model, and evidence failures explicitly. It MUST NOT represent a failed call as successful, silently substitute unsupported data, or invent an answer or citation.
- **FR-012**: The agent MUST refuse email sending, request approval, employee-record updates, and other unsupported or irreversible actions; it MUST NOT imply that such an action occurred.
- **FR-013**: The feature MUST provide deterministic, documented scenarios for both workflows using synthetic fixtures, without depending on live HR systems or a live model provider for routine tests. The scenarios and expected outcomes MUST be suitable for later reproduction through the grader-facing interface or API client.
- **FR-014**: Feature documentation MUST describe both demo workflows and their expected tool-call sequences, including the tools and relevant inputs and outputs, returned evidence, and conditions that lead to clarification or escalation. The selected sequence details MUST be established during planning and documented consistently with the implemented workflow; this specification does not prescribe a particular tool order or call signature.

### Key Entities

- **Employee profile**: A synthetic employee record, identified by employee ID, with current work arrangement and work state.
- **PTO balance**: Synthetic available PTO hours for an employee, including the date through which the balance is reported; a missing record is distinct from a zero balance.
- **Policy evidence**: Retrieved candidate policy excerpts with source identifiers, title, section when available, snippet, and index generation.
- **Approval facts**: Caller-provided facts for the one supported remote-work prior-approval check; not independently authenticated.
- **Workflow result**: The user-facing facts, citations, guidance, clarification, escalation, or failure outcome produced from the available evidence.
- **Operational trace**: A concise record of ordered tool calls, allowlisted summaries, outcomes, evidence references, and final-answer basis, excluding hidden reasoning and unnecessary sensitive data.
- **Email draft**: An unpersisted, unsent mock message created only at the user's explicit request.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The documented PTO scenario produces a response grounded in an employee profile, a PTO balance with its as-of date, and at least one relevant policy citation; missing records are reported distinctly from zero values.
- **SC-002**: The documented remote-work scenario produces a response grounded in the employee profile and relevant location or security policy evidence, and identifies unsupported or missing facts as clarification or escalation rather than a definitive eligibility result.
- **SC-003**: Both distinct workflows complete end to end by combining employee-specific information with cited policy guidance, and each workflow's trace shows the operations and outcomes in order.
- **SC-004**: Every policy claim in workflow acceptance tests has a matching returned citation; every employee-specific claim matches a returned synthetic tool result.
- **SC-005**: No acceptance scenario sends an email, submits or approves a request, updates an employee record, or treats an unsupported operation as completed.
- **SC-006**: Both workflows are reproducible from documented scenarios using synthetic fixtures; the scenarios and expected outcomes are available for the grader-facing interface or API client delivered by the owning interface feature.
- **SC-007**: Workflow traces contain the required observable call, allowlisted argument and output summaries, evidence, answer-basis, and escalation details while excluding hidden reasoning, credentials, full employee records, and unnecessary raw user input.
- **SC-008**: Documentation describes both demo tasks and their expected call sequences, relevant inputs and outputs, citations, and escalation outcomes; reviewers can compare those descriptions with the workflow traces.

## Assumptions

- Users identify synthetic employees by employee ID; profile lookup is not a name-search capability.
- The current synthetic profile and PTO fixtures are the only employee-specific data sources in scope.
- The available PTO value is a point-in-time balance, not a projected balance or an approval decision.
- Remote-work policy excerpts can describe required controls, but the synthetic records do not establish an employee's actual security posture or approval for a proposed location.
- Only the existing out-of-state prior-approval compliance check is available; other remote-work conclusions require policy-supported guidance or human review.
- Feature 003's MCP discovery, bounded sequential execution, grounding, trace, error, and confirmation behavior remains the orchestration foundation.
- All employees, policies, and operational examples are fictional. Human review recommendations refer to the fictional policy roles, such as the manager, People Operations, or IT.

## Assignment Requirements Traceability

In the acceptance-scenario column, `USn-ASm` refers to acceptance scenario *m* in User Story *n* above.

| Assignment requirement | Functional requirements | Success criteria | Acceptance scenarios |
|---|---|---|---|
| QR-019 - Support at least two multi-step HR workflows. | FR-001-FR-003, FR-006 | SC-001-SC-003 | US1-AS1, US2-AS1-AS2 |
| QR-020 - Provide concise, privacy-safe operational traces. | FR-009-FR-010 | SC-003, SC-007 | US3-AS1 |
| QR-021 - Handle missing identifiers, incomplete evidence, ambiguity, and unavailable tools. | FR-004, FR-007-FR-011 | SC-001-SC-004 | US1-AS2-AS4, US2-AS3-AS4, US3-AS2 |
| QR-022 - Prevent unauthorized or irreversible actions. | FR-005, FR-012 | SC-005 | US1-AS5, US3-AS3 |
| QR-032 - Enable a grader to reproduce both agentic tasks. (F005 owns the grader-facing interface; F004 supplies reproducible workflow scenarios.) | FR-013 | SC-006 | US3-AS4 |
| QR-047 - Describe both demo tasks and expected tool-call sequences. (F006 owns final design documentation; F004 supplies workflow-specific documentation.) | FR-014 | SC-008 | US3-AS4 |

QR-020-QR-022 are already verified at the general agent-orchestration level by F003; F004 acceptance verifies that both named workflows preserve those behaviors. The roadmap also identifies QR-040-QR-042 (evaluation) and QR-049/QR-051 (recorded demo and presentation) as requirements F004 supports; they remain F006-owned. F004 provides workflows and evidence suitable for later evaluation and demonstration but does not add an evaluation framework, create the recording, or assume F005's UI/API responsibility.
