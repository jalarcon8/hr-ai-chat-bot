
# Project Requirements Integration

## 1. Authoritative Documents

The following project documents MUST be consulted during
feature development:

1. `.specify/memory/constitution.md`
   - Defines project-wide principles and constraints.

2. `docs/feature-roadmap.md`
   - Defines feature objectives, scope, exclusions,
     dependencies, and completion criteria.

3. `docs/requirements/traceability.md`
   - Maps Quantic requirements to their assigned features.
   - Tracks requirement implementation and verification.

4. `docs/requirements/quantic-project-requirements.pdf`
   - Contains the original Quantic assignment requirements.
   - Serves as the authoritative source for assignment
     requirements.

The Quantic requirements take precedence when interpreting
mandatory assignment requirements.

If documents conflict, report the conflict and request
clarification before proceeding.

## 2. Feature Identification

Before generating or modifying feature artifacts:

1. Identify the active feature using its `F###` identifier.
2. Locate the corresponding entry in the feature roadmap.
3. Determine the feature's:
   - Objective and scope.
   - Explicit exclusions.
   - Dependencies.
   - Completion criteria.
   - Assigned `QR-###` requirements.

If the active feature cannot be identified, request
clarification before proceeding.

Do not introduce functionality assigned to other features
unless necessary to satisfy an explicit dependency.

## 3. Requirements Coverage

Every applicable `QR-###` requirement MUST be traceable to:

1. A feature specification requirement or acceptance criterion.
2. An implementation-plan element.
3. One or more implementation or verification tasks.

When generating feature artifacts:

- Preserve the original meaning of Quantic requirements.
- Preserve mandatory quantities, thresholds, and constraints.
- Include applicable `QR-###` identifiers.
- Define measurable and testable acceptance criteria.
- Identify requirements that cannot be fully addressed
  within the current feature.

Do not silently modify feature boundaries or reinterpret
mandatory requirements.

## 4. Spec Kit Workflow Integration

### 4.1 Specify (`speckit-specify`)

When generating a feature specification:

1. Read the feature's roadmap entry.
2. Identify all assigned `QR-###` requirements.
3. Incorporate applicable requirements into `spec.md`.
4. Include traceability identifiers where appropriate.
5. Define testable acceptance criteria.
6. Report missing requirements or scope conflicts.

Do not implement functionality during specification.

### 4.2 Plan (`speckit-plan`)

When generating an implementation plan:

1. Review the feature specification.
2. Review applicable `QR-###` requirements.
3. Ensure the technical design addresses those requirements.
4. Verify compliance with the project constitution.
5. Respect feature boundaries and dependencies.
6. Identify technical decisions that affect requirements
   coverage.

Document any requirements that the proposed design
does not adequately address.

### 4.3 Tasks (`speckit-tasks`)

When generating implementation tasks:

1. Review the feature specification and implementation plan.
2. Identify all applicable `QR-###` requirements.
3. Generate tasks necessary to implement each requirement.
4. Include appropriate testing and verification tasks.
5. Respect feature dependencies and implementation order.
6. Identify requirements without corresponding tasks.

Ensure tasks are sufficiently detailed to support
implementation and verification.

### 4.4 Analyze (`speckit-analyze`)

When analyzing feature artifacts:

1. Review `spec.md`, `plan.md`, and `tasks.md`.
2. Compare them against the feature roadmap.
3. Compare them against the requirements traceability matrix.
4. Verify that assigned `QR-###` requirements are covered.
5. Identify:
   - Missing requirements.
   - Uncovered acceptance criteria.
   - Missing implementation tasks.
   - Missing verification tasks.
   - Conflicts with the constitution.
   - Deviations from the feature roadmap.

Report findings before recommending changes.

Do not automatically modify project-level documents.

### 4.5 Implement (`speckit-implement`)

During implementation:

1. Follow the approved specification, plan, and tasks.
2. Maintain compliance with the constitution.
3. Respect the feature's defined scope.
4. Implement required tests.
5. Record verification evidence.
6. Identify incomplete requirements.
7. Recommend traceability status updates.

Do not mark a requirement as `Verified` without
supporting evidence.

## 5. Requirements Validation

Before implementing a feature, verify:

- [ ] The feature matches its roadmap definition.
- [ ] All assigned `QR-###` requirements are identified.
- [ ] Every applicable requirement has specification coverage.
- [ ] Every requirement has a corresponding implementation
      or verification task.
- [ ] Acceptance criteria are measurable and testable.
- [ ] The implementation plan complies with the constitution.
- [ ] Feature dependencies are respected.
- [ ] No unnecessary functionality has been introduced.
- [ ] Any conflicts or gaps have been reported.

If significant gaps are identified, resolve them before
proceeding with implementation.

## 6. Implementation Verification

After implementing a feature:

1. Identify the requirements assigned to the feature.
2. Determine which requirements have been implemented.
3. Identify tests or other verification evidence.
4. Report any incomplete or unverified requirements.
5. Recommend updates to the traceability matrix.

Use the following requirement statuses:

| Status | Definition |
|---|---|
| Not Started | Implementation has not begun. |
| In Progress | Implementation work is underway. |
| Implemented | Functionality is complete but not fully verified. |
| Verified | Verification criteria have been satisfied. |

Do not infer verification solely from completed code.

## 7. Change Control

The following documents are project-level governance
artifacts:

- `.specify/memory/constitution.md`
- `docs/feature-roadmap.md`
- `docs/requirements/traceability.md`

These documents MUST NOT be modified without explicit
user approval.

If a feature requires changes to project-level documents:

1. Identify the proposed change.
2. Explain the reason for the change.
3. Identify affected features and requirements.
4. Describe potential impacts on existing artifacts.
5. Request user approval before making modifications.

Do not silently alter project scope, requirements,
dependencies, or constitutional principles.

## 8. General Execution Rules

During all Spec Kit workflows:

- Prioritize mandatory Quantic assignment requirements.
- Follow the project constitution.
- Use the roadmap to establish feature boundaries.
- Use the traceability matrix to verify coverage.
- Avoid unnecessary architectural complexity.
- Maintain consistency between feature artifacts.
- Preserve traceability throughout implementation.
- Report uncertainties rather than making unsupported
  assumptions.
- Request clarification when significant conflicts arise.

The objective is to deliver a simple, complete, testable,
and reproducible implementation that satisfies the
Quantic project requirements.