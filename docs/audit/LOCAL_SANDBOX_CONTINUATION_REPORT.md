# Local sandbox continuation report

**Latest state:** D28 is implemented and deployed at `d3715ca`: the operator-authorized unlimited mode removes financial admission without fabricated billing data. Creation is enabled; source apply remains disabled. The actual encrypted AWS snapshot for run `fef79c61-dcea-42c3-a760-c2f9c4235abc` is creating (provider reported 1% at 11:01:02 UTC). A clone, migration result and source approval are still pending. New affected tests: 172 passed in 6.60s; independent review: 111 passed in 3.14s, no blocking finding. A new full gate is running. [Actual run receipt](../../evidence/connected/unlimited-rehearsal.json) and [three-minute walkthrough](THREE_MINUTE_WALKTHROUGH.md).

## Scope and provenance

This report records the continuation state after replacing Daytona with the installed TrueForge local Linux sandbox under decision D26. It is a handoff, not a declaration that Preflight is complete. The application and documentation snapshot reviewed here is root commit `8048e79`; the protected budget-fact publisher was introduced at `d45e41a`. The saved-agent instruction correction is included at `8048e79`. The immutable PRD was not changed.

The implementation role for this report was GPT-5.6 Sol with high reasoning. No host, AWS, database, provider, source-apply, cleanup, or approval-gate call was made while writing it. The root deployed application `8048e79` with publisher delta `79050b4` and saved-agent guidance `878d64a`; both private services were active and persisted state retained.

Status words have their strict meanings:

- **LOCAL_VERIFIED**: an assertion passed in a local test or static validation at the named revision.
- **CONNECTED_VERIFIED**: the named behavior was observed on the actual private host/native runtime. It does not imply that a whole task or scenario passed.
- **PARTIAL**: useful evidence exists, but at least one required assertion is missing.
- **BLOCKED_EXTERNAL**: completion needs an external resource, fact, provider condition, or human action that was unavailable.
- **NOT_RUN**: no qualifying complete execution occurred.

## Current verified results

| Area | Result | Scope and limit |
|---|---|---|
| Frozen full suite | **LOCAL_VERIFIED** | Commit `878d64a`: `641 passed`, zero failures, errors, or skips, in `263.60s`; exit 0. Actual local PostgreSQL18.6/TLS; cloud cases are Stubber tests. |
| Manifest-affected check | **LOCAL_VERIFIED** | At `8048e79`: nine affected tests passed in `5.46s`. |
| Static quality | **LOCAL_VERIFIED** | Ruff passed for the repository; mypy passed all 18 source modules. |
| Native sandbox boundary canary | **CONNECTED_VERIFIED component** | The reviewed TrueForge patch ran on the actual Linux host. The controlled host-owned `0600` canary supported the intended positive write/restore check while independent host bytes and metadata remained unchanged. Private/sibling reads and writes, process/environment access, direct private/IMDS access, and proxy-mediated access were denied; the proxy path returned 403. The session's own bridge socket was allowed and a foreign socket was denied. `BASH_ENV` was refused before launch. A timeout returned the explicit timeout result after 1,077 ms and the delayed child marker remained absent. The canary result was accepted as true. This proves the tested boundaries only; it is not a general Linux containment proof. |
| Saved native product agent | **CONNECTED_VERIFIED component / PARTIAL workflow** | Saved agent `preflight` (`01m3em9y0t7jqx20txq6s7pj39`), session `01m3emerb0g1f9cte1fpv1n4he`, turn `01m3emerb53n41nm53pp3znfnm`. The first attempt sent bare Python to the shell and exited 2. The model corrected itself by creating an explicit heredoc/script and invoking Python; sandbox call `call_t4C8Br4WdNBHQxYHXGaDDOlN` exited 0 and observed 1,000 rows, three columns, run state `ERROR`, and `cleanup_state=NOT_REQUESTED`. This is not a first-try success and is not a successful rehearsal. |
| Human gates | **CONNECTED_VERIFIED cleanup / source NOT_RUN** | The operator actually allowed cleanup at 10:42:10 UTC; receipt `da3e1dc4-60df-4fa4-b8f3-7d14d806f58d` records COMPLETE with clone and snapshot ABSENT. The coding agent did not click the gate. Source apply remains false. |
| RDS rehearsal | **NOT_RUN** | No run-owned snapshot, restored clone, source SQL apply, or complete bad-to-good connected rehearsal has occurred. |
| Failed-run resources | **CONNECTED_VERIFIED absence and cleanup receipt** | The real operator Allow produced COMPLETE, with both exact resources ABSENT. No resource was deleted and the source was untouched. |
| Budget admission | **LOCAL_VERIFIED implementation / BLOCKED_EXTERNAL publication** | The USD 100 operator ceiling is recorded, and protected publication plus durable admission/refusal code exists. Actual Cost Explorer facts remain `DataUnavailable`; current whole-footprint cost and a finite enforceable retention upper bound are unproved. Creation remains false. The publisher refuses missing, incomplete, estimated, stale, wrong-account, wrong-currency, or ambiguous facts. It does not implement or claim an AWS-native hard cap. |

The lead-owned sanitized evidence paths for this checkpoint are:

- `evidence/connected/local-sandbox-canaries.json`
- `evidence/connected/saved-agent-code-mode.json`
- `docs/audit/local-sandbox-verification.json`

The lead retained sanitized actual receipts, including `evidence/connected/cleanup-approval-request.json`. A second corrected postdeployment Code Mode call `call_cP0dXmj55AAFu40YuqzVek4Z` observed row_count=1000, column_count=3, phase=ERROR, cleanup_state=COMPLETE. A preceding N/A extraction is explicitly not accepted as business proof.

## What the local sandbox work implements

The native runtime remains TrueForge 0.2.1. The project does not add another agent framework or UI. The guarded vendor patch is version- and full-hash-bound and covers the runtime's actual CommonJS and ESM module forms. Its purpose is narrow:

1. Prefer a compatible per-session Python interpreter, avoiding the observed Python 3.9 PEP 604 failure when Python 3.12/3.11/3.10 is present.
2. Mount/read only the current session's trusted MCP Unix socket instead of exposing the shared socket parent, and reject untrusted or cross-session socket paths.
3. Remove agent-supplied process environment from the public execution schema and reject launcher-control variables before the host shell. Server-derived bridge/session values remain trusted inputs.
4. Preserve the existing filesystem and network restrictions without a broad private-network or filesystem bypass.
5. Convert the supervisor timeout into an explicit failed result and ensure the process group does not leave a delayed child action behind.
6. Keep the ten Preflight business tools and the two literal human gates. Generated Code Mode cannot hide source apply or cleanup inside an automatic program.

The saved-agent instructions now state that sandbox `exec` receives a shell command, so generated Python must use an explicit `python - <<'PY' ... PY` heredoc or a saved script followed by `python`. They also require `get_tool_info` before using an unfamiliar argument shape, a fresh UUID `request_id` for every Preflight call, and the actual `get_run.cleanup_state` field name. These instructions preserve both literal gates.

## File and module accounting

The following accounts for every path changed from the prior sealed local checkpoint `c19a1d4` through root `8048e79`. A changed file is not automatically a connected proof.

| Paths | Purpose | Verification / remaining limit |
|---|---|---|
| `.env.example`; `config/settings.example.json`; `src/preflight/config.py` | Replace Daytona readiness with the authorized local-sandbox settings and conservative defaults. | Local schema/config tests passed. Actual deployed settings must be re-read after the in-progress deployment. |
| `config/preflight-agent.yaml` | Saved native agent, exact MCP surface, Code Mode instructions, and literal approval lists. | Manifest validation and the affected nine-test check passed. One real corrected Python/MCP turn is recorded; full rehearsal and gates remain unrun. |
| `scripts/configure_trueforge_host.py` | Idempotent native provider/MCP/agent bootstrap using exact TrueForge routes and private transport. | Local route/privacy tests passed; current root deployment acceptance remains pending. |
| `scripts/patch_trueforge_local_sandbox.py` | Hash/version-guarded CJS+ESM patch for Python selection, per-session socket exposure, launcher-environment refusal, and explicit timeout handling. | Focused extraction/patch tests and the actual host boundary canary passed. Future TrueForge package changes require a new source review and hash, never a forced patch. |
| `scripts/probe_trueforge_local_sandbox.mjs` | Harmless host canary for allowed work, denied filesystem/process/environment/network/foreign-socket access, launcher injection refusal, and timeout cleanup. | Actual Linux receipt passed with the limits above. It intentionally uses inert canaries and does not touch AWS, RDS, credentials, or approval tools. |
| `scripts/publish_preflight_budget.py` | Root/operator-only publication of provider-reported spend plus trusted full-footprint bounds into the runtime ledger. | Synthetic provider tests passed. Real publication is blocked by missing complete Cost Explorer and retention facts. |
| `src/preflight/budget.py` | Canonical Decimal admission, reservations, freshness/scope checks, durable ledger state, and fail-closed reason codes. | Unit and boundary tests passed. It is an application admission control, not a native AWS account cap. |
| `src/preflight/aws_rds.py`; `src/preflight/runtime.py` | Require budget admission before billable create/restore intent and wire the durable ledger into runtime composition. | Local Stubber/runtime tests passed; no new snapshot or clone was created. |
| `scripts/verify_distribution.py` | Include the new runtime/config surface in reproducible distribution checks. | Covered by the frozen suite; final distribution must be rebuilt after all new evidence/docs land. |
| `tests/trueforge/test_configure_trueforge_host.py`; `tests/trueforge/test_local_sandbox_patch.py` | Exact native API routes, private bootstrap transport, patch transforms, both module formats, stale-hash refusal, socket scope, environment denial, Python selection, and timeout semantics. | Included in the 636-test gate. Test fixtures are not host proof; the separate canary supplies the bounded connected observation. |
| `tests/cloud/test_budget_boundaries.py`; `tests/cloud/test_budget_publication.py`; `tests/unit/test_budget.py`; `tests/cloud/test_rds.py`; `tests/unit/test_runtime.py` | Budget arithmetic, provenance/freshness, file ownership, provider response completeness, durable reservations, and pre-create refusal. | Included in the 636-test gate. All provider cost responses in these tests are synthetic/Stubs; live CE remained unavailable. |
| `README.md`; `docs/00_PRODUCT_AND_DECISIONS.md`; `docs/01_ARCHITECTURE.md`; `docs/03_BUILD_PLAN.md`; `docs/04_CLOUD_RUNBOOK.md`; `docs/05_TRUEFORGE_AGENT.md`; `docs/06_TEST_AND_EVIDENCE.md`; `docs/07_DEMO_AND_SUBMISSION.md`; `docs/09_BUILD_STATUS.md`; `docs/10_CODEX_OPERATING_SYSTEM.md`; `integration/DEPLOYMENT.md` | Record D26 local sandbox, D27 USD ceiling, deployment and canary procedure, evidence semantics, remaining human/cloud work, and truthful demo language. | Documentation reflects the implemented direction. Historical reports remain unchanged and must be read as historical snapshots. |
| `AGENTS.md`; `config/task-index.json`; `config/test-index.json` | Route ownership/model/task/test expectations to the authorized local-sandbox continuation. | Static routing only; these files are not execution evidence. |

No report/offline-verifier, SQL policy, transaction, verdict, human-gate, or public tool-schema implementation was weakened by this continuation.

## Task accounting

| Task | Current continuation assessment | Evidence gained | Still required |
|---|---|---|---|
| T04 — bounded AWS footprint | **BLOCKED_EXTERNAL** | USD 100 ceiling and fail-closed publication/admission code exist. | Complete current whole-account spend and enforceable future-retention bounds; protected publication; no creation until admitted. |
| T05 — private host/source/runtime identity | **PARTIAL connected** | Actual private host and native sandbox prerequisites/cgroup behavior were observed in the lead's connected work. | Accept the new deployed application revision and retain a complete current IAM/network/source packet. |
| T20 — TrueForge/model/sandbox/MCP compatibility | **PARTIAL connected** | Real saved native agent, model-generated Python, local sandbox execution, and MCP observation succeeded after one corrected shell invocation. Earlier Gateway linked-tool evidence remains separate. | A complete successful product workflow, provider failure cases, trace/privacy review, and all required scenario assertions. D26 supersedes the Daytona dependency; historical T20 text remains a historical snapshot. |
| T21 — deploy service and saved agent | **PARTIAL connected** | Saved product agent exists and called the private MCP through generated Python. | Finish and verify deployment of the current reviewed commit, restart behavior, exact config, private exposure, and durable state. |
| T22 — real synthetic RDS rehearsal | **BLOCKED_EXTERNAL** | Read-only source observation exists historically; no new resource was created. | Human-authorized budget admission, snapshot, private restore, TLS/ownership verification, and matching 1,000-row baseline on the clone. |
| T23 — real bad-to-good proof | **BLOCKED_EXTERNAL** | Local PostgreSQL proof remains valid. | Actual snapshot-restored RDS BLOCK then revised PASS with distinct exact candidate hashes and sealed reports. |
| T24 — deny/allow/replay demonstration | **NOT_RUN / BLOCKED_EXTERNAL** | Literal gates remain configured and source apply is false. | Accepted T27 packet first, then genuine human denial/no-change, explicit allow/one apply, receipt, source recheck, and replay refusal. The coding agent must not click either gate. |
| T27 — independent boundary review | **PARTIAL connected** | Independent reviews closed the shared-socket, stale helper/module form, launcher environment, timeout, and canary-oracle findings; host canary passed. | Final review tied to the deployed commit, actual IAM/private configuration, saved-agent/provider exports, and any remaining high/critical findings. |
| T28 — native experience/report | **PARTIAL connected** | Native saved agent and corrected Code Mode step are observable; instructions now match the actual shell API. | Judge-ready BLOCK/PASS/deny/apply/unknown flow on the real rehearsal without unsupported safety claims. |
| T29 — cleanup/retention | **CONNECTED_VERIFIED failed-run gate component** | Genuine operator Allow and COMPLETE absence receipt are retained. | Cleanup/retention of a future actual clone and recovery backup remains unrun. |
| T31 — final regression/review | **LOCAL_VERIFIED, connected incomplete** | 636-test gate, affected manifest tests, Ruff, and mypy passed. | Gate the final integrated/deployed revision and close all connected assertions. |
| T32 — submission | **BLOCKED_EXTERNAL** | Reproducible local materials continue to exist. | Final current distribution/evidence inventory, organizer fields, privacy review, and publication authorization. |
| T33 — pitch/recording | **NOT_RUN** | Runbook language exists. | Actual sanitized recording and evidence-led rehearsal with the human approver. |
| T34 — final read-only readiness | **BLOCKED_EXTERNAL** | This report gives the current honest start state. | Final post-deploy/source/resource/budget/gate audit immediately before the demo. |
| T35 — closeout | **NOT_RUN** | No new clone or manual snapshot exists to delete. | After the demo, record an explicit owner and retention/deletion decision for every remaining resource and observe only approved cleanup. |

All other tasks retain their prior local/connected classification. This continuation does not promote a whole task merely because one native component ran.

## Scenario accounting

The historical 153-scenario matrix remains the authoritative all-case inventory. Its old counts are not silently rewritten by this report. The current evidence changes or clarifies these specific rows:

| Scenario | Current evidence | Conservative status |
|---|---|---|
| M05 — saved agent uses actual provider | The saved `preflight` agent produced a native turn and generated a working Python/MCP execution after correcting its initial shell misuse. | **CONNECTED_VERIFIED component**; retain **PARTIAL** for the complete workflow until the receipt independently ties provider/model/resource and final response clauses. |
| M06 — generated sandbox Python chains MCP tools | Actual generated Python ran in the TrueForge local Linux sandbox and returned bounded aggregate values without credentials or raw rows. D26 replaces Daytona. | **PARTIAL connected** because the observed business run was already `ERROR` and no complete rehearsal chain occurred. |
| M07 — Code Mode calls gated source apply | The manifest forbids generated code from calling apply/cleanup and returns those operations to direct literal tools. | **NOT_RUN** for the required actual human pause; no gate was invoked. |
| N08 — Gateway route/model identity | Historical connected evidence records the approved Responses alias and resolved upstream model; the saved agent is now real. | **PARTIAL/connected component** until the final receipt binds adapter, API family, alias, resolved model, and saved resource in one reviewed packet. |
| N12 — streamed linked tool roundtrip | Prior native Gateway linked-tool evidence remains connected; the new saved-agent Code Mode call adds product-agent execution but is a different trace. | **PARTIAL** unless the final retained stream evidence satisfies every call-ID, argument, result-link, and continued-response clause. |
| N17 — MCP v2 and Code Mode result shapes | The actual Code Mode wrapper was exercised successfully after the shell correction. | **PARTIAL** pending independent receipt/schema accounting for every wrapper field and failure shape. |
| N20 — private transport policy | Loopback/private service and socket isolation are observed; own socket allowed and foreign socket denied. | **PARTIAL** unless the existing matrix's disallowed Host/Origin assertions are also tied to the deployed commit. |
| N22 — partial/invalid streamed arguments | No new qualifying malformed/partial delivery trace was created. | Prior **PARTIAL** unchanged. |
| N13, N15, N16, N19, N26 | No new complete auth/quota/timeout, exported-log privacy, telemetry, reconnect, or missing-trace-ID assertion was run. | Existing **BLOCKED_EXTERNAL**, **PARTIAL**, or **NOT_RUN** classifications remain. |
| N27 — prompt injection and approval invariance | Agent instructions and runtime bridge continue to keep SQL/tool output untrusted and gates direct. | **PARTIAL**; actual malicious saved-agent case and approval UI behavior remain unevaluated. |
| N29 — licenses/notices | No new license clearance or complete notice review was performed here. | Prior **PARTIAL** unchanged. |
| V23 — bounded Code Mode observation | The saved agent executed one bounded script; it did not demonstrate pending restore polling/backoff/checkpoint behavior. | Prior **PARTIAL** unchanged. |
| Native sandbox isolation/timeout assertions | Actual canary verified the enumerated filesystem, process/environment, network, socket, launcher, timeout, and host-integrity oracles. | **CONNECTED_VERIFIED boundary component**; these are bounded patch acceptance observations, not a claim that all 153 cases pass. |

### Agent evaluation cases

The successful native turn is not a substitute for the specified E01–E10 case suite. Each remains **NOT_RUN as a full evaluation**:

| ID | Case | Missing complete assertion |
|---|---|---|
| E01 | Normal rehearsal and revised candidate | No real clone, bad candidate, revision, good candidate, PASS, or awaiting-approval chain. |
| E02 | Instructions hidden in SQL comments | No actual malicious saved-agent trace. |
| E03 | Missing value coverage | No actual agent response to coverage-incomplete evidence. |
| E04 | SQL committed but data wrong | No connected clone/model explanation case. |
| E05 | Human denial | No genuine Deny action or source no-change receipt. |
| E06 | Stale/replayed apply | No genuine approved apply followed by replay refusal. |
| E07 | Unknown source commit | No connected unknown-outcome recovery trace. |
| E08 | Long pending cloud restore | No Code Mode backoff/deadline/checkpoint trace against a real restore. |
| E09 | Offline evidence substitution | No agent attempt to treat historical/unanchored evidence as current eligibility. |
| E10 | Provider failure and model fallback | No real provider failure trace proving bounded error and no unauthorized fallback. |

## Remaining dependency-ordered work

1. Sanitized native sandbox, two generated Code Mode traces, genuine cleanup Allow/COMPLETE receipt and the actual snapshot-start receipt are committed. Continue recording subsequent actual results.
2. The reviewed application and unlimited-budget delta are deployed, private state retained, both services active; the native read-only Code Mode probe returned exact aggregate values. Continue checking the same live run, not creating replacements.
3. D28 removes the numeric budget ceiling and authorizes the existing scoped run. Missing billing data remains unknown, but does not block this explicitly unlimited mode. Do not fabricate cost observations.
4. Wait for the actual creating snapshot, restore its one private run-owned clone, then verify TLS, ownership, provenance and exact baseline. No clone result is inferred from snapshot creation.
5. Run the real bad-to-good clone rehearsal and seal BLOCK then PASS evidence with distinct exact hashes. Complete remaining provider/runtime/privacy scenarios and E01–E04/E08–E10.
6. Obtain final independent T27 acceptance on the exact deployed build and evidence before T24.
7. With the human operator present, demonstrate E05 denial/no source change. Only under explicit approved scope demonstrate allow/one exact source apply, receipt, source recheck, and replay refusal. The coding agent does not click the gate.
8. Ask separately for the cleanup/retention decision. Record `NOT_REQUESTED`, denial, retention, or observed approved cleanup exactly; resource absence alone is not a gate result.
9. Rebuild the distribution and final inventory after evidence and this report land, run the final integrated gate, complete organizer fields/privacy review, and publish only with authorization.

## Current handoff state

- Source apply: **false**.
- Literal source-apply approval: **not requested/not clicked in this continuation**.
- Cleanup: **COMPLETE**, following genuine operator Allow; failed-run clone and snapshot were ABSENT.
- New run-owned RDS clone/manual snapshot: **none**.
- Billable creation: **disabled/refused without complete protected budget facts**.
- USD ceiling: **100**, with current CE facts unavailable and finite-retention bound unproved.
- Saved-agent native Code Mode: **one corrected successful sandbox execution**, preceded by one exit-2 bare-Python shell mistake; business run remained `ERROR`.
- Full local gate: **641 passed**, zero failures/errors/skips, `263.60s`, at `878d64a`.
- Manifest follow-up: **nine affected tests passed**, `5.46s`, at `8048e79`.
- Final connected acceptance: **incomplete**.


## Latest operator amendment and remaining proof

The operator has explicitly removed the USD100 ceiling. The explicit unlimited-budget configuration is implemented and deployed; this does not fabricate unavailable billing facts or waive ownership, private networking, SQL validation, or human source/cleanup gates. The previous budget blocker is historical once that amendment is deployed. Real snapshot/clone, bad/good migrations, source Allow/Deny and the three-minute recording are still not claimed complete. An optional heavily instrumented function-call diagnostic was interrupted after two failures, before its summary; the exact failure reasons were not established; the standard 641-test gate passed, and no current whole-function coverage is inferred.
