# 06 — Test matrix and acceptance evidence

## Evidence policy

No test result exists merely because this kit names a test. The coding agent must create and execute the tests, capture results and repair failures. Unit mocks prove branching/arguments, not a live AWS restore. Local PostgreSQL proves real SQL behavior, not TrueForge approval or AWS networking. A screenshot proves displayed state, not that a database write was actually prevented.

Use distinct pytest markers: `unit`, `postgres`, `mcp`, `cloud`, `trueforge`. The implementation must expose the following repeatable gates or equivalent documented commands:

```bash
uv run ruff check .
uv run mypy src/preflight
uv run pytest tests/unit -q
uv run pytest tests/postgres -q
uv run pytest tests/mcp -q
uv run pytest -m "not cloud and not trueforge" -q
uv run preflight doctor --json
```

Configure/test the exact commands in the actual pyproject. Do not claim these are already executable from the ZIP. A missing local PostgreSQL service causes the real-PG gate to fail/not-run, **not** quietly skip and mark the complete local gate green. Restrict cloud tests with explicit operator environment/allowlist; never run real source writes from a default test invocation. Live human approval is manual through the actual product gate, not an automated browser click pretending to be the engineer.

An evidence record includes task/test ID, UTC timestamp, actual implementation commit, package versions, environment/backend, command or observed action, expected result, actual result, exit code where applicable, run/candidate/resource references, report/receipt hashes and sanitized file paths. Records may identify AWS resources needed to prove provenance but contain no credentials or row values.

## U — Storage, state and artifact tests

| ID | Scenario | Required assertion |
|---|---|---|
| U01 | Text/base64 intake with trailing newline, CRLF, Unicode comments | SHA-256 matches original bytes; no normalization |
| U02 | Wrong expected hash, invalid UTF-8/base64/NUL/oversize/empty SQL | Candidate rejected before any DB action |
| U03 | Canonical contract vs differently formatted input JSON | Same canonical hash, distinct optional raw-file hash; labels accurate |
| U04 | Unknown contract fields, duplicate JSON keys, unsupported checks, missing PK coverage | Reject or explicit coverage WARN per schema; never a complete PASS |
| U05 | Same request ID repeated / same ID changed payload | Same safe result / IDEMPOTENCY_CONFLICT |
| U06 | Two concurrent start calls | Single active run; resource caps held transactionally |
| U07 | Invalid run/candidate/source ID or path traversal | Refused without a file/DB/cloud side effect |
| U08 | Two workers race phase transition or candidate parent change | Only correct CAS wins; no stale attachment |
| U09 | Report envelope digest verification | Payload-only digest; no self-reference; tamper detected |
| U10 | New candidate report and later apply receipt | Old report bytes/digest unchanged |
| U11 | Crash between report file publication and SQLite reference | Orphan reconciled safely; no false PASS/approval |
| U12 | Accidental public serialization of private evidence object | Raw keys, rows and private maps are absent |
| U13 | Service started against empty/wrong state directory with live resources | Doctor warns/fails; no accidental adoption/replay |

## P — SQL grammar and metadata policy

| ID | Input/condition | Required assertion |
|---|---|---|
| P01 | bad.sql and good.sql | Both pass syntax policy; semantic failure remains observable on clone |
| P02 | Quoted semicolon/comment with word COMMIT | AST interprets correctly; no naive string splitting |
| P03 | Explicit BEGIN/COMMIT/ROLLBACK, psql backslash command | Reject |
| P04 | DO/CALL/COPY/SELECT/DELETE/INSERT/TRUNCATE/GRANT/CREATE/DROP | Reject |
| P05 | CREATE INDEX CONCURRENTLY or unsupported ALTER subcommand | Reject |
| P06 | UPDATE with CTE, FROM, RETURNING, nested query or function call | Reject recursively |
| P07 | Default/generated/identity expression or user-defined cast/operator/type | Reject |
| P08 | Wrong schema/table, unqualified target, unknown column, PK mutation | Reject |
| P09 | Multiple statements where later statement is forbidden | Entire candidate rejected before execution |
| P10 | Supported statement plus malicious SQL-comment instructions | Comments remain inert; tool/approval policy unchanged |
| P11 | Unreviewed triggers/rules/event triggers, RLS, foreign-key/cascade graph, partitions/inheritance | Object policy refuses support, never disables the feature |
| P12 | Unsafe CHECK/exclusion constraint or expression/partial index, user-defined collation | Reject unsupported execution surface |
| P13 | Supported UPDATE of a protected non-PK value | Syntax accepted; preservation violation caught by comparator |
| P14 | Parser/database major mismatch | Readiness fails before migration |

P13 is intentional. The validator must catch a migration that commits and changes a protected value; a policy that rejects every data-changing statement would not prove the actual product behavior.

## D — Real PostgreSQL and evidence

Use a freshly created disposable source/clone pair or resettable fixture databases with explicit local-only guards. Seed 1,000 rows programmatically. Keep fixture generation deterministic and don't rely on global mutable database state between tests.

| ID | Scenario | Required assertion |
|---|---|---|
| D01 | Add a NOT NULL text column to populated table without backfill | PostgreSQL failure; confirmed rollback; pre-state preserved |
| D02 | Add nullable column, backfill, set NOT NULL | SQL commits and schema flag truly NOT NULL |
| D03 | Correct row count but one altered protected email | SQL can commit; preserved-hash check fails; verdict BLOCK |
| D04 | Equal row count but different primary-key set | Missing/extra keys reported as counts; not treated as unchanged |
| D05 | Same rows inserted/retrieved in different order | Canonical aggregate roots match |
| D06 | Integer 1 vs text "1", NULL vs empty text vs text "null" | Distinct encodings/digests |
| D07 | Equivalent timestamptz values in different offsets | Same UTC microsecond encoding |
| D08 | Naive timestamp or unsupported float/JSON/array/custom type | Coverage incomplete; never silent stringification/PASS |
| D09 | Missing PK/table/column or inaccessible metadata | Specific failure/not_run, no fabricated zero count |
| D10 | Scan exceeds rows, bytes or deadline | Stops within budget and cannot PASS |
| D11 | All required checks absent/not_run | WARN or BLOCK according to cause, never PASS |
| D12 | Multiple statements: first mutates, second fails | First mutation rolled back too |
| D13 | Several individually quick statements exceed whole-script limit | Deadline enforced; no PASS based only on statement timeout |
| D14 | Lock contention or cancellation | Safe timeout/known-outcome classification, no leaked DETAIL |
| D15 | DB error that embeds a row value/password-like sentinel | Tool/log/report output contains only safe classification |
| D16 | Legacy contract missing explicit schema expectations | Incomplete coverage; propose revision, never silent upgrade |
| D17 | A nullable column happens to contain no NULLs | no_nulls may pass but column_not_null/schema check fails |
| D18 | Consistent source/clone state but different irrelevant OIDs | Normalized schema fingerprints match |
| D19 | A failed candidate followed by an accepted same-contract revision | Full unchanged baseline checked before clone reuse |
| D20 | Committed-but-invalid clone or lost baseline maps | Same-clone revision refused; fresh rehearsal required |

## A — Source apply, concurrency and recovery

Tests of source apply run on **disposable local source fixtures** unless a separate live gate explicitly authorizes the owned RDS source. A test harness may call service use cases directly to test guards; label that as a service test, never as proof of human approval.

| ID | Attack/failure | Required behavior |
|---|---|---|
| A01 | Source apply feature disabled | Refuse before source writer acquired |
| A02 | Wrong source/account/database or source equal to clone | Refuse |
| A03 | Wrong migration/report hash, altered stored contract or report | Refuse, no write |
| A04 | Non-current candidate or WARN/BLOCK/incomplete run | Refuse |
| A05 | Source schema drift | STALE; no migration applied |
| A06 | Source preserved-data drift | STALE; no migration applied |
| A07 | Pre-existing nonpreserved column drift | Full-data guard catches it even though preservation subset matches |
| A08 | Missing/failed/wrong-source recovery snapshot | Refuse |
| A09 | Competing source writer before versus after table locks | Post-lock comparison is authoritative; no check/write window |
| A10 | Two concurrently allowed apply requests | Only one accepted source attempt; other refused |
| A11 | Same/new request ID after committed source apply | Refuse replay regardless of request ID |
| A12 | Source mandatory check fails before commit | Confirmed rollback → APPLY_FAILED |
| A13 | Source commit confirmed, read-only confirmation fails | APPLIED_NEEDS_ATTENTION; no retry |
| A14 | Commit acknowledgement lost | APPLY_OUTCOME_UNKNOWN; no retry or automated cleanup |
| A15 | Process restarts from durable APPLYING | Unknown until manual resolution; execution count not incremented |
| A16 | Crash before SQL after intent persisted | Conservative unknown/manual resolution is allowed; never guess safe retry |
| A17 | Clone migration interrupted | No automatic replay, no blind “rolled back” claim |
| A18 | Report was PASS, then clone deleted | Current eligibility false; historical report unchanged |
| A19 | Denied request in the real UI | No service execution/write connection; source unchanged |
| A20 | Model/provider failure after a sealed report | Report immutable; agent workflow incomplete, no invented apply |

Use actual concurrent local PostgreSQL connections for A09/A10, not merely a mocked lock method. A deliberately injected adapter exception can test state classification, but a separate real commit-then-connection-loss/postcheck-failure test should confirm the no-replay invariant. Do not claim end-to-end fault tolerance from a unit exception alone.

## C — AWS lifecycle and cleanup

| ID | Scenario | Required assertion |
|---|---|---|
| C01 | Restore request construction | New ID, exact snapshot, explicit subnet/SG/private settings and run tags |
| C02 | Ambiguous snapshot/restore create response | Describe exact existing ID before retry; no duplicate random names |
| C03 | Restart while snapshot/clone pending | Resume observation with same resource IDs |
| C04 | Name exists with another run/account/tag | Refuse adoption/deletion |
| C05 | Throttling, denied IAM/KMS, unsupported class/engine, deadline | Bounded error/backoff, no admin privilege escalation |
| C06 | AWS available but DB TLS connection unavailable | Not READY/BASELINED/PASS |
| C07 | Wrong cleanup clone/snapshot or source ID substituted | No delete call |
| C08 | Missing tag or live ARN mismatch | No delete call |
| C09 | Source applied/attempted, no independent pre-apply recovery backup | Snapshot deletion blocked |
| C10 | Unknown transaction outcome | Automated cleanup blocked |
| C11 | Approved known disposable clone deletion | Observe DELETING then actual absence, if performed |
| C12 | Retained clone for judging | Exact owner/reason/status recorded; no claim deletion occurred |
| C13 | Cleanup after sealed report | Report and separate receipts still verify |
| C14 | Resource cap reached | No extra creation merely to evade a failed run |

C01–C10/C13/C14 need unit/service tests and actual identity/network observations. C11 is a separately recorded live action only when authorized; C12 is a legitimate retention state, not evidence that deletion succeeded. After the demonstration, complete the chosen teardown and update the handoff.

## M — MCP and TrueForge integration

| ID | Scenario | Required assertion |
|---|---|---|
| M01 | Official client initializes Streamable HTTP server | Real protocol handshake and documented structured result |
| M02 | tools/list | Exactly ten business tools with strict input/output schemas |
| M03 | Invalid/unknown/oversize tool input | Typed error, no hidden effect |
| M04 | Real local end-to-end via MCP | Full bad/revision/good/report flow, not direct Python-only calls |
| M05 | TrueForge saved agent uses actual OpenAI provider | Successful real provider/tool trace |
| M06 | Generated Daytona Python chains actual Preflight MCP tools | Real sandbox execution and useful orchestration, no credentials |
| M07 | Code Mode calls gated source apply | Same actual human pause as direct call |
| M08 | Literal gate configuration survives agent save/reload | Both source apply and cleanup visibly gated |
| M09 | Annotation missing/wrong in a controlled negative test | Literal names still govern the selected tools |
| M10 | Engineer denies then later explicitly allows | Real denied/no-write and allowed/exact-write observations |
| M11 | Streaming/progress output | Actual states, bounded polling, no invented percentage/time |
| M12 | Source-read tool used after Allow | Correct new schema/aggregates and matching execution receipt |

For M09 use a disposable test connector or inspect configuration in a controlled integration test; do not weaken the live connector and forget to restore it. Final saved configuration must be inspected again at T34.

## N — V2 integration and coding-workflow verification

These are specified scenarios to implement/observe, **not executed tests**. Some are automated application tests, others are installed-tool/configuration or manual evidence checks. The final packet records the kind and actual result. Local negative tests use disposable fixtures and do not pretend to be live provider evidence.

| ID | Scenario | Required assertion | Task |
|---|---|---|---|
| N01 | Installed Codex and effective configuration | Record actual version/model/permissions; unsupported fields cause an explicit setup failure, not ignored configuration. | T01 |
| N02 | Role model and effort precedence | A task-specific setting is actually effective; a conflicting role file cannot silently override the intended route. | T01 |
| N03 | Independent worker checkouts | Each writer proves its cwd/base SHA/allowed paths; no shared-checkout overlap. | T02 |
| N04 | Child admission and thread retirement | At most three concurrent child threads; completed threads close; no grandchildren by workflow. | T02 |
| N05 | Goal pause/resume and fresh-session recovery | Ledger remains correct; no false completion or replayed external mutation. | T30 |
| N06 | Skill discovery and narrow loading | Four valid frontmatter skills route to existing task docs without loading every specification. | T01 |
| N07 | Inherited connector permissions | Read-only reviewer/DB worker cannot use unrelated privileged MCP tools through inherited access. | T27 |
| N08 | Gateway route and model identity | Actual adapter/API family/upstream ID/saved model resource are recorded and distinct. | T20 |
| N09 | Astra tool-call API mismatch | Astra with Chat Completions tools is rejected at setup; no live-run discovery of this known mismatch. This is a setup/configuration rejection test only; V3 does not call Astra as a runtime model. | T20 |
| N10 | Sol compatible-route reasoning mismatch | Sol Chat Completions tools require explicit none; high is not silently sent or represented as working. | T20 |
| N11 | Unsupported model parameters | Actual outgoing request omits unsupported sampling/log-probability options; permitted effort verified. | T20 |
| N12 | Streamed tool-call roundtrip | Complete JSON arguments, stable call ID, one harmless execution and linked result produce a continued response. | T20 |
| N13 | Provider auth/quota/timeout failure | Errors are visible and bounded; the stored run/SQL candidate are not recreated or replayed. | T20 |
| N14 | Semantic response cache versus prefix cache | No cached action response crosses run/candidate/state; harmless prompt-prefix caching is not misclassified. | T20 |
| N15 | Provider log and export privacy | Gateway/OpenAI/Daytona settings and evidence expose no key, connection string or unintended row value. | T27 |
| N16 | SDK OpenTelemetry leakage sentinel | Automatic spans/log exporters do not transmit secret-bearing inputs/outputs; disabled/default behavior actually checked. | T18 |
| N17 | MCP v2 and Code Mode result shapes | Official client structured_content and harness bridge wrappers decoded according to their own actual schemas. | T18 |
| N18 | Wire protocol interoperability | Actual TrueForge JS client and Python service negotiate successfully despite different package majors. | T20 |
| N19 | MCP reconnection after partial delivery | Business run remains durable; get_run observation is safe; no source SQL retry wrapper. | T18 |
| N20 | Private transport host/origin policy | Selected SDK deployment rejects disallowed host/origin exposure and remains loopback/private; negative test recorded. | T18 |
| N21 | Long SQL/cloud work versus transport health | Health/status stay responsive with bounded jobs; cancellation does not falsely claim rollback. | T18 |
| N22 | Partial/invalid streamed arguments | Incomplete tool arguments cannot create a candidate, run, write or cleanup operation. | T20 |
| N23 | Wrong RDS CA and hostname | Both fail closed independently; successful TLS is hostname-verified, not encryption-only. | T05 |
| N24 | Actual restored storage/encryption/network | Described clone matches approved private storage/KMS/SG settings; magnetic/unsupported configuration fails clearly. | T22 |
| N25 | Lazy loading and clone timing labels | Available is not asserted warm; observed storage state/timing labels have no invented percent or production projection. | T22 |
| N26 | Missing trace identifiers | Unavailable Gateway/AWS/sandbox trace fields stay NOT_OBSERVED; final report identity remains valid. | T23 |
| N27 | Prompt injection in SQL/comments/tool output | Instruction-like data cannot change checks, model permissions, targets or approval requirements. | T27 |
| N28 | Report markup injection | Metadata/error strings are escaped; no script/unsafe HTML/credential-bearing generated link in the native report. | T28 |
| N29 | Dependency inventory and public license claims | Version/integrity/notices recorded; pglast GPL metadata not mislabeled MIT; no claim of legal clearance. | T30 |
| N30 | Final organizer requirements and provider fallback | Actual final rules recorded; Gateway used or explicit rules-compatible fallback disclosed; coding-start provenance honest. | T34 |
| N31 | Recording and public repository privacy | Actual final artifacts reviewed for secrets/row values; publication performed only after authorization. | T32 |
| N32 | Integrated patch evidence differs from worker evidence | Lead reviews allowed paths, merges exact changes and reruns affected integration; worker green alone is not final green. | T31 |

The existing U/P/D/A/C/M tests remain required. Provider-route fallback does not waive their acceptance. Do not claim that the number of scenarios equals executed pytest functions.

## V — Sol-first admission, coverage and offline-proof regressions

All scenarios below are **specifications, initially NOT_RUN**. They supplement the existing 125 scenarios without claiming those earlier tests ran. Each result needs its actual commit, command/trace and backend. Verify workflow admission with configuration/ledger tests; do not burn an Astra session merely to test that the budget counter exists.

| ID | Scenario | Required assertion | Task |
|---|---|---|---|
| V01 | Sol-only primary model policy | All 36 primary assignments and normal role defaults use 6 Sol or 5.6 Sol with High; actual runtime role observations agree. | T01 |
| V02 | Automatic Astra or premium promotion | Model unavailability, slow tasks or normal errors do not promote to Astra, Fast, Pro/Ultra, xhigh or max. | T01 |
| V03 | Expert slot admission and exhaustion | Only unused A1/A2 tickets admit one focused Astra session; a critical investigation consumes a slot; a third requires explicit user extension. | T27 |
| V04 | Expert review scope and handoff | Astra returns findings without implementation, delegation, cloud changes or approval clicks; Sol makes and tests repairs. | T27 |
| V05 | No-change final safety review | Unchanged safety boundary skips another Astra rescan; a material diff is reviewed using an available slot and exact commit. | T34 |
| V06 | Unknown usage or substituted review | No fabricated allowance numbers, savings percentages, Astra identity or performed review; independent Sol substitution is explicit. | T34 |
| V07 | Unasserted existing value mutation | A valid UPDATE to a supported existing column outside preserve_columns and intended-value requirements cannot PASS. | T25 |
| V08 | Weak checks do not cover value intent | Row count, no_nulls and uniqueness without supported intended-value coverage yield COVERAGE_INCOMPLETE/WARN for unprotected value updates. | T10 |
| V09 | Preserved wrong-data failure remains BLOCK | An allowed UPDATE changing a protected value remains executable on the clone and deterministic comparison forces BLOCK. | T25 |
| V10 | Explicit whole-column intended value | Supported mandatory all_equal plus complete schema/preservation requirements passes only when actual evidence matches. | T09 |
| V11 | New-column coverage and real NOT NULL | An added column needs expected schema and mandatory value coverage; zero nulls does not substitute for a schema NOT NULL requirement. | T09 |
| V12 | Coverage fail-closed precedence | Known SQL/required-check failure is BLOCK even with a coverage gap; otherwise missing coverage is WARN, never PASS. | T10 |
| V13 | Requirement-result identity consistency | Duplicate/unknown/missing result IDs and a model-edited mandatory flag cannot evade the frozen requirement manifest. | T11 |
| V14 | Consistent multi-read baseline | Within each DB capture, schema/count/hash measurements share the controlled read-only transaction; source and clone snapshots remain separate. | T09 |
| V15 | Offline strict input parser | Invalid UTF-8, duplicate JSON keys, NaN/infinity, excessive size/depth and unsupported versions are rejected without side effects. | T30 |
| V16 | Offline unchanged trusted report | Valid report and separately provided matching digest yield EXPECTED_DIGEST_MATCH while current apply eligibility stays NOT_EVALUATED. | T30 |
| V17 | Offline payload modified old hash | Changed payload with old report hash fails integrity. | T30 |
| V18 | Offline forged payload with new self-hash | A report modified and rehashed fails against the original independently retained expected digest. | T30 |
| V19 | Offline unanchored report | No trusted expected hash yields SELF_CONSISTENT_UNANCHORED, never authenticated or proof of real AWS execution. | T30 |
| V20 | Offline historical BLOCK and missing checks | A truthful complete BLOCK artifact verifies as historical BLOCK; forged PASS or missing mandatory results fail semantic verification. | T30 |
| V21 | Offline backend and zero network | Verifier preserves backend labels, rejects unknown schema/backend, and runs with no network, AWS/DB credentials or model client. | T30 |
| V22 | Review before real source mutation | T27 acceptance/critical findings closure precedes T24 live write; mocked/local tests do not impersonate human approval. | T24 |
| V23 | Bounded Code Mode cloud observation | Batch limits/backoff/deadline bound polls; pending expiry preserves run and emits a checkpoint, not a new clone or replay. | T20 |
| V24 | No mutation inside polling loop | Only observation tools run in polling batches; apply/cleanup remain separately visible literal human gates. | T20 |
| V25 | Runtime stays on a tested Sol route | 6 Sol/high or tested 5.6 Sol/high; no runtime Astra; compatibility-none route needs explicit operator choice and truthful effort label. | T20 |
| V26 | Trace-based agent evaluation oracle | Actual tool/service/receipt evidence grades each behavior case; a model saying it passed cannot mark a case PASS. | T31 |
| V27 | Material fixes invalidate stale review assurance | Safety-changing fixes after A1 receive targeted independent Sol recheck before any further live apply; A2 is conditional and does not waive findings. | T34 |
| V28 | Nullable intended value semantics | The typed all_equal-to-null check uses explicit null semantics; SQL equality to NULL or vacuous missing-column behavior cannot produce PASS. | T09 |

The separate [agent evaluation plan](../config/agent-evaluation-plan.json) groups representative live/controlled trace checks; it does not replace these service/unit/integration regressions. Expert reviews are not test executions. Critical/high findings remain open until their reproductions and repairs are observed on the integrated commit.

## Required connected acceptance gates

| Gate | Evidence needed | What is insufficient |
|---|---|---|
| G1 — Real agent execution | TrueForge + actual OpenAI adapter/API route + Daytona trace and bridged MCP requests; Gateway evidence when used, disclosed authorized fallback otherwise | Local Python script named “sandbox” |
| G2 — Real AWS copy | Source/snapshot/new private clone IDs, tags, actual describes and TLS baseline | Screenshot of a manually copied local database |
| G3 — Real migration evidence | Bad BLOCK and good PASS reports from actual RDS clone with 1,000 rows and schema/hash checks | Successful SQL exit code or model-written verdict |
| G4 — Human control | Deny/no source change; later Allow/exact source write; immutable receipt | `approved:true` test flag or fake UI button |
| G5 — Defensive correctness | Executed hash/replay/drift/wrong-data/unknown-outcome tests; no unresolved critical/high finding | Happy path only |
| G6 — Privacy and retention | Scanned final artifacts; verified private network/gates; actual retained/deleted resource handoff | Assumed redaction or unobserved cleanup claim |
| G7 — Submission | Final commit, reproducible setup/tests, honest limitations, AI disclosure and actual demo starting state | Generic README or placeholder results |

G5 includes real local database adversarial cases; each must label its backend honestly. Do not imply every fault was induced against the RDS source. A safe controlled-demo source apply is sufficient for G4; no third-party production database is needed or permitted.

## Secret/raw-data scan checklist

Scan staged Git diffs, history newly created for the event, code/config files, tool JSON, report JSON/Markdown, service logs, screenshots, video frames, copied terminal commands, provider configuration exports and Daytona output. Use seeded sentinel strings in tests for DB password, fake AWS-key-like text and synthetic row values. Check outputs, not just logger calls.

Allow legitimate synthetic input SQL literals and declared expected values; disallow unintended returned row values. A scan must distinguish a declared `standard` contract constant from actual database content dumped by an error. Do not commit real credentials to test a scanner. Inspect the human recording too; regex cannot prove that a UI recording is safe.

## Final verification packet

Generate a sanitized `evidence/final/acceptance-matrix.json` listing every required gate as PASS/FAIL/NOT_RUN with real file references. Include independent hashes of reports/receipts, real run IDs, backend and implementation commit. The task ledger must agree with this packet. Any unperformed action remains NOT_RUN; do not use planned commands as executed evidence.


## Build-ready versus demo-ready

`KIT_VALIDATION.json` is static archive validation. It is never an application test report. T19 is local implementation readiness; T23/T24 supply live RDS/runtime proof; T34 closes the actual demo-readiness audit. A static JSON `true` in a planning template cannot stand in for any of those observations.

The accepted provider/model pair gets a compact representative evaluation: bad migration blocked, valid migration explained from evidence, wrong-data migration rejected, malicious comment ignored, denial preserved, and resumed session reads state without replay. Record per-case success/failure, latency and observed usage where available; do not claim a broad model benchmark from these six project cases.


## V3 stage readiness additions

Before the first real source mutation, require accepted T27 independent review. At final readiness, check the exact reviewed commit/delta, column-level coverage tests, offline verifier and trust-anchor labeling, model/effort observations, expert-ticket usage and representative runtime trace cases. Never rerun a committed source migration merely to refresh the evidence. New live runs require an authorized reset/new synthetic source and new rehearsal.

An offline report digest verifies historical bytes and declared evidence consistency; it does not replace fresh source drift/backup checks or demonstrate genuine human identity. Missing account/network access means connected gates are NOT_RUN/BLOCKED_EXTERNAL, not “verified by offline proof.”
