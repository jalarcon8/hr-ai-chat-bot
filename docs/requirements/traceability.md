# Quantic Requirements Traceability

Source: [Quantic AI Agent project](Quantic%20AI%20Agent%20project.pdf). Page numbers refer to
the eight-page PDF. Wording such as "should", "where feasible", "approximately", and
"optional" retains the source's level of obligation; project constitution requirements can
be stricter. Ownership identifies one primary feature and, where useful, supporting features.
All statuses are initialized to **Not Started**, not an assessment of existing draft specs.

| Requirement ID | Source | Requirement | Owning Feature | Verification Method | Status |
|---|---|---|---|---|---|
| QR-001 | p. 2, Project Description | Assemble a coherent policy/procedure corpus of approximately 5-20 short files totaling 30-120 pages, supporting realistic HR topics; use authored or legally includable material. | F001 | Inspect corpus, content coverage, rights, and documented page-equivalent count. | Not Started |
| QR-002 | p. 2, Project Description | Provide small, clearly synthetic structured datasets with no real private employee information. | F002; supports F004 | Inspect fixture provenance and synthetic records. | Not Started |
| QR-003 | p. 2, Project Description | Use free or zero-cost options where possible and keep corpus and datasets small enough for modest free-tier resources. | F006; supports F001, F002 | Inspect configuration and measure deployment resource use. | Not Started |
| QR-004 | p. 2, 1. Environment and Reproducibility | Create a virtual environment or equivalent setup and list dependencies. | F006; supports F001-F005 | Reproduce clean environment and inspect dependency manifest. | Not Started |
| QR-005 | p. 2, 1. Environment and Reproducibility | Provide README setup, local run, deployment, and evaluation instructions. | F006; supports F001-F005 | Follow README from clean setup through evaluation. | Not Started |
| QR-006 | p. 2, 1. Environment and Reproducibility | Set fixed seeds where applicable, including reproducible evaluation sampling or chunking. | F006; supports F001 | Inspect configuration and repeat applicable runs. | Not Started |
| QR-007 | p. 2, 1. Environment and Reproducibility | Read secrets such as API keys from environment variables and do not commit them. | F006; supports F001-F005 | Inspect configuration and repository for secrets. | Not Started |
| QR-008 | p. 2, 2. Policy Corpus Ingestion and Indexing | Parse and clean documents, handling at least two source formats where feasible. | F001 | Test ingestion of Markdown and TXT fixtures. | Not Started |
| QR-009 | p. 2, 2. Policy Corpus Ingestion and Indexing | Chunk documents using a justified strategy. | F001 | Inspect chunking rationale and test representative documents. | Not Started |
| QR-010 | p. 2, 2. Policy Corpus Ingestion and Indexing | Embed chunks with a free, local, or free-tier model/API. | F001 | Inspect configuration and test embedding generation. | Not Started |
| QR-011 | p. 2, 2. Policy Corpus Ingestion and Indexing | Store embedded chunks in a local or lightweight vector database. | F001 | Inspect FAISS index and test retrieval. | Not Started |
| QR-012 | p. 2, 2. Policy Corpus Ingestion and Indexing | Persist citation metadata including document title or ID, section, and source snippet. | F001 | Inspect indexed metadata and verify source traceability. | Not Started |
| QR-013 | p. 3, 3. Retrieval Augmented Generation | Implement top-k retrieval; filtering, rewriting, and reranking are optional. | F001 | Test top-k retrieval against synthetic corpus. | Not Started |
| QR-014 | p. 3, 3. Retrieval Augmented Generation | Inject retrieved chunks and source metadata into the LLM context. | F001 | Test or inspect prompt/context construction. | Not Started |
| QR-015 | p. 3, 3. Retrieval Augmented Generation | Generate answers citing source IDs, titles, or sections and include supporting snippets where appropriate. | F001; supports F003, F005 | Evaluate citations and supporting evidence against sources. | Not Started |
| QR-016 | p. 3, 3. Retrieval Augmented Generation | Refuse or redirect out-of-corpus policy questions, limit unsupported claims, and distinguish policy facts from recommendations. | F001; supports F003 | Test unsupported, out-of-scope, and recommendation cases. | Not Started |
| QR-017 | p. 3, 3. Retrieval Augmented Generation | Include at least one complex question requiring retrieval from multiple policy documents. | F001; supports F006 | Evaluate a multi-document question and its citations. | Not Started |
| QR-018 | p. 3, 4. Agentic System Design | Orchestrator interprets intent, decides whether RAG suffices, selects and calls MCP tools, and synthesizes final responses. | F003; supports F002 | Test agent decisions, actual calls, and final synthesis. | Not Started |
| QR-019 | p. 3, 4. Agentic System Design | Support at least two multi-step HR workflows. | F004; supports F003 | Demonstrate PTO and remote-work workflows end to end. | Not Started |
| QR-020 | p. 3, 4. Agentic System Design | Provide visible or logged concise operational traces of tool selection, arguments, outputs, sources, answer basis, and escalation decisions, without hidden chain-of-thought. | F003; supports F002, F004, F005 | Inspect traces for representative flows and redaction. | Not Started |
| QR-021 | p. 3, 4. Agentic System Design | Gracefully handle unavailable tools, missing employee IDs, incomplete evidence, and ambiguity requiring clarification. | F003; supports F002, F004 | Test each failure and clarification path. | Not Started |
| QR-022 | p. 3, 4. Agentic System Design | Prevent irreversible actions; HR tickets, manager messages, and case updates must be mock actions or require explicit user confirmation. | F003; supports F002, F004 | Test action safety, confirmation, and mock behavior. | Not Started |
| QR-023 | p. 3, 5. MCP Server and Tool Integration | Implement one or more MCP servers using a compatible transport. | F002 | Test local server startup and MCP handshake. | Not Started |
| QR-024 | p. 3, 5. MCP Server and Tool Integration | Expose at least five MCP tools, including at least one policy-evidence/RAG tool and one structured-data or mock-operation tool. | F002 | Discover tools and test evidence and data calls through MCP. | Not Started |
| QR-025 | p. 3, 5. MCP Server and Tool Integration | Tools should include operations such as policy search, policy sections, employee and PTO lookup, compliance checks, or draft email; listed tool names are examples. | F002 | Inspect tool descriptions and exercise the selected six. | Not Started |
| QR-026 | p. 3, 5. MCP Server and Tool Integration | Agent execution must actually invoke MCP-exposed tools; direct calls alone are insufficient. | F003; supports F002 | Integration test protocol calls from agent through MCP. | Not Started |
| QR-027 | p. 3, 5. MCP Server and Tool Integration | Document MCP architecture, transport, tool schemas, discovery, and invocation. | F002; supports F006 | Inspect architecture and tool documentation. | Not Started |
| QR-028 | p. 3, 6. Web Application | Provide a web application using an appropriate framework; the source permits several framework choices. | F005 | Inspect and demonstrate the browser application. | Not Started |
| QR-029 | p. 3, 6. Web Application | Web app should provide a chat interface for policy and workflow questions. | F005 | Demonstrate both categories of question in browser. | Not Started |
| QR-030 | p. 3, 6. Web Application | Provide a chat endpoint or equivalent returning final answer, citations, snippets, and concise tool-call trace. | F005; supports F003 | Test request/response equivalent and inspect output. | Not Started |
| QR-031 | p. 3, 6. Web Application | Provide a health endpoint or equivalent returning JSON app status and MCP connectivity where feasible. | F005; supports F006 | Request health equivalent and verify JSON and connectivity. | Not Started |
| QR-032 | p. 3, 6. Web Application | Enable a grader to reproduce at least two agentic demo tasks via UI or API client. | F005; supports F004 | Reproduce both tasks from documented entry points. | Not Started |
| QR-033 | p. 4, 7. Deployment | Deploy to Render, Railway, or equivalent free-tier/zero-cost host with a shareable URL unless a platform outage or exceptional deployment issue is documented. | F006 | Open deployed URL or inspect documented exception. | Not Started |
| QR-034 | p. 4, 7. Deployment | Single-service deployment is acceptable; avoid requiring a paid database. | F006; supports F001-F005 | Inspect deployment and storage configuration. | Not Started |
| QR-035 | p. 4, 7. Deployment | If an MCP server is deployed separately, configure its URL through environment variables; separate deployment is encouraged but not required. | F006; supports F002 | Inspect configuration if applicable; single-service baseline makes this conditional. | Not Started |
| QR-036 | p. 4, 7. Deployment | Explain expected cold-start behavior in README and demo if the free-tier service spins down. | F006 | Inspect README and demonstration when applicable. | Not Started |
| QR-037 | p. 4, 8. CI/CD | Run GitHub Actions or equivalent on push or pull request; install dependencies, perform a build/start/import check, and run automated tests before deployment. | F006; supports F001-F005 | Inspect and execute pipeline. | Not Started |
| QR-038 | p. 4, 8. CI/CD | Include at least one automated application-start test and one MCP discovery or simple tool-call test. | F006; supports F002, F005 | Inspect CI results for both checks. | Not Started |
| QR-039 | p. 4, 8. CI/CD | Deployment must only occur if tests pass. | F006 | Inspect pipeline dependency and test failure behavior. | Not Started |
| QR-040 | p. 4, 9. Evaluation | Provide 20-30 evaluation questions/tasks with correct or gold answers, covering straightforward policy, multi-document, tool-requiring, ambiguous, and out-of-scope cases. | F006; supports F001-F004 | Count and inspect evaluation set and expected answers. | Not Started |
| QR-041 | p. 4, 9. Evaluation | Report answer groundedness and citation accuracy; exact/partial match is optional. | F006; supports F001, F003 | Inspect evaluation method and reported results. | Not Started |
| QR-042 | p. 4, 9. Evaluation | Report tool-selection accuracy, workflow completion rate, escalation/clarification accuracy, and action-safety pass rate. | F006; supports F003, F004 | Inspect evaluation cases, scoring, and results. | Not Started |
| QR-043 | p. 4, 9. Evaluation | Report p50/p95 latency for 10-20 representative queries/tasks; separate cold and warm starts where possible if cold starts affect latency. | F006 | Inspect timed sample count, calculations, and results. | Not Started |
| QR-044 | p. 4, 9. Evaluation | Include at least one ablation or comparison, such as retrieval k, chunk size, prompts, or tool availability. | F006; supports F001, F003 | Inspect comparison method and reported results. | Not Started |
| QR-045 | p. 4, 10. Design Documentation | Justify orchestration, MCP server and transport, tool schemas, embeddings, chunking, retrieval k, vector store, deployment, and safety choices. | F006; supports F001-F005 | Inspect design documentation. | Not Started |
| QR-046 | p. 4, 10. Design Documentation | Include an architecture diagram or text showing web app, agent orchestrator, MCP client/server, RAG index, mock data, and LLM provider. | F006; supports F001-F005 | Inspect architecture description. | Not Started |
| QR-047 | p. 4, 10. Design Documentation | Describe both demo tasks and expected MCP tool-call sequences. | F006; supports F004 | Compare documentation with actual workflow traces. | Not Started |
| QR-048 | pp. 1, 5-6, Submission Guidelines | Submit links to the recorded demo and GitHub repository; include deployed URL in README and share the repository with `quantic-grader`. | F006 | Inspect submission links, README, and repository access. | Not Started |
| QR-049 | pp. 1, 5-6, Submission Guidelines | Record a 7-10 minute screen-share with voiceover showing two deployed agentic tasks end to end. | F006; supports F004, F005 | Review recording duration and both deployed tasks. | Not Started |
| QR-050 | pp. 5-6, Submission Guidelines | All group members must speak, be on camera, and show government ID in the demo; do not store identity documents in the repository. | F006 | Presenter verifies recording meets assignment instructions. | Not Started |
| QR-051 | p. 6, Submission Guidelines | For each demo task explain MCP tool names, arguments, outputs, retrieved citations, and final answer or action; briefly cover design, deployment, CI/CD, and evaluation. | F006; supports F003-F005 | Review recording against demonstration checklist. | Not Started |
| QR-052 | p. 6, Submission Guidelines | Repository contains developed code, synthetic mock data where used, and MCP server code and tool definitions. | F006; supports F001-F005 | Inspect repository contents. | Not Started |
| QR-053 | p. 6, Submission Guidelines | Include README, `design-and-evaluation.md`, `ai-tooling.md`, and `deployed.md` with the assignment's setup, design, evaluation, AI usage, URL, health, and cold-start information. | F006; supports F001-F005 | Inspect each document against assignment. | Not Started |
| QR-054 | p. 6, Submission Guidelines | Include an evaluation directory or equivalent with questions, expected answers or rubrics, scripts, and reported results. | F006 | Inspect evaluation artifacts and reproduce results. | Not Started |
| QR-055 | p. 6, Submission Guidelines | Submit through the project dashboard; for groups, only one member submits and a signed final Group Project Agreement page is uploaded when prompted. | F006 | Confirm submission and conditional group agreement. | Not Started |
| QR-056 | p. 6, Plagiarism Policy | Cite others' work appropriately, describe AI tooling used and its strengths/limitations, and remain responsible for correctness, security, and academic integrity. | F006; supports F001-F005 | Review source attribution and AI tooling disclosure. | Not Started |
| QR-057 | p. 1, Project Overview | Build and evaluate an agentic HR policy/operations system using policy RAG, MCP servers, synthetic structured data, and grounded cited responses. | F006; supports F001-F005 | Demonstrate and evaluate the integrated application. | Not Started |
| QR-058 | p. 1, Project Overview | The agentic system must also run locally for development. | F006; supports F001-F005 | Follow documented local setup and run both workflows. | Not Started |
| QR-059 | p. 1, Project Overview | Work individually or in a group of no more than three people. | F006 | Confirm project participant count at submission. | Not Started |
| QR-060 | p. 6, Submission Guidelines | `deployed.md` contains deployed URL, health endpoint URL if available, and free-tier cold-start notes. | F006; supports F005 | Inspect deployment document and check URLs. | Not Started |

## Coverage and qualification notes

- All ten numbered technical sections and the substantive overview, project description, and
  submission requirements have assigned owners. Rows may combine closely related bullets;
  the authoritative PDF remains the source for full context.
- The PDF's five-tool minimum is QR-024; this project's six named tools are a proposed
  feature choice, not a separate Quantic minimum.
- The rubric on pp. 7-8 describes grading levels rather than additional mandatory scope.
  Optional extra services, exact-match metrics, and retrieval enhancements are not mandatory.
- The source permits mock actions or confirmation; the constitution is stricter for
  state-changing operations: synthetic data only, explicit confirmation, and reversible/resettable.
- F006 owns final delivery while earlier features own their component behavior. All "Not Started"
  statuses are the requested initial matrix values, irrespective of specification documents.