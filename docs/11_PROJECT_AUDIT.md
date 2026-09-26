# Preflight V3 implementation audit — 26 September 2026

Preflight's local implementation works and the integrated audit gate passed **314 tests, with zero failures, errors or skips**. The complete connected product is **not finished**: real RDS rehearsal, a funded OpenAI route, Daytona execution, private-host deployment, genuine human Deny/Allow and final submission/closeout remain unverified.

The earlier statement that independent work was exhausted was too broad. This audit found substantive DB, MCP and bootstrap gaps, repaired them, added regression assertions and corrected the task ledger. A passing test count does not mean every specified scenario or every function branch has been verified.

## Scope and evidence

Implementation under test: **`221a79a`**. Audit baseline: `dbc4c1a`. Later audit documentation and the inventory generator are separately committed; they do not change the application exercised by the gate.

The audit compared the immutable PRD, AGENTS.md, the numbered product/architecture/safety/build/cloud/runtime/verification/demo/operating-system documents, all 36 task cards, all 153 scenario specifications and E01–E10. It inventoried every first-party tracked file, including hidden role/skill configuration, fixtures, tests, probes, locks and retained evidence. It also parsed the two original untracked kit metadata files. The file appendix records the exact snapshot, hash, purpose, parse method and every discovered declaration.

Vendor packages, Git internals, repeated worktree copies, binaries, virtual environments and ignored private configuration/state/logs are excluded from the first-party file review. Dependency locks and the installed dependency/license inventory are assessed separately. “Every file” does not mean every third-party source line or private credential file was inspected or exported.

The PRD remains byte-for-byte unchanged: SHA-256 `5f607b53bd7c439c94e3f97d3826e24e441cb5d007863eca023313347533b6bf`.

Detailed appendices:

- [Every first-party file and declared function/class](audit/FILE_FUNCTION_INVENTORY.md), with [machine inventory](audit/file-function-inventory.json).
- [All 36 tasks, dependencies, exact acceptance and subtasks](audit/TASK_MATRIX.md), with [machine task matrix](audit/task-matrix.json).
- [All 153 scenarios and their missing assertions](audit/SCENARIO_MATRIX.md), with [machine scenario matrix](audit/scenario-matrix.json).
- [Actual test commands/results and failed attempts](audit/verification.json).
- [Scoped function review notes](audit/review-notes.json) and [limited function-call observations](audit/function-call-observations.json).

## What actually works locally

The Python service exposes exactly ten MCP business tools through the official SDK. Inputs and outputs are strict and tool-specific. Unknown/invalid input produces safe fixed errors. The service owns exact SQL bytes and hashes, canonical contracts, candidate ancestry, SQLite state/CAS/idempotency, immutable report publication and durable apply/cleanup receipts.

The SQL policy uses PostgreSQL 18 pglast ASTs. It confines statements, relations, columns and expressions to the supported contract. The database boundary rejects unsupported catalog capabilities, verifies the runtime role/TLS/major/encoding, and runs exact SQL in a fresh explicit transaction with lock, statement and whole-operation limits. A failed supported migration is rolled back; an uncertain commit is never labeled rollback or automatically retried.

Evidence capture uses a controlled read-only repeatable-read transaction, normalized schema/index semantics, type-tagged value hashes and private primary-key maps. Reports expose safe aggregates, including missing/extra/changed preserved-row counts. Every written column needs preservation or supported intended-value coverage; a new column also needs expected schema. Deterministic complete checks decide PASS/WARN/BLOCK. The model cannot redefine them.

Actual disposable PostgreSQL tests prove bad migration rollback/BLOCK, accepted same-contract revision, good migration commit/PASS, protected wrong-data BLOCK, incomplete mutation coverage WARN, real schema NOT NULL, source drift refusal and the HTTP MCP causal chain. New tests prove competing source writers before/after locks, exactly one concurrent accepted apply, failed post-commit confirmation and actual COMMIT followed by lost acknowledgement. These use explicitly isolated local fixture databases and test-only source authorization; they are **not** human approval or AWS source-write evidence.

Sealed reports cover canonical payload bytes only. Offline verification distinguishes an independently supplied expected digest from unanchored self-consistency. It preserves historical backend labels, checks requirement/result consistency and never asserts current source eligibility. Prior reports remain unchanged after revision, apply receipts and publication restart.

The RDS adapter, persistent asynchronous jobs and bootstrap driver are implemented. Local Boto Stubber tests exercise ownership, identity, private topology, storage, resource limits, uncertainty, restart and cleanup/retention boundaries. They prove client arguments and branch behavior, not actual IAM effectiveness, RDS restore or network reachability.

TrueForge 0.2.1, its bundled MCP client, configuration fields and package/runtime dependencies were locally probed. The actual native connector was observed connected to the fail-closed local MCP service with ten tools. It had no configured model agent or provider execution. Saved-agent templates and the two literal approval names are validated; actual save/reload and human gate behavior remain external.

## Findings and implemented repairs

| Finding | Initial problem | Repair and evidence |
|---|---|---|
| DB-F01 HIGH | Schema roots omitted index direction/null ordering, builtin opclass identity and NULLS NOT DISTINCT. | `5ccb78f`: normalized semantic fields; real PG drift regressions. Unsupported non-immediate/exclusion indexes refused. |
| DB-F02 MEDIUM | Default baseline capture could reuse an uncontrolled existing transaction. | `5ccb78f`: fresh-session requirement; explicitly chosen in-transaction source pre/postcheck remains supported. Real transaction cases. |
| DB-F03 HIGH | Runtime login checks omitted effective DB/schema ownership and CREATE privileges. | `5ccb78f`: broad runtime capability refused; real role/TLS regressions. Table-specific migration ownership remains supported. |
| DB-F04 MEDIUM | Promised missing/extra/changed row aggregates were absent. | `5ccb78f`: safe complete coverage requirements/results; no private keys or row values returned. |
| DB-F05 MEDIUM | A precommit callback could return None/0/an empty object and still permit commit. | `5ccb78f`: explicit True or a validated nonempty complete all-pass CheckSet. `8ec02a9`: service returns True only after deterministic PASS. |
| DB-F06 LOW | PG18 NO INHERIT NOT NULL semantics were discarded. | `5ccb78f`: unsupported variant rejected; actual PG catalog test. |
| MCP-F01 | All outputs used generic dictionaries rather than distinct schemas. | `1d81bef`, `8ec02a9`: ten typed output models/envelopes and real HTTP schema assertions. |
| MCP-F02 | Public warnings, baseline/report references, status hashes/progress/elapsed, next operation and actual precheck state were missing. | `8ec02a9`: explicit safe fields; truthful nullable observation time and preliminary eligibility reason. |
| MCP-F03 | Source status lacked baseline MATCH/DIFFERENT/UNAVAILABLE comparison. | `8ec02a9`: requested-table evidence and safe comparison; no row maps. |
| CLOUD-A01 MEDIUM | IAM delete permission accepted an overly broad prefix without all required ownership/run guards. | `73780b4`, `221a79a`: narrow clone/snapshot scope, source protection and exact Project/Owner/RunId conditions. |
| CLOUD-A02 MEDIUM | Observed source storage could exceed the approved footprint. | `73780b4`: exact approved storage verification; missing/oversized/valid cases. |
| CLOUD-A03 MEDIUM | Reuse could accept a returned host other than the approved exact ID. | `73780b4`: returned identity bound to approved ID. |
| CLOUD-A04 MEDIUM | Encryption/persistence/root mapping was assumed from the request. | `73780b4`, `54eeeed`, `221a79a`: observed EBS attachments/encryption/gp3/persistence; AMI's actual root name; created host constrained to one 30-GiB volume. |
| CLOUD-A05 MEDIUM | Missing or unusably conditional grants counted as required permissions. | `73780b4`, `221a79a`: required action/resource coverage; unsupported and mixed conditional grants refused. Optional deletion permissions deliberately permit retention. |
| CLOUD-A06 MEDIUM | Returned created-host AMI/root was not bound to the approved AMI/root. | `221a79a`: explicit returned identity/root checks; negative tests. |
| CLOUD-A07 LOW | Malformed/unknown IAM condition structures could crash validation or pass. | `221a79a`: fail-closed typed shape/condition validation with fixed errors and negative probes. |
| LEDGER-F01 | T32 LOCAL_VERIFIED overstated complete submission acceptance. | Corrected to BLOCKED_EXTERNAL; local materials are ready, final connected/event/publication requirements are not. |

Additional corrections: `.env.example` now lists actual implemented inputs rather than unsupported environment knobs; the service does not silently load dotenv. The local service test fixture now records actual `created_at`, as the runtime does, and connection deadlines prevent indefinite test hangs.

Independent Sol/high review at exact `221a79a` closed CLOUD-A01–A07, reran **106 cloud tests** and **37 affected unit tests**, and inspected the integrated models/service/server/DB/evidence delta. No remaining critical/high defect was found within that bounded review. It did not rerun PG and does **not** accept connected T27. The lead's final integrated gate ran all PG tests.

## Tests, simulations and their limits

Final command: `uv run --locked pytest -q --junitxml=var/audit/final-tests.xml`, in the locked `.venv-clean`, with an explicitly configured disposable PG18.6 loopback port and retained local CA.

| Lane | Passed | Backend / implication |
|---|---:|---|
| Unit | 99 | Pure/service/CLI/offline boundaries and injected faults. |
| PostgreSQL | 97 | Actual SQL, locks, transactions, metadata and source-fixture races/outcomes. |
| Cloud | 106 | Injected AWS client responses and pure durable-state tests; no real AWS mutation. |
| MCP | 1 | Actual local HTTP transport, ten schemas and safe failures; additional PG/TrueForge tests also exercise MCP. |
| TrueForge | 11 | Pinned local package/config/protocol/probe tests; no funded runtime or Daytona execution. |
| **Total** | **314** | **182.74 seconds; zero failures/errors/skips.** |

Ruff, Mypy across 17 application files and `uv lock --check` passed. The audited package build and distribution inspection results are recorded with artifact hashes in `audit/distribution.json`; earlier isolated-wheel installation is historical evidence in the ledger.

Failed/interrupted attempts are retained in the verification record. A worker integration gate failed because a manually created test run lacked the newly required timestamp; the fixture was repaired. Root fault tests initially exposed fixture import/proxy/column mistakes; those were corrected before the accepted gate. Full profiling attempts were interrupted and are not passing evidence.

The limited older function profiler records call names/counts only, never arguments or rows. It ran only in-process unit/cloud Python at `73780b4`; it is **not branch coverage**, excludes PG subprocess/JavaScript observations and does not prove the final function's full correctness. Zero recorded calls do not mean the function was never tested.

The 153 complete scenario assertions currently classify as **58 LOCAL_VERIFIED, 65 PARTIAL, 22 BLOCKED_EXTERNAL and 8 NOT_RUN**. The partial rows identify the exact missing clause, rather than crediting an entire scenario from one related test name. **All ten agent evaluations E01–E10 are NOT_RUN.** Original `config/test-index.json` and KIT_VALIDATION describe specified/static kit checks, not execution receipts.

## Task completion and actual acceptance

The ledger contains **21 locally verified tasks and 15 externally blocked tasks** after correcting T32. Local tasks implement their core behavior; their status does not imply all 153 assertions are complete. The appendix reproduces each task's acceptance and subtasks, explains what exists and names what remains.

| Required gate | Current assessment | Still needed |
|---|---|---|
| G1 real agent execution | BLOCKED_EXTERNAL | Actual authorized OpenAI/Gateway Responses route, saved TrueForge agent, Daytona Code Mode and bridged tool trace. |
| G2 real AWS copy | BLOCKED_EXTERNAL | Owned source, real snapshot/private restored clone, tags/describes/TLS baseline. |
| G3 real migration evidence | BLOCKED_EXTERNAL | Bad BLOCK and good PASS from that actual RDS clone, with complete deterministic evidence. |
| G4 human control | BLOCKED_EXTERNAL | Operator Deny/no-write, then Allow/exact-write and immutable receipt through the literal native gate. |
| G5 defensive correctness | LOCAL_PROOF_WITH_REMAINING_COVERAGE | Integrated adversarial proof and bounded review exist; close missing relevant clauses before full acceptance. |
| G6 privacy and retention | PARTIAL / external boundary pending | Local negative tests/package exclusions exist; actual IAM/private route/exporter/provider/Daytona/recording/resource retention proof is missing. |
| G7 submission | BLOCKED_EXTERNAL | Final event fields, connected acceptance packet, recording, final commit and authorized publication. |

The ledger also contains an operator AWS CLI authentication entry from separate host setup. It establishes identity authentication only; this audit did not repeat or inspect credential-bearing configuration. It is not resource scope/budget approval, RDS access, deployment readiness or any connected product gate.

## What needs to be done next

1. **Close independent local proof gaps from the scenario appendix.** Prioritize concurrent start/candidate-parent CAS, exhaustive unsupported AST/catalog variants, missing object/inaccessible metadata and scan deadlines, source hash/target/state combinations, and recovery interruption permutations. The eight NOT_RUN rows are N05/N09/N14/N16/N19/N26/V03/V04. Some are workflow/provider checks; each requires the named observation, not an invented pass.
2. **Probe telemetry and transport boundaries.** N16's explicit SDK OpenTelemetry sentinel, N19 partial-delivery reconnection, missing trace IDs and real transport timeout/reconnect behavior still need dedicated evidence. Disabling telemetry in deployment examples does not prove redaction with an exporter enabled. Validate the empty/wrong-state-directory/live-resource doctor behavior and artifact/export fsync interruption assumptions.
3. **Obtain the concrete cloud footprint and runtime inputs once.** Approved account/region, budget/resource caps, permitted create/reuse/reset scope, private network/subnet/security-group/host/AMI/IAM/secret references and actual Gateway/OpenAI/Daytona settings. Configure secrets in provider settings or ignored local files, never in chat/report/Git. Authentication or “full access” alone does not supply spend/reset permission.
4. **Execute T04 → T05 → T20 → T21 → T22 → T23.** Review the digest-bound concrete footprint, validate/create only within approved scope, install on the private host, probe the actual model/tool streaming route, run Daytona Code Mode, then obtain real RDS bad/revision/good evidence. Keep provider/API/model/resource identities distinct and record sanitized receipts.
5. **Accept T27 before T24.** Review actual IAM, private routes, SDK/provider/Daytona output, literal saved/reloaded gates and final artifacts. Close relevant critical/high findings, record the admitted review ticket/model and recheck material fixes. A1/A2 have used **zero Astra sessions**; no spend/usage saving measurement is claimed.
6. **Have the real operator demonstrate T24.** The operator must perform Deny and later Allow. The coding agent must not click either source-apply or cleanup approval. Observe source schema/data/receipt and replay refusal. Never retry uncertain source SQL.
7. **Finish T28–T34 and E01–E10.** Record actual malicious-comment/incomplete-coverage/denial/outage/retry/polling/unknown-outcome behavior from tool/service traces. Complete final event fields, privacy review of recording/screenshots, licenses, README commands and the final acceptance packet. Publish only with authorization.
8. **Perform T29/T35 deliberately.** Preserve reports/receipts and recovery backup; obtain the separate human cleanup choice. Verify actual retained/deleted resources and costs. No automatic cleanup or unsupported instant-undo claim.

No extra dashboard, replacement agent framework, general SQL support, third-party production access or cryptographic enterprise approval mechanism was added. Those are outside this controlled-demo contract. Production concurrency/application compatibility/downtime and later source changes remain outside historical rehearsal proof.
