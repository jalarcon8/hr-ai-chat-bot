# AI Tooling Disclosure

## Recorded use

GitHub Copilot in VS Code assisted specification-driven planning, code/test changes,
diagnosis, CI/evaluation tooling and documentation. GitHub Spec Kit supplied the
specification/clarification/plan/task workflow, adapted to the assignment traceability
process. Groq `openai/gpt-oss-20b` is the application's runtime model, not an independent
grader of its own answers.

The owner reviewed milestone scope, approved protected-main changes and bounded live runs,
reported manual deployment smoke tests, and directed closure without more live requests.
This disclosure covers the observed project record; the submitter must confirm any other
AI tools or externally sourced material used before submission.

## Strengths and limits observed

- Helpful for generating focused tests, connecting existing interfaces, preparing deployment
  instructions, and preserving safe provider diagnostics and evaluation evidence.
- Scripted tests can verify orchestration and guardrails but cannot establish live model
  correctness. Completed responses still require human rubric review.
- Live tool-call generation varied: HTTP 400 `tool_use_failed`, a later usable call followed
  by local MCP timeout, and hosted clarification instead of policy search. No single cause
  or general reliability improvement is claimed.
- AI-generated explanations and documentation can become stale. Paths, configuration, CI
  outcomes and evidence counts were checked against this checkout and saved artifacts;
  public deployment details and submission actions remain owner verification tasks.

## Responsibility and academic integrity

The submitter remains responsible for correctness, security, source attribution and compliance
with the assignment's AI-use rules. No ungraded answer is labeled correct, no missing result
is fabricated, and no skipped live test is reported as passed. Only fictional policies and
synthetic employee fixtures are intended for this project. Secrets, real HR data, identity
documents and hidden reasoning must not be added to the repository or demo artifacts.

External dependency/design references are listed in
[design-and-evaluation.md](design-and-evaluation.md). Retain upstream license notices and
attribute any additional reused material; these links do not claim authorship of dependencies.
Project workflow references: [GitHub Spec Kit](https://github.com/github/spec-kit) and
[GitHub Copilot documentation](https://docs.github.com/en/copilot).
