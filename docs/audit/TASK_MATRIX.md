# All 36 dependency-ordered tasks

21 tasks retain local-verification status; 15 have external acceptance blockers. None is claimed CONNECTED_VERIFIED for the full product. T32 is corrected to blocked. Local status is not complete branch/scenario coverage.

## T00 — Establish event rules, clean workspace and build provenance

**LOCAL_VERIFIED** · owner lead · gpt-6-sol/high · dependencies: none

Acceptance: The product/track and source attribution are recorded; implementation starts only within the allowed event window. Unavailable event text is a named rule-check blocker, not invented rules.

Implemented/observed: Organizer coding-start authorization recorded; immutable PRD and Git provenance retained. Final event rules remain incompletely confirmed.

Primary paths: `src/preflight/models.py`, `src/preflight/service.py`, `src/preflight/storage.py`, `tests/unit`, `tests/postgres/test_service.py`

Pending: Complete any unproven clauses named in the 153-scenario matrix; LOCAL_VERIFIED is local task scope, not connected demo completion.

Specified subtasks:

1. Inspect the extracted workspace, existing Git status and user configuration without overwriting unrelated work. Confirm the allowed implementation start; retain the original PRD unchanged.
2. Read actual organizer rules when accessible. Record time window, mandatory products, submission fields, team/repository rules and AI disclosure. Keep unknowns explicitly unknown.
3. Create the single task ledger and a dated event-start entry; do not claim prior application code or cloud resources were created by this kit.
4. Record the indexed organizer rubric, provisional check-in/build/submission times, public-repository requirement and final on-site overrides. AI Gateway is the preferred integration, not a falsely asserted mandatory rule.

## T01 — Resolve and record one compatible toolchain

**LOCAL_VERIFIED** · owner lead · gpt-6-sol/high · dependencies: T00

Acceptance: Imports, transport initialization and structured result decoding work. No guessed API methods or mixed Python SDK API surfaces; different Python/JS package majors are allowed only with demonstrated protocol compatibility. A lock candidate exists; full lock freezes after integration.

Implemented/observed: Locked Python/Node/TrueForge/MCP/PostgreSQL-compatible toolchain installed and tested; observed worker role models match assigned Sol/high settings.

Primary paths: `src/preflight/models.py`, `src/preflight/service.py`, `src/preflight/storage.py`, `tests/unit`, `tests/postgres/test_service.py`

Pending: Complete any unproven clauses named in the 153-scenario matrix; LOCAL_VERIFIED is local task scope, not connected demo completion.

Specified subtasks:

1. Inspect installed Python, uv, Node, pnpm and Codex versions. Prefer Python 3.12 and supported Node 22.14+; use Linux/WSL2 or the Linux service host consistently.
2. Check published TrueForge baseline package metadata and actual Python release metadata. Select the source-major/parser pair; record all exact versions and package integrity values.
3. Run a small official-SDK Streamable HTTP probe with an official client; use v2 MCP APIs consistently. This is a compatibility probe, not fake product evidence. If a documented compatibility adjustment is needed, isolate it here.
4. Check Codex 0.157.0 release baseline and effective project/role settings, account model availability, Goals/skills/worktree support, and root/child sandbox/tool permissions. Write capability-probe.local.json; source-verified is not installed-tested.
5. Check actual package indexes and pinned source instead of stale latest-page caches. Validate MCP v2 imports and protocol negotiation, including the installed TrueForge JS client. The two SDK package majors do not have to match.
6. Verify GPT-6 Sol/high and GPT-5.6 Sol/high access in the actual Codex surface; match task/role defaults and record effective models. Check model-policy admission without spending an Astra turn. Keep Fast/Pro/Ultra and effort upgrades off unless explicitly requested.

## T02 — Freeze shared domain models and service interfaces

**LOCAL_VERIFIED** · owner lead · gpt-6-sol/high · dependencies: T01

Acceptance: Types serialize only permitted public data; all ten tool schemas and error vocabulary have a single source. Workers can implement adapters against stable interfaces.

Implemented/observed: Frozen strict shared inputs, domain records and all ten output envelopes; isolated writer ownership and lead integration.

Primary paths: `src/preflight/models.py`, `src/preflight/service.py`, `src/preflight/storage.py`, `tests/unit`, `tests/postgres/test_service.py`

Pending: Complete any unproven clauses named in the 153-scenario matrix; LOCAL_VERIFIED is local task scope, not connected demo completion.

Specified subtasks:

1. Create typed records for candidates, runs, state transitions, check sets, reports, receipts, errors and tool envelopes. Define strict 1.1 contract validation and private/public evidence separation.
2. Implement interface skeletons and ownership boundaries, enumerate every legal transition and standard error code. Resolve sync adapters versus async transport explicitly.
3. Create an initial Git commit, share the interface revision with workers, and reserve public schema changes to the lead.
4. Define the trace envelope, provider/session delivery status and protocol compatibility record without changing the immutable DB verdict. Keep source approval outside build automation.
5. Freeze deterministic write-set and coverage entry schemas plus offline-verifier output. Coverage is column-level: each mutable existing column is preserved or has a supported mandatory whole-column value assertion; every new column also has explicit schema and value expectations.

## T03 — Implement configuration, doctor and runnable service shell

**LOCAL_VERIFIED** · owner lead · gpt-6-sol/high · dependencies: T02

Acceptance: Doctor never writes or exposes secrets, missing required values fail clearly, malformed input fails closed, and intake hashes agree with an independent SHA-256 command.

Implemented/observed: Settings, local readiness doctor, loopback MCP serving and CLI commands implemented. Doctor does not independently prove live cloud/network health.

Primary paths: `src/preflight/models.py`, `src/preflight/service.py`, `src/preflight/storage.py`, `tests/unit`, `tests/postgres/test_service.py`

Pending: Complete any unproven clauses named in the 153-scenario matrix; LOCAL_VERIFIED is local task scope, not connected demo completion.

Specified subtasks:

1. Create pyproject, uv environment, package entry point, strict settings and pytest markers. Add doctor with local/cloud/apply readiness separated and source apply disabled by default.
2. Implement safe nonsecret configuration loading, OS/process ownership and a responsive transport entry point. Use typed not-ready responses until each use case is implemented, never fake successful business results.
3. Create candidate-intake CLI to read bytes and generate exact base64/hash tool input without a source connection.
4. Doctor distinguishes local, AWS, Gateway/API, Daytona and approval readiness; secret presence checks reveal no values. Do not count a text-only model reply as tool compatibility.

## T04 — Authorize and plan the bounded AWS footprint

**BLOCKED_EXTERNAL** · owner cloud · gpt-6-sol/high · dependencies: T00

Acceptance: Plan IDs/region belong to the team; source contains synthetic data only or is to be created; permission/spend authorization is recorded. Local work continues if this is externally blocked.

Implemented/observed: Digest-bound budget/scope plan and operator approval validation implemented; no resource spend inferred.

Primary paths: `src/preflight/aws_rds.py`, `src/preflight/jobs.py`, `infra`, `tests/cloud`

Pending: Run actual dependency-ordered connected acceptance with approved scope and operator inputs; see report ordered actions. No cloud spend, publication, source write or cleanup permission inferred.

Specified subtasks:

1. Discover configured AWS account/region using authenticated read-only calls. Consolidate genuinely missing account, source, network, permissions and spending inputs once.
2. Produce an explicit resource plan for one source, one service host and bounded run-owned clones/snapshots. Record create versus reuse, costs not yet known, approved limits and retention.
3. Separate bootstrap administrator privileges from runtime instance-role privileges. Do not create billable resources until the operator authorized the actual scope.
4. Record build-provider budget separately from runtime API and AWS budgets. Prefer gp3 for newly provisioned synthetic RDS storage; verify the region engine/class/KMS choices instead of assuming sponsor credits.

## T05 — Provision or validate private host, source and runtime identity

**BLOCKED_EXTERNAL** · owner cloud · gpt-6-sol/high · dependencies: T01, T03, T04

Acceptance: AWS describes the owned source and host; RDS is private, SG paths are correct, IAM identity is expected and no static key is deployed. Pending AWS readiness is shown honestly.

Implemented/observed: Approved IAM/network/secrets/image prerequisite validation and scoped host/source bootstrap implemented with restart reconciliation; deployment prerequisites are reused, not implicitly created.

Primary paths: `src/preflight/aws_rds.py`, `src/preflight/jobs.py`, `infra`, `tests/cloud`

Pending: Run actual dependency-ordered connected acceptance with approved scope and operator inputs; see report ordered actions. No cloud spend, publication, source write or cleanup permission inferred.

Specified subtasks:

1. Create/reuse the approved VPC networking, restricted security groups, DB subnet group, EC2 host and allowlisted RDS PostgreSQL source. Start asynchronous source creation early while local lanes continue.
2. Set up the instance profile, separate bootstrap/runtime roles, actual least-privilege database logins and named secrets, verified TLS CA and persistent private service directories. Connection-only probes may run before the fixture tables exist. Never grant public DB, 8000 or 8790 access.
3. Record actual resource IDs and engine/class availability. Keep fixture table creation for the explicitly authorized seeding step when its implementation is ready.
4. Verify correct RDS CA/hostname and restore network groups; wrong CA/hostname must fail. Keep human UI tunneled and MCP private. Inventory third-party licenses before public packaging.

## T06 — Build immutable candidates, durable state and idempotency

**LOCAL_VERIFIED** · owner lead · gpt-6-sol/high · dependencies: T02

Acceptance: Concurrent registrations/transitions do not duplicate effects; altered idempotency inputs fail; path traversal and overwrite fail; crash/orphan artifact behavior is explicit.

Implemented/observed: Immutable exact-byte SQL/contract artifacts; durable SQLite CAS, idempotency and atomic publication/restart safety.

Primary paths: `src/preflight/models.py`, `src/preflight/service.py`, `src/preflight/storage.py`, `tests/unit`, `tests/postgres/test_service.py`

Pending: Complete any unproven clauses named in the 153-scenario matrix; LOCAL_VERIFIED is local task scope, not connected demo completion.

Specified subtasks:

1. Implement SQLite WAL repositories, foreign keys, transaction/CAS transitions, events, request idempotency and process/run locks.
2. Implement byte-preserving candidate registration and safe immutable artifact writes. Hash canonical contract separately from optional original-file bytes.
3. Add report/apply-intent/receipt persistence schemas and atomic file-publication recovery. Keep row maps out of persistent serialization.

## T07 — Implement recursive PostgreSQL AST and object policy

**LOCAL_VERIFIED** · owner database · gpt-6-sol/high · dependencies: T02

Acceptance: All policy negative cases in test group P fail for the right code, quoted semicolons are parsed correctly, and both intended migrations plus the deliberate preserved-data mutation parse as specified. Column write-set extraction is deterministic and incomplete acceptance coverage is identified.

Implemented/observed: Recursive pglast PG18 grammar now has exact negative coverage for all catalogued forbidden statement/expression/target branches; unsupported object capabilities are refused on disposable PostgreSQL.

Primary paths: `src/preflight/db.py`, `src/preflight/evidence.py`, `src/preflight/sql_policy.py`, `tests/postgres/test_database.py`

Pending: Complete any unproven clauses named in the 153-scenario matrix; LOCAL_VERIFIED is local task scope, not connected demo completion.

Specified subtasks:

1. Inspect actual parser nodes for supported good/bad/wrong-data fixtures. Implement a positive nested grammar allowlist and explicit supported ALTER subcommands.
2. Reject transaction controls, nested statements, functions, FROM/RETURNING, dynamic constructs and undeclared targets. Keep exact original script bytes for execution.
3. Implement metadata policy checks for ordinary tables, built-in types, primary keys and unsupported triggers/RLS/rules/partitions/foreign-key graphs.
4. Extract the declared written columns and relevant reads from accepted ASTs; combine with catalog metadata without LLM inference. Unsupported grammar remains rejected. Return coverage gaps separately from SQL-policy errors; missing coverage cannot become PASS.

## T08 — Build real DB sessions, fixtures and transactional runner

**LOCAL_VERIFIED** · owner database · gpt-6-sol/high · dependencies: T03, T07

Acceptance: Bad SQL rolls back with unchanged data/schema; good SQL commits; no SQL DETAIL or credentials leak; multi-statement failure and whole-script deadline cases pass against real PostgreSQL.

Implemented/observed: Verified TLS/runtime privilege checks, fresh explicit transactions, row/byte/catalog/whole-capture deadlines, rollback and unknown-outcome semantics; exact disposable PostgreSQL regressions.

Primary paths: `src/preflight/db.py`, `src/preflight/evidence.py`, `src/preflight/sql_policy.py`, `tests/postgres/test_database.py`

Pending: Complete any unproven clauses named in the 153-scenario matrix; LOCAL_VERIFIED is local task scope, not connected demo completion.

Specified subtasks:

1. Create a real disposable PostgreSQL database on the chosen major. Implement the 1,000-row deterministic synthetic fixture with integer id, synthetic email and timestamptz.
2. Create separate read-only and table-owner migration roles. Implement endpoint/TLS checks, exact-script execution, result-set draining, lock/statement/whole-script deadlines and sanitized errors.
3. Exercise confirmed rollback, successful clone commit and pre-commit validation callback behavior for source mode; use only disposable databases at this stage.

## T09 — Implement canonical row/schema evidence and typed checks

**LOCAL_VERIFIED** · owner database · gpt-6-sol/high · dependencies: T08

Acceptance: Identical logical data hashes identically despite row ordering; genuine differences change evidence; no unsupported or partial dataset can pass; reports expose aggregates only.

Implemented/observed: Controlled repeatable-read capture, canonical order-insensitive hashes, normalized schema/OID semantics, specific missing/inaccessible metadata failures, private key maps and complete typed coverage.

Primary paths: `src/preflight/db.py`, `src/preflight/evidence.py`, `src/preflight/sql_policy.py`, `tests/postgres/test_database.py`

Pending: Complete any unproven clauses named in the 153-scenario matrix; LOCAL_VERIFIED is local task scope, not connected demo completion.

Specified subtasks:

1. Implement consistent baseline capture, stable schema normalization and type-tagged PK/preserved/full-existing row hashes with bounded private maps.
2. Implement full key-set comparison, preserved-column changes, explicit schema delta validation and every supported typed check.
3. Test timestamp zones, null-versus-text, Unicode/CRLF, changed keys, unsupported types, incomplete scans and lost in-memory evidence.
4. Evaluate whole-column intended-value assertions and preserved-column equality separately. No-null/count/unique checks alone cannot certify an intentional value change. Capture each source/clone baseline under one consistent read-only snapshot per database, not separately committed count/hash reads.

## T10 — Implement the pure verdict and eligibility rules

**LOCAL_VERIFIED** · owner lead · gpt-6-sol/high · dependencies: T06, T09

Acceptance: Every verdict test passes and every mandatory missing/failed condition disables apply. Historical PASS does not override STALE or cleanup/unknown states. No undeclared or weakly asserted value mutation can receive PASS.

Implemented/observed: Pure complete-manifest PASS/WARN/BLOCK oracle; row-count/no-null/uniqueness weak checks cannot certify unprotected value intent or acquire a source writer.

Primary paths: `src/preflight/models.py`, `src/preflight/service.py`, `src/preflight/storage.py`, `tests/unit`, `tests/postgres/test_service.py`

Pending: Complete any unproven clauses named in the 153-scenario matrix; LOCAL_VERIFIED is local task scope, not connected demo completion.

Specified subtasks:

1. Encode mandatory check inventory and precedence BLOCK > WARN > PASS; separate execution outcome, report verdict, run phase and current apply eligibility.
2. Validate complete coverage, infrastructure provenance, exact artifacts and all budgets. A model narrative cannot set any of these fields.
3. Create exhaustive table-driven cases, including empty check list, not_run, SQL failure, committed-but-wrong values and a valid complete fixture.
4. Make COVERAGE_INCOMPLETE a WARN reason when no required failure already forces BLOCK. Carry coverage entries into sealed payloads and require complete supported column coverage for report-time eligibility.

## T11 — Implement sealed JSON evidence and readable report rendering

**LOCAL_VERIFIED** · owner integration · gpt-5.6-sol/high · dependencies: T02, T10

Acceptance: Report digest verifies independently, no self-reference exists, report-time/current eligibility are clearly distinct, and no raw customer row appears in output. Offline verification detects tampering and distinguishes trusted-digest match from unanchored self-consistency without network access.

Implemented/observed: Payload-only sealed digest, escaped Markdown, strict offline verification and trusted/unanchored distinction; no current-source claim.

Primary paths: `src/preflight/report.py`, `src/preflight/offline.py`, `integration`, `scripts`, `tests/trueforge`

Pending: Complete any unproven clauses named in the 153-scenario matrix; LOCAL_VERIFIED is local task scope, not connected demo completion.

Specified subtasks:

1. Implement canonical report payload/envelope, payload-only digest and deterministic Markdown. Keep post-apply/cleanup receipts separate.
2. Render source/snapshot/clone provenance, exact hashes, before/after schema, every mandatory check, duration, backup status and untested risks.
3. Test hash recomputation, immutable history, old-candidate retrieval and displayed status that cannot be changed by a model explanation.
4. Add a redacted evidence-chain panel and copyable hashes to the native report. Missing Gateway/Daytona/request IDs remain absent or NOT_OBSERVED, never invented.
5. Implement preflight evidence verify <report.json> [--expected-report-sha256 <trusted-hash>]. Parse bounded JSON strictly, reject duplicate keys, validate the version, payload digest, mandatory evidence and deterministic verdict. It must need no network, DB or model. Without a separately recorded expected hash label self-consistency UNANCHORED, not authenticity.
6. Add an impact/coverage section and an explicit historical-evidence label to the native report. Reuse the existing canonicalization and pure verdict code; include a read-only verification result and trust-anchor status without changing the sealed report.

## T12 — Implement the narrowly scoped RDS adapter

**LOCAL_VERIFIED** · owner cloud · gpt-6-sol/high · dependencies: T02

Acceptance: Unit tests show every restore private and every delete limited to exact owned IDs. No generic delete-by-prefix, arbitrary ARN or model-provided endpoint path exists.

Implemented/observed: RDS allowlist/ownership/private topology/storage/cap checks and scoped create/describe/cleanup adapter; local client stubs only.

Primary paths: `src/preflight/aws_rds.py`, `src/preflight/jobs.py`, `infra`, `tests/cloud`

Pending: Complete any unproven clauses named in the 153-scenario matrix; LOCAL_VERIFIED is local task scope, not connected demo completion.

Specified subtasks:

1. Implement create/describe snapshot, restore/describe instance, list/add tags and verified run-scoped deletion using the installed Boto3 API.
2. Set explicit DB subnet group, restricted SGs, private access, run tags and supported class/engine settings. Verify destination is never source.
3. Use Botocore Stubber or controlled fakes only in unit tests for API arguments, denied permissions, wrong account/tag/ID, throttling and ambiguous responses.

## T13 — Build asynchronous snapshot/restore jobs and restart reconciliation

**LOCAL_VERIFIED** · owner cloud · gpt-6-sol/high · dependencies: T06, T12

Acceptance: start_rehearsal returns promptly; a restarted worker does not multiply snapshots/clones; unknown resources are not adopted; failures keep visible cleanup IDs.

Implemented/observed: Durable asynchronous intent, deterministic names, leases, bounded polling and reconciliation; real shared-SQLite races prove transactional active-run and retained resource caps.

Primary paths: `src/preflight/aws_rds.py`, `src/preflight/jobs.py`, `infra`, `tests/cloud`

Pending: Complete any unproven clauses named in the 153-scenario matrix; LOCAL_VERIFIED is local task scope, not connected demo completion.

Specified subtasks:

1. Persist operation intents, resource names, deadlines and polling status. Enforce single active rehearsal and configured resource caps.
2. Implement bounded retries/backoff for safe describe/create reconciliation, distinguish AWS available from database connectivity, and verify snapshot/clone provenance.
3. Restart at each infrastructure phase in tests; reconcile exact IDs and reject collisions or unowned resources. Never put migration replay in the job worker.
4. Track restore availability separately from SQL readiness/storage initialization. Label clone timing and any cold-read warm-up; never infer production duration or fake storage progress.

## T14 — Connect baseline, clone execution and validation use cases

**LOCAL_VERIFIED** · owner lead · gpt-6-sol/high · dependencies: T06, T07, T08, T09, T10, T13

Acceptance: A complete real-local PostgreSQL bad/good flow works through service use cases; source is unchanged by all rehearsal tools; unavailable evidence never yields PASS.

Implemented/observed: Full real local PG baseline/clone SQL/validation chain connected to service and official HTTP MCP.

Primary paths: `src/preflight/models.py`, `src/preflight/service.py`, `src/preflight/storage.py`, `tests/unit`, `tests/postgres/test_service.py`

Pending: Complete any unproven clauses named in the 153-scenario matrix; LOCAL_VERIFIED is local task scope, not connected demo completion.

Specified subtasks:

1. Implement register/start/get/status/baseline/clone/validation orchestration against adapter interfaces, with source-read versus clone-write factories separated.
2. Ensure baseline happens before mutation and source matches clone; store aggregate evidence while keeping private comparison maps resident.
3. Wire confirmed rollback to a BLOCK report, successful commit to independent validation, and complete PASS to a sealed report plus AWAITING_APPROVAL.

## T15 — Implement safe candidate revision and report history

**LOCAL_VERIFIED** · owner lead · gpt-6-sol/high · dependencies: T11, T14

Acceptance: Bad-to-good can reuse only a demonstrably unchanged clone; every candidate keeps its own hash/report; attempts to reuse a dirty clone require a new rehearsal.

Implemented/observed: Parent/current candidate guards, rollback/baseline-only revision and immutable history; a forced same-parent publication CAS race attaches exactly one child.

Primary paths: `src/preflight/models.py`, `src/preflight/service.py`, `src/preflight/storage.py`, `tests/unit`, `tests/postgres/test_service.py`

Pending: Complete any unproven clauses named in the 153-scenario matrix; LOCAL_VERIFIED is local task scope, not connected demo completion.

Specified subtasks:

1. Implement optional run attachment during registration with current-parent CAS, the unchanged canonical contract hash, and full-baseline equality after confirmed rollback. Changed contracts require a new run.
2. Invalidate old eligibility without deleting old reports. Refuse same-clone reuse after a successful-but-invalid mutation or an unknown outcome.
3. Test stale parent, changed contract/hash, lost private maps, altered preserved/nonpreserved values and replayed requests.

## T16 — Implement the guarded source transaction and durable outcomes

**LOCAL_VERIFIED** · owner lead · gpt-6-sol/high · dependencies: T11, T14, T15

Acceptance: Wrong hash/source, drift, replay or unavailable backup causes no migration write. Lost acknowledgement never causes an automatic second apply; post-commit failure is not called rollback.

Implemented/observed: Source gate-side target/hash/report/backup/drift guards, sorted exclusive locks, fresh comparison, precommit checks, durable receipt and no replay, with exact local PostgreSQL refusal/restart proofs.

Primary paths: `src/preflight/models.py`, `src/preflight/service.py`, `src/preflight/storage.py`, `tests/unit`, `tests/postgres/test_service.py`

Pending: Complete any unproven clauses named in the 153-scenario matrix; LOCAL_VERIFIED is local task scope, not connected demo completion.

Specified subtasks:

1. Create the only source-writer entry point; default feature off. Check literal tool contract, current phase, hashes, source/backup/clone identity and attempt history.
2. Persist apply intent; acquire source table locks; recheck full existing data/schema after locking; run exact SQL plus mandatory checks in one transaction.
3. Implement confirmed rollback/commit/post-commit failure/unknown outcomes and replay refusal. Use disposable local source databases for exhaustive transaction/concurrency tests.

## T17 — Implement guarded cleanup and recovery retention

**LOCAL_VERIFIED** · owner cloud · gpt-6-sol/high · dependencies: T11, T12, T13

Acceptance: All wrong-ID/tag/source/backup/unknown-outcome cases refuse deletion; valid stubbed deletes use exact resources and retain evidence; already-deleted known resources are handled safely.

Implemented/observed: Exact run-owned cleanup and independent recovery retention with local deletion/absence tests; no actual deletion or human gate.

Primary paths: `src/preflight/aws_rds.py`, `src/preflight/jobs.py`, `infra`, `tests/cloud`

Pending: Complete any unproven clauses named in the 153-scenario matrix; LOCAL_VERIFIED is local task scope, not connected demo completion.

Specified subtasks:

1. Implement separate clone/snapshot selections, live ID/ARN/tag checks, mutation-state interlocks, report-retention prerequisite and recovery-backup verification.
2. Block source deletion and pre-apply snapshot deletion after source mutation unless another suitable recovery snapshot is independently confirmed.
3. Model asynchronous deletion separately from run verdict and keep cleanup retries scoped to known IDs. Do not introduce an automatic expiry deleter.
4. Retain the pre-apply recovery snapshot across confirmed or uncertain source outcomes; expired tags are review signals, not permission for blind automatic deletion.

## T18 — Expose and contract-test the complete MCP surface

**LOCAL_VERIFIED** · owner lead · gpt-6-sol/high · dependencies: T14, T15, T16, T17

Acceptance: Official client receives the documented schemas/results; extra fields and unsafe requests fail; no source SQL/credential/general query tool is exposed.

Implemented/observed: Ten strict flat MCP inputs and tool-specific outputs; actual loopback HTTP MCP/JS SDK ping plus typed get_run remain responsive and phase-consistent during one held mutator.

Primary paths: `src/preflight/models.py`, `src/preflight/service.py`, `src/preflight/storage.py`, `tests/unit`, `tests/postgres/test_service.py`

Pending: Complete any unproven clauses named in the 153-scenario matrix; LOCAL_VERIFIED is local task scope, not connected demo completion.

Specified subtasks:

1. Wrap service use cases as exactly ten typed MCP tools with correct annotations, strict input validation, compact structured results and bounded errors.
2. Exercise initialization, tools/list, schema parsing, every permitted operation and meaningful refusals via the official MCP client over Streamable HTTP.
3. Ensure transport deadlines do not translate into unsafe mutation retries; add middleware/auth/loopback checks appropriate to the controlled deployment.
4. Test MCP v2 structured_content, lifecycle, reconnection, request bounds, responsive async transport and privacy of default telemetry. Use documented origin/host protections for the selected transport.

## T19 — Pass the complete local end-to-end gate

**LOCAL_VERIFIED** · owner lead · gpt-6-sol/high · dependencies: T11, T18

Acceptance: The local gate passes without skipped mandatory DB/MCP tests; source and clone isolation, report integrity and replay refusal are independently asserted.

Implemented/observed: Actual HTTP bad rollback/BLOCK to registered good commit/PASS/report causal chain on real disposable local PG.

Primary paths: `src/preflight/models.py`, `src/preflight/service.py`, `src/preflight/storage.py`, `tests/unit`, `tests/postgres/test_service.py`

Pending: Complete any unproven clauses named in the 153-scenario matrix; LOCAL_VERIFIED is local task scope, not connected demo completion.

Specified subtasks:

1. Run from a fresh disposable PostgreSQL fixture through MCP: register bad, baseline, failure report, valid attached revision, good commit/validation and report export. Any injected cloud metadata is labeled local_postgres_test, never real AWS provenance.
2. Exercise source apply guards on a distinct disposable local source; mark the backend plainly as local integration testing.
3. Run the full local suite, lint and type checks; inspect failures instead of shrinking requirements. Preserve exact commands, versions, exit codes and commit.

## T20 — Prove TrueForge, OpenAI and Daytona compatibility early

**BLOCKED_EXTERNAL** · owner integration · gpt-5.6-sol/high · dependencies: T03

Acceptance: A real model response, real sandbox execution and real MCP call are visible. Missing provider access is a precise external blocker, not a mocked success.

Implemented/observed: Pinned TrueForge and Responses probes plus sanitized connected native TrueForge/Gateway/private-MCP read-only get_run and get_source_status receipts. The observed Gateway alias resolved to gpt-4o-mini-2024-07-18, not Sol; saved product agent and Daytona execution remain unobserved.

Primary paths: `src/preflight/report.py`, `src/preflight/offline.py`, `integration`, `scripts`, `tests/trueforge`

Pending: Daytona credentials/runtime and the saved product agent remain unobserved, so full T20 stays BLOCKED_EXTERNAL. The native Gateway/private-MCP receipts prove only the linked read-only compatibility component; they do not authorize source apply or either human gate.

Specified subtasks:

1. Launch the verified TrueForge version on a private endpoint. Configure an actually available OpenAI model and the Daytona provider outside Git.
2. Run a bounded generated-code probe in Daytona and a real MCP handshake through the harness. Inspect actual tool result shape rather than assuming direct-client output shape.
3. Confirm literal approval selectors and Code Mode behavior in the installed version. Keep this compatibility probe separate from final business evidence.
4. Configure a team-scoped TrueFoundry AI Gateway route from its actual Playground snippet. Verify TrueForge provider adapter, upstream endpoint family, exact Gateway model ID, permitted reasoning/sampling options, tool-call IDs and a streamed tool-result roundtrip.
5. Try the OpenAI Responses adapter with the Gateway base URL for GPT-6 Sol/high (tested GPT-5.6 Sol/high fallback; no runtime Astra) when the actual route is supported. The custom/truefoundry compatible adapter is a different path; for Sol Chat Completions tool calls explicitly use none, never send Astra tools there. Record and regression-test any approved fallback.
6. Check denied/invalid provider credentials, quota/rate errors, transport reconnect, log redaction and semantic-cache policy. Preserve the same run through a failure rather than replaying SQL.
7. Keep runtime GPT-6 Sol/high on the verified Responses path or explicitly tested GPT-5.6 Sol/high fallback. Do not put Astra in the runtime. A Chat Completions none fallback is a separate explicit operator choice, never mislabeled High.
8. Implement bounded read-only Code Mode polling with a deadline, backoff and compact state-change summaries. Polling expiry returns pending; it never repeats a migration, creates another clone or crosses the human gate.

## T21 — Deploy the service and saved agent on the EC2 host

**BLOCKED_EXTERNAL** · owner integration · gpt-5.6-sol/high · dependencies: T05, T18, T20

Acceptance: The deployed saved agent calls the real MCP service; the source writer is disabled until the explicit demo policy is enabled; no service port is publicly open.

Implemented/observed: Private host/systemd/SSH deployment and saved-agent templates prepared; installation on actual approved EC2 not done.

Primary paths: `src/preflight/report.py`, `src/preflight/offline.py`, `integration`, `scripts`, `tests/trueforge`

Pending: Run actual dependency-ordered connected acceptance with approved scope and operator inputs; see report ordered actions. No cloud spend, publication, source write or cleanup permission inferred.

Specified subtasks:

1. Deploy locked packages and the actual application to the persistent private host with systemd, correct working directories, restrictive environment files and stable ports.
2. Configure the preflight connector and saved-agent manifest, ten named tools, explicit sandbox true/dynamic-subagents false and literal source/cleanup gates.
3. Verify SSH-forwarded UI, loopback endpoint, TLS database access, IAM identity, logs and startup behavior from the actual host.
4. Export only sanitized effective provider/agent settings and model route evidence. Do not advertise implicit per-turn model routing in the pinned TrueForge release.

## T22 — Create and verify the real synthetic RDS rehearsal

**BLOCKED_EXTERNAL** · owner cloud · gpt-6-sol/high · dependencies: T08, T13, T21

Acceptance: AWS describes the real snapshot and clone as available; the service connects over verified TLS; 1,000 synthetic rows and matching before-state evidence are observed.

Implemented/observed: Real source initializer/ownership safeguards and snapshot/restore worker prepared; only local PG source fixture and AWS stubs observed.

Primary paths: `src/preflight/aws_rds.py`, `src/preflight/jobs.py`, `infra`, `tests/cloud`

Pending: Run actual dependency-ordered connected acceptance with approved scope and operator inputs; see report ordered actions. No cloud spend, publication, source write or cleanup permission inferred.

Specified subtasks:

1. With explicit fixture-bootstrap permission, seed the allowlisted synthetic source using the tested fixture, set table ownership/SELECT grants for the already provisioned runtime roles, then remove bootstrap credentials from runtime.
2. Use the actual agent/MCP start path to create a snapshot and separate private clone. Poll honestly and preserve API/session IDs and timestamps.
3. Verify source/clone identifiers differ, snapshot provenance/tags/engine/network match, and baseline source equality holds. Do not claim a prior restore happened live.

## T23 — Run the real bad-to-good migration proof

**BLOCKED_EXTERNAL** · owner integration · gpt-5.6-sol/high · dependencies: T15, T19, T22

Acceptance: The real AWS-backed sequence produces BLOCK then PASS with distinct SQL hashes and an AWAITING_APPROVAL phase; no source apply has occurred.

Implemented/observed: Real local bad/revision/good proof retained; actual RDS/OpenAI/Daytona trace missing.

Primary paths: `src/preflight/report.py`, `src/preflight/offline.py`, `integration`, `scripts`, `tests/trueforge`

Pending: Run actual dependency-ordered connected acceptance with approved scope and operator inputs; see report ordered actions. No cloud spend, publication, source write or cleanup permission inferred.

Specified subtasks:

1. Run the supplied bad migration through generated Code Mode calls; retrieve its BLOCK report and demonstrate source schema unchanged.
2. Attach the accepted good candidate only after rollback/baseline proof, then execute and validate it. Preserve both immutable report versions.
3. Show 1,000 rows preserved, identical protected hashes, zero account_tier nulls, correct values, actual NOT NULL schema and measured runtime.
4. Correlate real TrueForge, Daytona, Gateway/OpenAI, MCP and AWS trace identifiers with the candidate and sealed report. Label an already completed restore honestly.
5. Link the same run/candidate/snapshot/report identities through observed TrueForge, Daytona and provider traces. Show readable expected-versus-observed coverage; missing identifiers remain NOT_OBSERVED, not guessed.

## T24 — Demonstrate denial, approved apply and replay refusal

**BLOCKED_EXTERNAL** · owner integration · gpt-5.6-sol/high · dependencies: T16, T23, T27

Acceptance: Trace plus read-only DB evidence proves deny/no change and allow/one observed apply. Replay is rejected. Human gate actions are genuine and the receipt ties to exact hashes. T27 review precedes any live source mutation; critical/high boundary findings have no unresolved entries.

Implemented/observed: Local no-writer/refusal/exact apply/replay guards tested; genuine TrueForge Deny/Allow with actual source has not happened.

Primary paths: `src/preflight/report.py`, `src/preflight/offline.py`, `integration`, `scripts`, `tests/trueforge`

Pending: Run actual dependency-ordered connected acceptance with approved scope and operator inputs; see report ordered actions. No cloud spend, publication, source write or cleanup permission inferred.

Specified subtasks:

1. Ask for source apply through TrueForge; let the engineer press Deny. Observe no service call/write connection/source change for that denied request.
2. On a later explicit engineer request invoke the same literally gated tool and let the engineer press Allow. Verify fresh guards, committed exact SQL and source postconditions.
3. Try a repeated request through the properly gated path or demonstrate the backend refusal with safe evidence; never simulate an Allow click or bypass the UI to manufacture the proof.
4. Do not invoke a live source-write demonstration until T27 independent boundary review is accepted and all relevant critical/high findings are repaired and retested. Neither Sol nor Astra may click the product human-approval buttons.

## T25 — Prove successful SQL can still fail correctness, and drift blocks apply

**LOCAL_VERIFIED** · owner database · gpt-6-sol/high · dependencies: T19

Acceptance: Committed SQL is not treated as proof of correctness; old PASS does not authorize a drifted source. The wrong-data clone cannot be reused as if it rolled back. The unasserted-value mutation receives WARN, not PASS, while actual protected-value failure remains BLOCK.

Implemented/observed: Committed protected wrong-data BLOCK, all weak-check coverage combinations WARN, schema/full-data drift STALE and zero-writer refusal proven on disposable PostgreSQL.

Primary paths: `src/preflight/db.py`, `src/preflight/evidence.py`, `src/preflight/sql_policy.py`, `tests/postgres/test_database.py`

Pending: Complete any unproven clauses named in the 153-scenario matrix; LOCAL_VERIFIED is local task scope, not connected demo completion.

Specified subtasks:

1. Run wrong_data.sql on real disposable PostgreSQL: perform the intended new-column migration but overwrite protected email values. SQL must commit; validation must BLOCK.
2. Rehearse a valid candidate, then change a nonpreserved pre-existing source column in a controlled fixture. The stronger full-source fingerprint must refuse apply.
3. Test a competing writer and schema drift under the locked source recheck. Optional AWS repetitions require a separate explicitly authorized fixture/run and honest backend labels.
4. Add a second existing mutable column omitted from preserve_columns and all intended-value checks; an otherwise runnable update must be COVERAGE_INCOMPLETE/WARN, not PASS. Add a control using a supported all_equal expectation; demonstrate a SQL-committed-but-wrong-data BLOCK independently.

## T26 — Exercise crash, timeout and uncertain-commit recovery

**LOCAL_VERIFIED** · owner lead · gpt-6-sol/high · dependencies: T19

Acceptance: Infrastructure resumes safely, mutation uncertainty fails closed, APPLY_FAILED means confirmed rollback, and every uncertain/committed source retry is refused.

Implemented/observed: Local rollback/deadline/commit-ack loss, durable APPLYING restart, no-replay/manual-unknown outcomes, concurrent publication and phase-consistent status tests are observed; complete provider fault permutations remain narrower.

Primary paths: `src/preflight/models.py`, `src/preflight/service.py`, `src/preflight/storage.py`, `tests/unit`, `tests/postgres/test_service.py`

Pending: Complete any unproven clauses named in the 153-scenario matrix; LOCAL_VERIFIED is local task scope, not connected demo completion.

Specified subtasks:

1. Inject restarts during snapshot/restore, baseline capture, clone mutation, report sealing and source apply; classify each operation according to its known outcome.
2. Use real local PostgreSQL plus fault injection for lost acknowledgement and post-commit verification failure. Assert the source execution counter never increases on restart/retry.
3. Check resource reconciliation does not duplicate AWS IDs and lost RAM evidence cannot produce a sealed PASS.

## T27 — Perform independent privacy, IAM and boundary review

**BLOCKED_EXTERNAL** · owner reviewer · gpt-6-sol/high · dependencies: T21, T23

Acceptance: No unresolved critical/high safety issue; literal approval and private deployment are inspected in the real configuration; findings and fixes have evidence. The recorded independent audit is tied to the actual reviewed commit, and any Astra session obeys its admitted slot.

Implemented/observed: Independent Sol local boundary reviews and all reported repair repros closed; actual IAM/private runtime/Daytona/human boundary acceptance still outstanding. A1/A2 unused.

Primary paths: `docs/audit/verification.json`, `docs/11_PROJECT_AUDIT.md`

Pending: Run actual dependency-ordered connected acceptance with approved scope and operator inputs; see report ordered actions. No cloud spend, publication, source write or cleanup permission inferred.

Specified subtasks:

1. Read implementation and actual traces as an adversarial reviewer. Trace every route to source writer acquisition and resource deletion.
2. Scan Git, logs, reports, screenshots, Code Mode output and saved-agent exports for secrets/raw rows. Inspect network/IAM scope and fake-backend reachability.
3. Return concrete findings with file/line, reproduction, severity and expected repair. Owning workers fix issues; reviewer rechecks rather than editing across lanes.
4. Audit MCP/OpenTelemetry payload exposure, Gateway logs, build-agent inherited connectors, provider secrets and public-repository artifacts. Attack an instruction embedded in SQL comments or tool output; it must not change rules.
5. Run routine independent Sol High audit first. Admit A1 only for the compact implemented safety boundary packet; Astra High is read-only and returns findings once. Record the exact reviewed commit and slot before spawning; Sol implements repairs and safely runs reproductions. If Astra is unavailable, disclose independent Sol review without lowering the safety bar. The lead admits the expert session after the ordinary reviewer hands off; the child reviewer does not spawn another agent. A previously consumed slot cannot be reused; use an independent Sol recheck if no slot is available.

## T28 — Polish the report and native TrueForge experience

**BLOCKED_EXTERNAL** · owner integration · gpt-5.6-sol/high · dependencies: T11, T23

Acceptance: A judge can distinguish BLOCK, PASS awaiting approval, denied, applied and unknown outcomes quickly. UI language never implies production guaranteed safe or instant rollback.

Implemented/observed: Escaped report/native connector usability preparation; no complete saved agent/model/Daytona/human experience.

Primary paths: `src/preflight/report.py`, `src/preflight/offline.py`, `integration`, `scripts`, `tests/trueforge`

Pending: Run actual dependency-ordered connected acceptance with approved scope and operator inputs; see report ordered actions. No cloud spend, publication, source write or cleanup permission inferred.

Specified subtasks:

1. Make the existing report readable at presentation scale with clear verdict, provenance, before/after checks, next action and limitations. Do not create a parallel dashboard.
2. Ensure poll output is concise, status names consistent, hashes expandable/copyable where the actual UI supports them, and failure/denial wording honest.
3. Inspect actual rendered reports and approval dialogs; remove misleading green states and test report readability without scrolling through raw JSON.

## T29 — Exercise cleanup guards and record deliberate retention

**BLOCKED_EXTERNAL** · owner cloud · gpt-6-sol/high · dependencies: T17, T24

Acceptance: The actual cleanup/retention state and backup guard are observed. Unit deletion-policy tests are green; any unperformed live deletion is transparently marked NOT_RUN, not hidden.

Implemented/observed: Cleanup guards plus actual disposable local clone deletion retain an independently anchored sealed report and separate cleanup receipt. Real RDS cleanup and human retention/deletion choice remain unobserved.

Primary paths: `src/preflight/aws_rds.py`, `src/preflight/jobs.py`, `infra`, `tests/cloud`

Pending: Run actual dependency-ordered connected acceptance with approved scope and operator inputs; see report ordered actions. No cloud spend, publication, source write or cleanup permission inferred.

Specified subtasks:

1. Inspect actual run resource IDs/tags and saved report integrity. Demonstrate recovery-snapshot retention and refuse unsafe cleanup selections through the guarded path.
2. With the engineer, choose retain-for-judging or approved deletion of a no-longer-needed run-owned clone. Do not destroy the staged demo merely to mark a task green.
3. When deletion is explicitly approved, observe it complete and export the receipt; otherwise record the exact retained resource, owner, reason and next human decision. Never claim deletion was tested when it was only retained.

## T30 — Verify reproducible installation and operational handoff

**LOCAL_VERIFIED** · owner lead · gpt-6-sol/high · dependencies: T19, T21

Acceptance: A fresh environment can install and run the documented local gate. Exact tested versions and deployment commands are captured; application/source-apply readiness is not inferred from installation alone. A fresh offline reader can verify a report against an independently supplied digest without credentials.

Implemented/observed: Fresh locked environment, dependency inventory, package build and isolated installed-wheel checks. Linux systemd/private host operational proof remains external.

Primary paths: `src/preflight/models.py`, `src/preflight/service.py`, `src/preflight/storage.py`, `tests/unit`, `tests/postgres/test_service.py`

Pending: Complete any unproven clauses named in the 153-scenario matrix; LOCAL_VERIFIED is local task scope, not connected demo completion.

Specified subtasks:

1. Freeze uv.lock and TrueForge version/integrity after the green compatibility path. Recreate an isolated environment from locks and run the local suite.
2. Verify startup/doctor/export commands, persistent state, log rotation and restart restrictions. Document account-dependent steps without storing secrets.
3. Inventory dependency licenses and retained artifacts; do not label upstream GPL/LGPL dependencies as though the entire distribution were newly MIT licensed.
4. Freeze uv lock, tested TrueForge package integrity, actual model/endpoint/effort and Codex control version; record an SBOM/license inventory including pglast GPL-3.0-or-later without choosing an incompatible project license by accident.
5. Package the offline evidence-verifier entry point and instructions. Test strict parsing, tampering, a separately supplied expected digest and an unanchored self-consistent artifact in an environment with network disabled. Do not call an unanchored hash proof of an authentic AWS run.

## T31 — Run the final regression and close review findings

**BLOCKED_EXTERNAL** · owner lead · gpt-6-sol/high · dependencies: T25, T26, T27, T28, T29, T30

Acceptance: Final local gate is green; required real integration evidence exists; incomplete external actions are explicit. Test evidence references the actual final implementation commit.

Implemented/observed: Frozen application commit 9f75cc1 passed the complete 485-test gate with zero errors/failures/skips in 236.95s; Ruff and mypy also passed. Connected gates and behavior evaluations remain incomplete.

Primary paths: `src/preflight/models.py`, `src/preflight/service.py`, `src/preflight/storage.py`, `tests/unit`, `tests/postgres/test_service.py`

Pending: Run actual dependency-ordered connected acceptance with approved scope and operator inputs; see report ordered actions. No cloud spend, publication, source write or cleanup permission inferred.

Specified subtasks:

1. Run lint, type checks, unit/real-PostgreSQL/MCP tests and the applicable live evidence checks at the final commit.
2. Check every mandatory acceptance row has an actual evidence file and no high/critical review finding remains open. Separate verified retained cleanup from unobserved live deletion.
3. Rescan final diffs for credentials, disabled tests, mock backends, unreviewed package upgrades and unauthorized architecture changes.
4. Run the V3 regression scenarios and config/agent-evaluation-plan.json cases on the frozen implementation with the actual runtime Sol route. Grade state/tool/receipt evidence, not model-written success claims; retain NOT_RUN for missing live checks.

## T32 — Prepare the complete repository submission

**BLOCKED_EXTERNAL** · owner integration · gpt-5.6-sol/high · dependencies: T24, T28, T30

Acceptance: Submission material is technically reproducible and honest; no placeholders remain except operator-specific configuration; no unsupported winning/production claims.

Implemented/observed: Runnable local submission materials/license inventory prepared; complete submission was incorrectly markedLOCAL_VERIFIED and is nowBLOCKED_EXTERNAL.

Primary paths: `src/preflight/report.py`, `src/preflight/offline.py`, `integration`, `scripts`, `tests/trueforge`

Pending: Run actual dependency-ordered connected acceptance with approved scope and operator inputs; see report ordered actions. No cloud spend, publication, source write or cleanup permission inferred.

Specified subtasks:

1. Write the implementation README: problem, architecture, setup, exact versions/commands, fixture flow, approval boundary, tests, limitations and AI-assistant disclosure.
2. Assemble only sanitized evidence, source and necessary config examples. Record organizer-required fields and actual team details without inventing names/claims.
3. Prepare a clean repository/export. Publish/push only to an operator-approved remote and visibility; do not make state/keys/session stores public.
4. Map submission evidence to the published 30/25/20/15/10 rubric. Keep repository visibility and any public posting as explicit operator-approved actions.
5. Explain product differentiation precisely: real RDS restore plus value preservation, coverage, human control and auditable outcome. Acknowledge existing migration-test/dry-run tools; do not claim first-ever or quantified incident reduction. Include the offline verifier command and current limitation statements.

## T33 — Record and rehearse the evidence-led pitch

**BLOCKED_EXTERNAL** · owner integration · gpt-5.6-sol/high · dependencies: T24, T28, T32

Acceptance: Recording is real and sanitized; the live walkthrough has an identified starting state and human approver; answers distinguish clone evidence from production guarantees.

Implemented/observed: Evidence-led demo/runbook materials prepared; actual recording/five-minute connected pitch and final event format missing.

Primary paths: `src/preflight/report.py`, `src/preflight/offline.py`, `integration`, `scripts`, `tests/trueforge`

Pending: Run actual dependency-ordered connected acceptance with approved scope and operator inputs; see report ordered actions. No cloud spend, publication, source write or cleanup permission inferred.

Specified subtasks:

1. Record the real completed main flow and inspect the recording for credentials/raw rows. Preserve timestamps and explicitly label any previously completed AWS restore.
2. Rehearse the short narrative, expansion proof and judge questions. Replace unsupported claims with observed facts.
3. Prepare an honest contingency for provider or venue-network failure using the recorded real trace, clearly labeled as recorded rather than live.
4. Rehearse a five-minute evidence-led explanation, plus answers to architecture and irreversibility questions. Show recorded versus live steps clearly; no invented timing or uptime claim.
5. Use the stage cut in docs 07: show a complete real causal chain first, then the committed-wrong-data or coverage case and a trusted-hash verification only when the stage format permits. Historical/prepared cloud restores stay explicitly labeled.

## T34 — Perform the final read-only demo-readiness audit

**BLOCKED_EXTERNAL** · owner lead · gpt-6-sol/high · dependencies: T31, T32, T33

Acceptance: The team knows the actual live state and can demonstrate without pretending an old apply is new. No pending source mutation is accidentally triggered by readiness checks. Astra usage stays within the admitted policy; no unobserved cost or review is reported as measured.

Implemented/observed: Local audit/evidence ready; actual real-resource/demo starting state and connected acceptance packet incomplete.

Primary paths: `src/preflight/models.py`, `src/preflight/service.py`, `src/preflight/storage.py`, `tests/unit`, `tests/postgres/test_service.py`

Pending: Run actual dependency-ordered connected acceptance with approved scope and operator inputs; see report ordered actions. No cloud spend, publication, source write or cleanup permission inferred.

Specified subtasks:

1. Inspect current resources, source schema, backup status, saved-agent configuration and evidence hashes. Do not replay an applied migration to “check readiness.”
2. Confirm which session/run is staged for live judging versus recorded evidence and whether the source has already been mutated. A fresh live re-run requires an explicitly reset synthetic fixture/new rehearsal, not hidden state changes.
3. Provide a clear completion report naming passed gates, exact run/candidate/hashes and any remaining external action.
4. Verify final organizer submission details, actual model route, all effective gates, report/receipt hashes, model degradation status and retained resource owner. Do not start another source migration to make the screen look fresh.
5. Review the safety diff since A1. Use A2 only for material boundary changes or an admitted critical blocker; skip an unchanged full rescan. A2 can be spent only once, and a previously consumed critical-blocker slot is not replenished. Record model/usage observations and all skips/substitutions truthfully.

## T35 — Close out resources after the demonstration

**BLOCKED_EXTERNAL** · owner cloud · gpt-6-sol/high · dependencies: T29, T34

Acceptance: Every remaining resource has an explicit owner/retention decision; approved deletions are observed; no evidence or recovery asset disappears through an automatic broad teardown.

Implemented/observed: No Preflight AWS resource creation observed; no real closeout performed or invented.

Primary paths: `src/preflight/aws_rds.py`, `src/preflight/jobs.py`, `infra`, `tests/cloud`

Pending: Run actual dependency-ordered connected acceptance with approved scope and operator inputs; see report ordered actions. No cloud spend, publication, source write or cleanup permission inferred.

Specified subtasks:

1. List all billable run-owned resources and recovery snapshots with owners and current retention reasons. Obtain explicit decisions for remaining deletions.
2. Execute only approved run-scoped cleanup, verify absence where deletion was requested and preserve reports/receipts. Source/host/network teardown is a separate operator-controlled action, not cleanup_run.
3. Record unresolved recovery/unknown-outcome resources rather than deleting them to meet a deadline. Revoke temporary access and retain the sanitized submission.
4. Record remaining vendor/model usage only when observed, separately from AWS resource retention. No extra model sessions or infrastructure recreation merely to produce a cleaner final screen.
