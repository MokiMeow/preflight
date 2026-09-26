# 09 — Live build status and resume ledger (V3)

**Initial state:** planning starter only. No application implemented, installed, tested or deployed by creating this archive. Update this file during the actual build; do not overwrite the original PRD.

## Current checkpoint

- Event start / organizer constraints: NOT_CONFIRMED_IN_THIS_KIT.
- Implementation commit: NONE.
- Selected toolchain lock: NOT_CREATED.
- Active agent assignments/worktrees: NONE.
- Next task: T00, then T01–T03; T04 can proceed with actual operator context.
- Latest passing gate: NONE.
- Source apply enabled: false.
- Actual run/candidate/resource IDs: NONE.
- Current irreversible action awaiting a human: NONE.

## Task ledger

Use status `NOT_STARTED`, `IN_PROGRESS`, `BLOCKED_EXTERNAL`, `FAILED`, `LOCAL_VERIFIED`, `CONNECTED_VERIFIED` or `RETAINED_WITH_REASON`. Add actual evidence paths/commit references. A local result never implies a connected result.

| Task | Owner | Initial status | Evidence / commit / blocker |
|---|---|---|---|
| T00 — Establish event rules, clean workspace and build provenance | lead | NOT_STARTED | Not executed |
| T01 — Resolve and record one compatible toolchain | lead | NOT_STARTED | Not executed |
| T02 — Freeze shared domain models and service interfaces | lead | NOT_STARTED | Not executed |
| T03 — Implement configuration, doctor and runnable service shell | lead | NOT_STARTED | Not executed |
| T04 — Authorize and plan the bounded AWS footprint | cloud | NOT_STARTED | Not executed |
| T05 — Provision or validate private host, source and runtime identity | cloud | NOT_STARTED | Not executed |
| T06 — Build immutable candidates, durable state and idempotency | lead | NOT_STARTED | Not executed |
| T07 — Implement recursive PostgreSQL AST and object policy | database | NOT_STARTED | Not executed |
| T08 — Build real DB sessions, fixtures and transactional runner | database | NOT_STARTED | Not executed |
| T09 — Implement canonical row/schema evidence and typed checks | database | NOT_STARTED | Not executed |
| T10 — Implement the pure verdict and eligibility rules | lead | NOT_STARTED | Not executed |
| T11 — Implement sealed JSON evidence and readable report rendering | integration | NOT_STARTED | Not executed |
| T12 — Implement the narrowly scoped RDS adapter | cloud | NOT_STARTED | Not executed |
| T13 — Build asynchronous snapshot/restore jobs and restart reconciliation | cloud | NOT_STARTED | Not executed |
| T14 — Connect baseline, clone execution and validation use cases | lead | NOT_STARTED | Not executed |
| T15 — Implement safe candidate revision and report history | lead | NOT_STARTED | Not executed |
| T16 — Implement the guarded source transaction and durable outcomes | lead | NOT_STARTED | Not executed |
| T17 — Implement guarded cleanup and recovery retention | cloud | NOT_STARTED | Not executed |
| T18 — Expose and contract-test the complete MCP surface | lead | NOT_STARTED | Not executed |
| T19 — Pass the complete local end-to-end gate | lead | NOT_STARTED | Not executed |
| T20 — Prove TrueForge, OpenAI and Daytona compatibility early | integration | NOT_STARTED | Not executed |
| T21 — Deploy the service and saved agent on the EC2 host | integration | NOT_STARTED | Not executed |
| T22 — Create and verify the real synthetic RDS rehearsal | cloud | NOT_STARTED | Not executed |
| T23 — Run the real bad-to-good migration proof | integration | NOT_STARTED | Not executed |
| T24 — Demonstrate denial, approved apply and replay refusal | integration | NOT_STARTED | Not executed |
| T25 — Prove successful SQL can still fail correctness, and drift blocks apply | database | NOT_STARTED | Not executed |
| T26 — Exercise crash, timeout and uncertain-commit recovery | lead | NOT_STARTED | Not executed |
| T27 — Perform independent privacy, IAM and boundary review | reviewer | NOT_STARTED | Not executed |
| T28 — Polish the report and native TrueForge experience | integration | NOT_STARTED | Not executed |
| T29 — Exercise cleanup guards and record deliberate retention | cloud | NOT_STARTED | Not executed |
| T30 — Verify reproducible installation and operational handoff | lead | NOT_STARTED | Not executed |
| T31 — Run the final regression and close review findings | lead | NOT_STARTED | Not executed |
| T32 — Prepare the complete repository submission | integration | NOT_STARTED | Not executed |
| T33 — Record and rehearse the evidence-led pitch | integration | NOT_STARTED | Not executed |
| T34 — Perform the final read-only demo-readiness audit | lead | NOT_STARTED | Not executed |
| T35 — Close out resources after the demonstration | cloud | NOT_STARTED | Not executed |

## Consolidated external inputs

Record presence and nonsecret IDs only. Never paste an API key/password/private key/token here.

| Input | Status | Resolved by / nonsecret reference |
|---|---|---|
| Actual organizer rules/submission fields | Unknown | User URL; see docs 00 limitations |
| Allowed implementation start | Unknown | Organizer confirmation |
| Team-owned AWS account and region | Missing | Operator JSON |
| Creation scope, budget and resource caps | Missing | Explicit operator authorization |
| Source/database or creation permission | Missing | Operator JSON / cloud discovery |
| Network/security-group/subnet IDs | Missing | Cloud discovery/bootstrap |
| Runtime IAM identity and named secret ARNs | Missing | Bootstrap output |
| OpenAI provider/model access | Missing | TrueForge settings, never key text |
| Daytona provider access | Missing | TrueForge settings, never key text |
| Human approver present | Pending | Real UI decision |
| Submission remote and visibility | Unknown | Organizer/team decision |

## Accepted implementation deviations

| Time | Task | Original requirement / evidence | Smallest change and reason | Tests | Owner |
|---|---|---|---|---|---|
| — | — | No deviations yet beyond docs 00 D01–D14 | — | — | — |

## Findings and repairs

| Finding | Severity | Reproduction/evidence | Owning task | Repair commit | Recheck |
|---|---|---|---|---|---|
| — | — | No implementation review performed yet | — | — | — |

## Evidence checkpoints

| Gate | Status | Exact command or real observation | Commit/time/backend |
|---|---|---|---|
| Local unit/policy/evidence | NOT_RUN | — | — |
| Real local PostgreSQL | NOT_RUN | — | — |
| MCP contract + end-to-end | NOT_RUN | — | — |
| TrueForge/OpenAI/Daytona | NOT_RUN | — | — |
| AWS snapshot/private clone | NOT_RUN | — | — |
| Bad/BLOCK and good/PASS | NOT_RUN | — | — |
| Human denial / no source change | NOT_RUN | — | — |
| Human allow / exact source apply | NOT_RUN | — | — |
| Replay/tamper/drift | NOT_RUN | — | — |
| Crash/uncertain outcome | NOT_RUN | — | — |
| Privacy/network/IAM review | NOT_RUN | — | — |
| Cleanup/retention | NOT_RUN | — | — |
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
- Coding CLI baseline: 0.157.0 source/docs; installed version NOT_OBSERVED.
- Requested lead: GPT-6 Sol/high; actual model NOT_OBSERVED.
- Runtime route: preferred Gateway + verified Responses adapter + GPT-6 Sol/high; actual route NOT_RUN.
- Gateway optionality/final event schedule: final operator/on-site confirmation pending.
- `.codex` role configuration accepted: NOT_RUN. Four `.agents/skills` discovered: NOT_RUN.
- Source-tag verification: TrueForge 0.2.1 and MCP v2.2.0 confirmed; registry install/integrity and interoperability pending.
- Current instruction: start T00 after authorized event start, then T01/T04 and the dependency graph. Do not mark any task done merely because a specification was revised.

Fill a local copy of `config/capability-probe.example.json`. Record actual model/effort per assignment, checkout/base commit, worker evidence, integrated evidence and reviewer result. Keep a consolidated operator-input list rather than repeatedly interrupting for the same missing access.


## Model admission and observed usage

- Primary implementation: GPT-6 Sol/high and GPT-5.6 Sol/high only.
- Routine independent reviewer: GPT-6 Sol/high; exact observed model: NOT_OBSERVED.
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
| Sol role/effective-model agreement | NOT_RUN | Actual lead/child model and effort, no silent Astra/premium routing |
| Column-level coverage | NOT_RUN | Unasserted mutation WARN; protected wrong-data BLOCK; explicit value/schema coverage PASS control |
| Offline report verifier | NOT_RUN | No network; tamper and forged rehash/trusted-anchor checks; historical/unanchored labels |
| Pre-apply review order | NOT_RUN | Accepted T27 evidence precedes first T24 live write |
| Agent behavior evaluations | NOT_RUN | Real trace/state results for config/agent-evaluation-plan.json |
| Expert budget accounting | NOT_RUN | Admitted/used/skipped A1/A2 tickets, actual evidence, no fabricated savings |
