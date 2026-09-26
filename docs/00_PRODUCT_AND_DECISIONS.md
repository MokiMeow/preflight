# 00 — Product, evidence and locked decisions

## Product contract

**Preflight rehearses the exact migration on an isolated, populated RDS clone, produces reproducible schema and row evidence, and pauses for an engineer before the same SQL may touch the owned demo source.**

The buyer/user framing, the Migration Rehearsal Agent statement, the 1,000-customer demo, ten MCP tools and original architecture come from [the supplied PRD](../reference/Preflight-PRD.md), especially sections 1, 4, 7 and 11. This kit is an implementation specification built on that source, not a different hackathon idea.

The competitive demonstration is a causal chain, not an unsubstantiated superiority claim: **real database → real restore → observed failure → corrected candidate → deterministic proof → visible denial → exact approved write → verified outcome**. An extra “SQL committed but preserved data changed” case shows why execution success is not correctness. Do not claim unique invention, a measured market size, a quantified outage reduction or an official judging score without evidence.

## Event facts and their confidence

**Event: 26 September 2026, Bengaluru, Asia/Kolkata.** The original PRD is the source for the Migration Rehearsal Agent problem. Fresh research recovered indexed official TrueFoundry event text, not a complete rendered copy of the canonical HackCulture page. Keep that distinction in the submission/provenance record. Sources and retrieval limits are in [08](08_RESEARCH.md).

| Item | Evidence and decision |
|---|---|
| Core requirements | TrueForge, meaningful real-system tools, generated sandbox code and a human checkpoint. Preserve the supplied problem's real RDS rehearsal. |
| Build provenance | Official event text says build during the event; research/planning is allowed. This ZIP is specifications/configuration, not prebuilt product code. Record the actual implementation start. |
| Team and submission | Indexed organizer text: teams of up to four, public runnable repository, README and AI-assistant disclosure. Final invitation/on-site rules override cached text; operator authorizes repository publication. |
| Provisional agenda | 09:00 check-in, 10:00 kickoff, 10:30 walkthrough, **12:00 build start**, 16:00 optional checkpoint, **19:00 submission**, 19:30 demos, 21:00 results. Organizer labels the agenda provisional. |
| Pitch | Indexed organizer text specifies five minutes; be ready to explain the architecture. Confirm the actual stage format at T00. |
| Scoring | Harness work **30**, actually runs **25**, where it stops/human control **20**, worthwhile job **15**, clear demo **10**. This is the published rubric, not our predicted score. |
| AI Gateway | The accessible official Portuguese-path event text explicitly says Gateway is useful but not required to win. Other indexed descriptions emphasize it. **Use it by default; do not falsely claim a mandatory rule.** Reconcile with final event instructions. |

The user's 09:00–19:00 description covers attendance/submission, not necessarily permission to begin implementation at 09:00. Do not impose an artificial reduced-scope project because of that distinction; implement the full dependency plan, starting actual code only when permitted. Preparation, account inspection and infrastructure actions also follow the organizer's actual boundaries.

T00 records the source of truth once. If the canonical page stays inaccessible, use the organizer's final invitation/on-site brief; do not fabricate a complete page scrape or spend the entire build re-fetching a broken URL.

## Stack decisions

| Layer | Chosen implementation | Reason in this project |
|---|---|---|
| User experience and orchestration | TrueForge's bundled UI and saved `preflight` agent | Preserves event/platform fit; approval and tool trace are visible together |
| Language/model | Verified OpenAI model; GPT-6 Sol/high via a working Responses route is the runtime starting choice | Coding-model assignments are separate; endpoint/tool compatibility must pass before choosing the runtime model |
| Model access and visibility | Prefer TrueFoundry AI Gateway, using the actual team route and secret settings | Makes model routing/usage inspectable without exposing database or AWS secrets; direct OpenAI is only an explicit rules-compatible fallback |
| Generated-code execution | Daytona via TrueForge Code Mode | Runs bounded agent-generated Python outside the DB service; secrets stay in the harness/service |
| Application backend | One Python 3.12 MCP service, official Python MCP SDK | Small typed integration surface; direct control of deterministic validation |
| AWS integration | Boto3; EC2 IAM role; Secrets Manager | Real RDS snapshot and restore, scoped credentials |
| Database execution | Psycopg 3 over verified TLS | Exact supported SQL in explicit transactions |
| SQL policy | pglast AST matched to PostgreSQL major | Structural validation, not keyword/semicolon filtering |
| Local state | SQLite plus immutable files on the EC2 volume | Single active run, durable cloud jobs, append-only events without Redis or queues |
| Tests | pytest, real disposable PostgreSQL, MCP client, Boto3 stubs and explicitly separate live tests | Independently prove logic and integration |
| Packaging | uv lock; pinned TrueForge npm package; recorded tool/runtime versions | Reproducibility without guessing tomorrow's transitive versions |

No Next.js/React frontend, LangChain/LangGraph, Kubernetes, Terraform dependency, vector database, embeddings, RAG, browser-controlled SQL console, or second auth product is needed for this build. Infrastructure provisioning is a small reviewed Boto3 bootstrap plus documented settings, created during the event. These exclusions protect a coherent architecture; they are not permission to omit the full safety/demo flow.

For a new synthetic source prefer PostgreSQL **18** with **pglast 8.4**, subject to actual AWS region/instance-class availability. For an already provisioned PostgreSQL **17** source use **pglast 7.18**. Never upgrade a source just to match a parser. Other majors require a verified parser match and tests, not an assumption. The research record explains these version mappings. The source, clone and local integration database must use the same chosen major.

## Numbered implementation amendments

These are **new design decisions in this kit**, not claims that the original PRD already specifies them. They resolve concrete implementation gaps while preserving its product boundaries.

**D01 — Exact-byte intake.** Extend candidate registration with an expected file SHA-256 and an optional base64 UTF-8 payload. Plain SQL text remains accepted with an expected hash. The service hashes decoded bytes before UTF-8 parsing, preserves line endings/comments and rejects any mismatch. A locally generated intake file avoids an LLM calculating or guessing a hash. See docs 02 for the mutually exclusive fields.

**D02 — Explicit revision attachment.** Extend `register_candidate` with optional `run_id` and `parent_candidate_id`. An attached revision is legal only after a conclusively rolled-back failed migration, an unchanged canonical contract hash and a fresh full-baseline equality check. A changed contract needs a fresh rehearsal; do not weaken an existing run's acceptance conditions. Candidate insertion/attachment is atomic. A committed-but-invalid clone needs a fresh rehearsal, not an automatic down migration.

**D03 — Nested SQL safety, not top-level checking alone.** The v1 SQL subset remains ALTER TABLE and UPDATE. Recursively constrain expressions, DDL subcommands and target objects. Reject unreviewed triggers/rules, row-level security, partitions/inheritance and dangerous nested constructs. This is a bounded synthetic-data migration format, not a safe executor for arbitrary PostgreSQL programs.

**D04 — Full static-source drift guard.** Preserve the PRD's preserved-column row comparisons, but also fingerprint every supported pre-existing column of the declared tables for source drift. Otherwise a column read by an UPDATE could change without appearing in the preserved subset. Unsupported existing types make source-apply eligibility unavailable rather than silently disappearing from the guard.

**D05 — Close the source recheck/write race.** Inside the source transaction, acquire target-table locks in a deterministic order, then freshly compare schema/full-baseline evidence and execute. An advisory lock alone is not sufficient against unrelated writers. The demo uses conservative locks and short timeouts; it does not establish production zero downtime.

**D06 — Unknown commit is a first-class outcome.** Persist an apply intent before executing source SQL. Add `APPLY_OUTCOME_UNKNOWN` for lost commit acknowledgement or an interrupted APPLYING state. Do not replay. `APPLY_FAILED` means rollback is confirmed; `APPLIED_NEEDS_ATTENTION` means commit is confirmed but later verification is not. This delivers guarded at-most-once automated attempts, not an impossible unconditional exactly-once guarantee across SQLite and PostgreSQL failures.

**D07 — Separate immutable evidence from mutable lifecycle.** Hash a canonical report payload that excludes its own hash. Keep later source-apply/cleanup receipts separate. An old report's PASS is historical evidence; its report-time eligibility does not override current state, candidate, drift or approval. Mark a drifted run `STALE` rather than rewriting its report.

**D08 — Whole-script and data-size budgets.** A per-statement PostgreSQL timeout alone is not a whole-migration deadline. Enforce both, check elapsed time before commit, and cancel on a monotonic deadline. Bound row counts and full-scan bytes. Never use sampling to produce PASS.

**D09 — Correct report coverage.** The supplied contract is strengthened with explicit expected schema changes and a schema-level NOT NULL check, not just a query observing zero current nulls. The fixture contract is version 1.1. A legacy contract lacking this coverage is accepted only as incomplete evidence/WARN until a human registers a complete revision.

**D10 — Recovery distinguishes infrastructure from mutation.** Snapshot/restore polling may reconcile automatically using durable IDs and tags. A worker must not automatically repeat clone/source migration execution after an uncertain crash. Per-row comparison maps stay in bounded memory; if required maps are lost before sealing, the run cannot pass and a fresh rehearsal is required.

**D11 — Build agents are not runtime agents.** Parallel Codex workers accelerate implementation; they do not become extra privileged runtime database agents. The deployed TrueForge agent has dynamic subagents disabled and only the ten exposed Preflight tools.

**D12 — Model availability and database truth are separate.** Clarify the PRD's blanket failure sentence: an OpenAI outage cannot manufacture a completed agent run, but it also must not retroactively change an already computed deterministic verdict or immutable report. The service does not call a second model to decide correctness. Store `agent_delivery_status` in the session/evidence record separately from the DB verdict. A disconnected/model-failed session is not a successful end-to-end demo; it makes no autonomous source apply. A later human request must resume through the real approval gate and current guards.

**D13 — Credential and spending bootstrap is explicit.** No application is created or account provisioned by this kit. Source apply defaults disabled; cloud creation waits for an account/region/resource/spend authorization. Secrets are configured outside prompts. The build agent proceeds with unblocked local tasks rather than asking the user to redesign the system.

**D14 — Version truth beats stale examples.** The Python MCP v2.2.0 source tag and TrueForge 0.2.1 package metadata at the PRD commit were fetched. Installation, package-index freshness and cross-component behavior are still T01/T20 checks. Freeze one tested set; never confuse source verification, latest-page caching, account entitlement and actual runtime evidence.


**D15 — Explicit Gateway/API routing.** Prefer a team-scoped Gateway route, but the runtime adapter and endpoint family must match the model's tool API. Pinned TrueForge source sends its `openai` adapter through Responses; its `custom`/`truefoundry` compatible adapters follow a different path. Try Gateway + OpenAI Responses + Sol/high first. A separately operator-approved compatible-only route can use Sol/none, explicitly not the requested High route; never send Astra tool calls through Chat Completions. See docs 05. This is a concrete integration design, not a promise of account access.

**D16 — Evidence-chain observability without data leakage.** Correlate the run, candidate, report hash, agent session, sandbox execution, MCP request, AWS operation and model-route trace when each is actually observed. Immutable database evidence remains authoritative; provider delivery/usage metadata is supplemental, not a PASS condition manufactured from model output. Never expose raw row contents or credentials in telemetry.

**D17 — Sol-first coding policy (V3 replaces V2's Astra-heavy assignment).** All 36 primary tasks use GPT-6 Sol/high or GPT-5.6 Sol/high. Lead/DB/cloud use 6 Sol; integration/report work uses 5.6 Sol; ordinary independent review uses Sol. Astra/high is limited to two admitted focused review/critical-blocker sessions, read-only, with Sol making the fixes. Three children plus the lead, explicit worktrees and one shared cloud writer remain the default. No automatic premium-mode/effort upgrade or runtime Astra. The workflow limit is not a vendor billing cap. Runtime remains one saved TrueForge agent.

**D18 — Capability probes before feature dependence.** Native Goals, role models, worktree support, provider tools and protocol features must be observed in the installed environment. A documented fallback preserves acceptance, not a hidden scope downgrade. Experimental Codex ergonomics are optional; the ledger, ordinary Git isolation and verification gates are always available.

**D19 — Restored-copy limits stay visible.** RDS availability does not mean warmed storage. Preserve the source engine major/encryption and explicit private network settings; reject unsupported restored objects before running permitted SQL. Timing is clone timing, not proof of source downtime or an online rollout strategy.

**D20 — Column-level acceptance coverage.** Table inclusion and unchanged row count are not sufficient. Deterministically extract every written column from the accepted SQL. Each existing value mutation must be covered by preservation or a supported mandatory intended-value assertion; each new column also needs explicit expected schema. Null/unique/count checks alone do not specify an intended value. Missing coverage is WARN and cannot become PASS. This is an additional product rule, not an upstream guarantee.

**D21 — Offline, trust-aware report verification.** Add a local CLI that validates a sealed JSON report, its required-evidence manifest and deterministic verdict. An independently supplied expected digest can detect a forged replacement; without it, report only self-consistency, not authenticity. No network/credentials/model, no extra MCP tool, no claim of cryptographic human approval or current source eligibility.

**D22 — Review before live write; delta review afterward.** T24 now depends on accepted T27 independent boundary review. Close all relevant critical/high findings and rerun the affected tests before the first authorized live source apply. An expert review is not the operator's approval. A2 checks only material safety changes, not the unchanged repository again.

**D23 — Observable agent behavior and bounded waiting.** Add trace-based cases for injection, incomplete coverage, denial, retries, pending cloud state and unknown outcomes. A model's success sentence is not an oracle. Use bounded read-only Code Mode polls and emit state changes, not one model turn per describe call. Restore polling expiry remains pending; it never starts a replacement job or migration automatically.

**D24 — Evidence-based differentiation.** Existing migration testing and SQL dry-run tooling is acknowledged. Preflight's demonstration combines actual RDS restore, protected-value and schema checks, coverage, a visible human stop, outcome/replay discipline and inspectable sealed evidence. Do not claim first invention, universal database support or quantified outage prevention. Focus on the published rubric through observed behavior, not extra logos/frameworks.

**D25 — Operator-supplied Gateway model override (26 September 2026).** The operator explicitly supplied `https://gateway.truefoundry.ai` and alias `vm-polaris/openai`, and revoked subscription authentication for runtime testing. A real Responses probe resolved this alias to `gpt-4o-mini-2024-07-18`; it is not a Sol/high route. Use the pinned OpenAI Responses adapter and omit the unsupported reasoning parameter. Only the exact saved resource `openai/gpt-model` receives this explicit non-reasoning exception; coding/review model assignments remain Sol/high. A real streamed function roundtrip and native TrueForge/MCP read-only sessions succeeded. These observations do not waive the approved Code Mode runtime, RDS restore, deterministic reports or genuine human gates. D26 subsequently replaces Daytona with the native local sandbox.

## Non-negotiable product acceptance

The required result includes actual AWS snapshot/restore, both migration outcomes, row and schema evidence, the generated native local Linux Code Mode trace (operator amendment D26), literal approval denial and allowance, replay/tamper/drift refusal, recovery semantics, privacy checks, report retention and deliberate cleanup. A local PostgreSQL demonstration is necessary testing but is **not** a replacement for the RDS proof. A screenshot of a green badge is not evidence that a write was gated.

The extra committed-but-wrong-data test, stale-source test and replay rejection are important differentiators and part of the planned validation work. They do not require a second product, new deployment platform or marketing dashboard.

## Value and limits to communicate

Preflight reduces uncertainty for the specific rehearsed SQL/data snapshot by making evidence inspectable. It does not prove how a later production workload behaves. Live lock contention, application compatibility, traffic, replication, long-running production transactions, external side effects and later data drift remain unproven. No percentages of risk reduction or performance improvement are promised.

The “win” argument is the observed causal proof and disciplined human control, not the number of frameworks, agent personas or slides. Present the project as a strong working controlled demo with clearly stated production-hardening boundaries.

## D26 — Operator-authorized local Code Mode runtime (26 September 2026)

The operator replaces the paid Daytona requirement with TrueForge 0.2.1's native local Linux sandbox on the existing private EC2 host. This explicitly supersedes Daytona-specific runtime acceptance in the implementation kit; the original PRD remains byte-for-byte preserved as historical provenance. Acceptance now requires actual local Code Mode/Python MCP traces, isolated session files, credential and metadata/network denial, bounded execution and unchanged literal source-apply/cleanup approvals. Unsupported isolation must fail closed; unsandboxed execution is not an acceptable fallback. No Daytona credential, account or service call is required for this approved runtime.

## D27 — Operator-authorized AWS continuation ceiling (26 September 2026)

The operator authorizes at most USD100 for AWS continuation, with no account-plan upgrade and no extra source/reset. Record the fixed ceiling and retain singleton clone/snapshot caps. Cost admission requires current, complete observations and conservative accrued/reserved cost bounds; unknown or stale spending facts refuse new billable creation. A budget alert or positive configuration number is not an instantaneous AWS hard cap. Existing resource retention remains chargeable and is reported; no automatic source deletion or approval bypass is authorized by this ceiling.

## D28 — Operator revokes the AWS dollar ceiling and requests the full live result (26 September 2026)

The operator explicitly revokes D27's USD100 maximum and authorizes the AWS work required to complete the planned live result. Do not report a remaining fixed dollar cap or block the approved singleton snapshot/clone workflow solely because no numeric ceiling exists. Continue to use the exact authorized account, owned synthetic source, smallest compatible resources, one active run, one run-owned clone and the existing snapshot-count limit; observe and report actual resource state and costs when available. This is not permission for unrelated resources, an account-plan upgrade, a source reset, repeated create attempts, or broad teardown. The literal `apply_to_demo_source` and `cleanup_run` human gates, all deterministic eligibility checks, recovery retention, private networking and unknown-outcome rules remain unchanged. D28 supersedes only D27's numeric spending ceiling.
