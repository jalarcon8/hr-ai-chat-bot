# Final Demonstration and Submission Checklist

**Status:** recording, access and submission are pending. Live prompts/evaluation remain
paused; this checklist is not authorization for more Groq requests. Review saved evidence
first and obtain owner approval before recording new live interactions.

## Prepare

- [ ] Review the [final report](../evaluation/final-report.md) and acknowledge incomplete
  evaluation, ungraded answers and insufficient latency samples.
- [ ] Review/merge the final documentation/evidence package through protected-main CI.
- [ ] Confirm deployed URL access for the grader, Community Cloud full main-file path
  `src/hr_app/app.py`, current serving revision and protected-main tracking.
- [ ] Confirm `quantic-grader` repository access; do not include secret/settings screens.
- [ ] Use only synthetic data: SYN-001, 80 PTO hours as of 2026-01-01, policy HR-002.
- [ ] Confirm project participant count is at most three and check the authoritative
  assignment's presenter, camera and identification instructions. Do not add identity
  documents to source control or reusable diagnostic artifacts.

## Suggested 7-10 minute screen-share

| Time | Show and explain |
|---|---|
| 0:00-1:00 | Objective, fictional data, app URL, health-equivalent JSON and cold-start caveat |
| 1:00-3:00 | PTO: employee context, profile/balance/policy MCP calls, safe arguments/results, citation/snippet, as-of balance and no approval/submission claim |
| 3:00-5:00 | Remote work: profile and policy evidence, conditional prior-approval check only if applicable, missing security/approval facts and human review instead of eligibility claim |
| 5:00-6:30 | Architecture, stdio MCP, local FAISS/MiniLM, Groq and secret boundaries |
| 6:30-8:00 | Protected-main CI: passing ordinary matrix jobs, AppTest/MCP tests; distinguish failed live diagnostic job |
| 8:00-9:00 | Two ungraded suite answers, provider failure, Windows timeout, hosted clarification, k comparison and missing 10-sample latency evidence |

- [ ] Show actual tool names, nonsecret synthetic arguments, outputs, sources and final
  behavior for **both** deployed tasks; a sample-prompt button alone is not workflow evidence.
- [ ] The UI intentionally shows allowlisted summaries, not all raw arguments/results.
  Explain the synthetic input and the returned balance/citations; use the documented schemas
  for field names. Do not weaken UI redaction or enable raw provider logging for the demo.
  If required raw tool details are not visible, record this limitation rather than claiming
  the screen demonstrates them.
- [ ] If a task fails or clarifies instead of answering, label it honestly; do not replace
  it with deterministic test output described as a successful deployed run.
- [ ] All group members participate as required; verify final duration is 7-10 minutes.

## Deliver

- [ ] Upload the recording; test sharing and add its actual link to README and deployed.md.
- [ ] Verify repository/deployment/demo links from the intended viewer context.
- [ ] Ensure the final commit includes required docs, cases, original partial results,
  preserved evidence, synthetic data and MCP code/schemas.
- [ ] Submit via the project dashboard; for groups, one member submits and uploads the
  signed final Group Project Agreement page if prompted.
- [ ] Retain the report's remaining gaps in the submission; no unsupported quality,
  latency, cold-start or full-workflow pass claims.
