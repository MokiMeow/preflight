# 09 — Live build status and resume ledger (V3)

**Current state:** implemented Python service, deterministic evidence, guarded AWS adapters and pinned native TrueForge integration. Local verification is ongoing; connected deployment and human demonstrations await operator access. The archive began as specifications only.

## Current checkpoint

- Event start: operator confirmed organizer authorizes coding now on 2026-09-26, before first application edit. Final submission fields remain unconfirmed.
- Implementation checkpoint: 2867449; report, database, service, MCP and cloud adapter implementations integrated.
- Toolchain: uv.lock installed; Python 3.12.10 / MCP 2.2.0 / pglast 8.4 / PostgreSQL18 target.
- Active isolated lanes: database (fresh synthetic fixture initializer), cloud (bootstrap prerequisites), integration (runtime probe/handoff/submission artifacts); no grandchildren.
- Next: integrate remaining lane commits, independently recheck, recreate locked environment, run final local regression and record sanitized evidence.
- Latest full passing gate: 155 tests in 111.21s on real local PostgreSQL18 plus local AWS Stubber, unit, MCP and TrueForge checks, before the latest inventory/storage/role delta. New role/database/MCP targeted gate: 35 passed in 70.01s; real HTTP MCP bad-to-good flow: 1 passed in 3.16s; runtime composition: 1 passed in 0.30s. Final combined gate pending.
- Source apply enabled: false.
- Actual run/candidate/resource IDs: NONE.
- Current irreversible action awaiting a human: NONE.

## Task ledger

Use status `NOT_STARTED`, `IN_PROGRESS`, `BLOCKED_EXTERNAL`, `FAILED`, `LOCAL_VERIFIED`, `CONNECTED_VERIFIED` or `RETAINED_WITH_REASON`. Add actual evidence paths/commit references. A local result never implies a connected result.

| Task | Owner | Initial status | Evidence / commit / blocker |
|---|---|---|---|
| T00 — Establish event rules, clean workspace and build provenance | lead | LOCAL_VERIFIED | evidence/setup/event-and-provenance.md; operator timing override; PRD original hash retained |
| T01 — Resolve and record one compatible toolchain | lead | LOCAL_VERIFIED | uv.lock installed; Python MCP2.2 HTTP and pinned TrueForge JS MCP roundtrip passed; paid model route pending |
| T02 — Freeze shared domain models and service interfaces | lead | LOCAL_VERIFIED | 5790a6a frozen types; strict schemas and integrated safety tests |
| T03 — Implement configuration, doctor and runnable service shell | lead | LOCAL_VERIFIED | b068fc5, settings/doctor/CLI/loopback official MCP runnable; defaults disabled |
| T04 — Authorize and plan the bounded AWS footprint | cloud | BLOCKED_EXTERNAL | Bounded bootstrap plan/approval implementation; missing approved account/region/budget/scope |
| T05 — Provision or validate private host, source and runtime identity | cloud | BLOCKED_EXTERNAL | Private host/source/IAM bootstrap code and Stubber checks; cloud inputs missing |
| T06 — Build immutable candidates, durable state and idempotency | lead | LOCAL_VERIFIED | 12cfc72, immutable artifacts/CAS/idempotency and atomic report publication 9bb5841 |
| T07 — Implement recursive PostgreSQL AST and object policy | database | LOCAL_VERIFIED | 19cb6ad/e5d7368, recursive PG18 AST confinement; real metadata refusal tests |
| T08 — Build real DB sessions, fixtures and transactional runner | database | LOCAL_VERIFIED | e5d7368/77113a0, real PG18 TLS/role/transaction/timeout/outcome tests |
| T09 — Implement canonical row/schema evidence and typed checks | database | LOCAL_VERIFIED | e5d7368, complete canonical typed evidence and written-column coverage |
| T10 — Implement the pure verdict and eligibility rules | lead | LOCAL_VERIFIED | 12cfc72, deterministic complete manifest verdict and eligibility |
| T11 — Implement sealed JSON evidence and readable report rendering | integration | LOCAL_VERIFIED | f69addf/9bb5841, sealed report/offline trust-anchor checks and interruption repair |
| T12 — Implement the narrowly scoped RDS adapter | cloud | LOCAL_VERIFIED | d41712a, injected boto Stubber only; storage/private ownership/inventory guards; no AWS |
| T13 — Build asynchronous snapshot/restore jobs and restart reconciliation | cloud | LOCAL_VERIFIED | ea477ac/d41712a, persistent leases/reservations/async reconciliation; no AWS |
| T14 — Connect baseline, clone execution and validation use cases | lead | LOCAL_VERIFIED | b9696bc, real local DB baseline/clone/validation causal chain |
| T15 — Implement safe candidate revision and report history | lead | LOCAL_VERIFIED | 9bb5841, same-contract rollback-only revision and immutable history |
| T16 — Implement the guarded source transaction and durable outcomes | lead | LOCAL_VERIFIED | 77113a0, local fixture locked guard/apply/replay tests; actual human/AWS apply NOT_RUN |
| T17 — Implement guarded cleanup and recovery retention | cloud | LOCAL_VERIFIED | d41712a, local Stubber guarded cleanup/retention/absence reconciliation; live deletion NOT_RUN |
| T18 — Expose and contract-test the complete MCP surface | lead | LOCAL_VERIFIED | 77113a0, ten flat strict tools via real HTTP official MCP with sanitized invalid-input test |
| T19 — Pass the complete local end-to-end gate | lead | LOCAL_VERIFIED | 77113a0, real HTTP MCP bad rollback/BLOCK -> revision good commit/PASS -> report/AWAITING_APPROVAL; local DB only |
| T20 — Prove TrueForge, OpenAI and Daytona compatibility early | integration | BLOCKED_EXTERNAL | Pinned native bundled JS MCP to Python roundtrip passed; OpenAI/Gateway and Daytona missing |
| T21 — Deploy the service and saved agent on the EC2 host | integration | BLOCKED_EXTERNAL | Deployment/agent configuration prepared; approved host/provider setup missing |
| T22 — Create and verify the real synthetic RDS rehearsal | cloud | BLOCKED_EXTERNAL | No cloud source/snapshot/clone exists from this build; AWS access/authorization missing |
| T23 — Run the real bad-to-good migration proof | integration | BLOCKED_EXTERNAL | Local bad-to-good proof passed; real snapshot-restored RDS proof missing |
| T24 — Demonstrate denial, approved apply and replay refusal | integration | BLOCKED_EXTERNAL | Backend local guards tested; actual saved human deny/allow gate missing; T27 must precede |
| T25 — Prove successful SQL can still fail correctness, and drift blocks apply | database | LOCAL_VERIFIED | e5d7368, real PG wrong-data commit/BLOCK, uncovered-column WARN, drift refusal |
| T26 — Exercise crash, timeout and uncertain-commit recovery | lead | LOCAL_VERIFIED | 9bb5841, actual local PG fault injection and durable restart/publication tests; AWS uncertainty not connected |
| T27 — Perform independent privacy, IAM and boundary review | reviewer | BLOCKED_EXTERNAL | Independent Sol local findings F1-F4 repaired/rechecked; composition/role delta recheck pending; connected IAM/UI/privacy and A1 pending |
| T28 — Polish the report and native TrueForge experience | integration | IN_PROGRESS | Report/native TrueForge templates implemented; handoff/demo polish in progress |
| T29 — Exercise cleanup guards and record deliberate retention | cloud | BLOCKED_EXTERNAL | Local cleanup guard tests passed; actual operator cleanup choice/resources absent |
| T30 — Verify reproducible installation and operational handoff | lead | IN_PROGRESS | Locks installed and pinned SDK tested; fresh isolated locked install pending |
| T31 — Run the final regression and close review findings | lead | IN_PROGRESS | 155 full local tests passed before latest safety delta; final regression pending |
| T32 — Prepare the complete repository submission | integration | IN_PROGRESS | Repository built locally; license/SBOM/submission artifacts in progress; no remote publication authorized |
| T33 — Record and rehearse the evidence-led pitch | integration | BLOCKED_EXTERNAL | Demo material preparation; actual connected proof/recording pending |
| T34 — Perform the final read-only demo-readiness audit | lead | BLOCKED_EXTERNAL | Final connected evidence/A1 audit pending; local review ongoing |
| T35 — Close out resources after the demonstration | cloud | BLOCKED_EXTERNAL | No AWS resources created; connected deliberate cleanup/retention not demonstrated |

## Consolidated external inputs

Record presence and nonsecret IDs only. Never paste an API key/password/private key/token here.

| Input | Status | Resolved by / nonsecret reference |
|---|---|---|
| Actual organizer rules/submission fields | Unknown | User URL; see docs 00 limitations |
| Allowed implementation start | Confirmed | Operator: organizer authorized coding now, before application edits |
| Team-owned AWS account and region | Missing | Operator JSON |
| Creation scope, budget and resource caps | Missing | Explicit operator authorization |
| Source/database or creation permission | Missing | Operator JSON / cloud discovery |
| Network/security-group/subnet IDs | Missing | Cloud discovery/bootstrap |
| Runtime IAM identity and named secret ARNs | Missing | Bootstrap output |
| OpenAI provider/model access | Missing | TrueForge settings, never key text |
| Daytona provider access | Missing | TrueForge settings, never key text |
| Human approver present | Pending | Real UI decision |
| Submission remote and visibility | Unknown | Organizer/team decision |

Operator requests independent implementation while credits/access are pending. No cloud spend, source reset, publishing or product approval is inferred. No real AWS/provider/Daytona request has been executed.

## Accepted implementation deviations

| Time | Task | Original requirement / evidence | Smallest change and reason | Tests | Owner |
|---|---|---|---|---|---|
| — | — | No deviations yet beyond docs 00 D01–D14 | — | — | — |

## Findings and repairs

| Finding | Severity | Reproduction/evidence | Owning task | Repair commit | Recheck |
|---|---|---|---|---|---|
| F1 invalid request ID echoed | MEDIUM | Secret-like invalid-input sentinel | lead | bb7b05c | Independent Sol closed at 9bb5841 |
| F2 contradictory aggregate report could seal PASS | MEDIUM | Row count/root contradiction with rehashed report | integration | f69addf | Independent Sol closed at 9bb5841 |
| F3 interrupted report publication retry changed seal | MEDIUM | Markdown write interruption and restart | lead | 9bb5841 | Independent Sol closed at 9bb5841 |
| F4 unsupported RDS storage accepted | MEDIUM | Stubber source/clone magnetic storage | cloud | d41712a | Independent Sol closed at d41712a |
| F5 missing tagging client in deployed composition | MEDIUM | Static composition, new creation refused | lead | 77113a0/2867449 | Inert composition test passed; independent recheck pending |
| RDS inherited administrative membership | Safety concern | Local rolsuper=false rds_superuser and server-file membership | lead | 77113a0 | Real PG tests refused both; independent recheck pending |

## Evidence checkpoints

| Gate | Status | Exact command or real observation | Commit/time/backend |
|---|---|---|---|
| Local unit/policy/evidence | LOCAL_VERIFIED | Integrated 155-test run plus targeted repairs | Local only |
| Real local PostgreSQL | LOCAL_VERIFIED | PG18.6, loopback TLS, separate nonsuperuser fixtures | e5d7368/77113a0 |
| MCP contract + end-to-end | LOCAL_VERIFIED | Actual HTTP official client and bad-to-good chain | 77113a0 |
| TrueForge/OpenAI/Daytona | BLOCKED_EXTERNAL | Bundled JS MCP roundtrip LOCAL_VERIFIED; paid route/Daytona NOT_RUN | No external credentials |
| AWS snapshot/private clone | NOT_RUN | — | — |
| Bad/BLOCK and good/PASS | LOCAL_VERIFIED | Actual disposable PostgreSQL, exact bytes, historical reports | AWS version NOT_RUN |
| Human denial / no source change | NOT_RUN | — | — |
| Human allow / exact source apply | NOT_RUN | — | — |
| Replay/tamper/drift | LOCAL_VERIFIED | Actual local DB and trusted/unanchored offline verifier | Connected NOT_RUN |
| Crash/uncertain outcome | LOCAL_VERIFIED | Actual PG fault injection; durable restart and report publication | Connected NOT_RUN |
| Privacy/network/IAM review | BLOCKED_EXTERNAL | Independent Sol local review/Stubber checks; AWS and saved human gates unobserved | T27 not accepted connected |
| Cleanup/retention | LOCAL_VERIFIED | Guarded local Stubber deletion/absence/retention tests | No live cleanup performed |
| Final submission/recording | NOT_RUN | — | — |

## Resume packet — replace at a meaningful checkpoint

```text
Last verified commit:
Currently active task and owner:
Completed facts with evidence paths:
Current source/run/clone state:
Any APPLYING / unknown transaction: [never replay]
Pending cloud job IDs and last observed state:
Missing external input and who must provide it:
Next safe actionable task:
Exact relevant tests to rerun after the next edit:
```

A restarted coding session first reads this ledger, verifies Git and the referenced evidence, and resumes the next safe task. It never infers that a source operation failed merely because the previous chat or connection stopped.


## V3 setup/compatibility ledger

- Archive: V3 specifications only; no product implementation, installed-provider probe or live cloud test has been performed by preparing this kit.
- Coding CLI baseline: 0.157.0 source/docs; installed version 0.153.0, retained without replacing global binary.
- Requested lead: GPT-6 Sol/high; actual session trace observed GPT-6 Sol/high.
- Runtime route: preferred Gateway + verified Responses adapter + GPT-6 Sol/high; actual route NOT_RUN.
- Gateway optionality/final submission fields: final operator/on-site confirmation pending; coding start authorized.
- Effective DB/cloud/reviewer GPT-6 Sol/high and integration GPT-5.6 Sol/high observed from role/session traces. Narrow repository skill routers used; explicit isolated worktrees and no grandchildren.
- TrueForge 0.2.1 and MCP v2.2.0 installed from pinned locks; registry integrity and real cross-language MCP interoperability verified locally.
- Current instruction: finish independent authorized work while operator obtains credits; connected acceptance remains gated.

Fill a local copy of `config/capability-probe.example.json`. Record actual model/effort per assignment, checkout/base commit, worker evidence, integrated evidence and reviewer result. Keep a consolidated operator-input list rather than repeatedly interrupting for the same missing access.


## Model admission and observed usage

- Primary implementation: GPT-6 Sol/high and GPT-5.6 Sol/high only.
- Routine independent reviewer: GPT-6 Sol/high; exact observed role/session model: gpt-6-sol/high.
- Exceptional expert policy: [model-policy.json](../config/model-policy.json); at most two admitted sessions without a further user extension.
- Astra sessions actually used: **0**. Additional user-authorized sessions: **0**.
- Vendor allowance/usage before and after: **NOT_OBSERVED**. The template is not a billing measurement.

| Slot | Trigger/task | Reviewed commit and question | Actual model/effort | Usage, units | Findings/repair/retest | State |
|---|---|---|---|---|---|---|
| A1 | T27 focused pre-live-apply safety boundary audit | — | NOT_OBSERVED | NOT_OBSERVED | — | NOT_USED |
| A2 | Conditional T34 safety delta or qualifying critical blocker | — | NOT_OBSERVED | NOT_OBSERVED | — | NOT_USED |

Write the ticket from docs 10 **before** spawning the exceptional reviewer. A slot spent on a blocker is not available again for the final audit. Skip repeated Astra review when there is no material safety change; record why. If an independent Sol review substitutes because Astra is unavailable, say so and retain the same acceptance bar. Never imply an AI audit is the engineer's product approval.

## V3 additional evidence gates

| Gate | Initial status | Required evidence |
|---|---|---|
| Sol role/effective-model agreement | LOCAL_VERIFIED | Actual lead/child session traces; Astra sessions 0 |
| Column-level coverage | LOCAL_VERIFIED | Real PG unasserted mutation WARN, protected wrong-data BLOCK, explicit value/schema PASS |
| Offline report verifier | LOCAL_VERIFIED | Strict parse/tamper/rehashed-contradiction/trusted-anchor and historical/unanchored tests |
| Pre-apply review order | NOT_RUN | Accepted T27 evidence precedes first T24 live write |
| Agent behavior evaluations | NOT_RUN | Real trace/state results for config/agent-evaluation-plan.json |
| Expert budget accounting | NOT_RUN | Admitted/used/skipped A1/A2 tickets, actual evidence, no fabricated savings |
