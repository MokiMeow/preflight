# 10 — Coding-agent operating system

This is the **builder workflow**, not the deployed agent architecture. It turns the detailed specifications into executable work without loading the entire kit on every turn. Model allocation, concurrency limits, stopping rules and task strategy below are our project-specific recommendations. Upstream feature facts and evidence levels are in [08](08_RESEARCH.md).

## 1. Sol-first model policy and bounded expert review

The user's explicit priority is to use **GPT-6 Sol and GPT-5.6 Sol at High**, not burn Astra allowance on the whole build. Every primary task below follows that preference. Model names/capabilities are sourced in [08](08_RESEARCH.md); assignments and the cap are our workflow design, not empirical model rankings.

| Job | Requested model / effort | Execution rule |
|---|---|---|
| Lead, shared interfaces, architecture, core use cases, integration decisions | GPT-6 Sol / high | Own the project continuously; do not hand the lead to Astra. |
| SQL policy, database transactions, row/schema evidence | GPT-6 Sol / high | Same detailed contracts, tests and independent checks as before. |
| Cloud lifecycle, IAM, networking, deployment | GPT-6 Sol / high | Single authorized mutation owner; no parallel source/reset actions. |
| TrueForge/TrueForge local sandbox integration, report verifier, native report presentation, submission | GPT-5.6 Sol / high | Narrow owned lane; use a tested GPT-6 Sol/high fallback if necessary. |
| Routine independent review and regression | GPT-6 Sol / high, read-only context | Different context from the implementer, exact commit and concrete reproductions. |
| Exceptional safety audit or qualifying critical blocker | GPT-6 Astra / high, read-only | Only through a recorded unused A1/A2 ticket; return findings and close. |
| Deployed TrueForge runtime | GPT-6 Sol / high, tested Responses route | Tested GPT-5.6 Sol/high alternative; no runtime Astra and no silent per-turn switching. |

### Admission, not an unbounded expert loop

The machine-readable authority is [model-policy.json](../config/model-policy.json). All ordinary coding, dependency troubleshooting, read-only research, tests, documentation and repairs use Sol High. Do not automatically enable Fast, Pro/Ultra, xhigh or max; do not fabricate a native Codex budget key.

**A1:** at T27, one focused audit of the **implemented** SQL confinement, evidence/coverage, report sealing, source-apply and cleanup boundaries before T24. Run the ordinary independent Sol audit first so Astra receives the difficult residual questions rather than the entire repository. Include the successful tests as well as unresolved assumptions; Astra may find a defect the earlier audit missed.

**A2:** at T34, one **delta-only** audit if safety-relevant code/configuration changed since A1. No material delta means skip, record the reviewed commit and retain the slot; do not pay for an identical full review. A2 can instead be used for a qualifying critical blocker during implementation. Slots are not replenished when a problem is solved or the chat compacts. Prefer spending A2 on an early critical blocker. If A1 was legitimately consumed earlier, T27 still needs independent review at its actual implemented commit; use Sol or the remaining admitted slot, never silently create a third expert session.

A qualifying blocker threatens correctness or safety of SQL confinement, data evidence, credential boundaries, approval, commit outcome, replay guards or recovery. Ordinarily provide a reproducible failure plus **two materially different Sol diagnosis/repair attempts**. Immediate credible data-safety risk may justify earlier expert review. Missing credentials, AWS pending state, quota/permission errors, formatting, routine syntax and generic “this is hard” are not expert triggers. Stop a dangerous path immediately; do not reproduce a destructive bug on the shared source.

The lead alone admits these reviews after releasing a child slot; the ordinary Sol reviewer must not spawn Astra or grandchildren. At most two Astra investigations, one active at a time, without a further explicit user extension. A critical investigation consumes an existing slot, it is not a third exemption. Write the ticket before spawning. After the cap, continue safe Sol work and request authorization only for additional Astra use; an unresolved critical/high safety finding continues to block the relevant live path. A model cannot reason an unknown database commit into a known rollback.

Astra returns one bounded findings packet and closes. Sol implements repairs and runs the safe reproductions. A reopened extended investigation consumes a further slot. Aim for no more than about 12,000 input tokens of targeted context and 1,500 words of findings. These are **routing targets**, not API-enforced token caps; never hide important evidence to meet them. Explain a needed expansion instead of silently turning an expert review into a full implementation session.

### Review ticket and observed-usage ledger

```text
Slot / triggering task:
Exact commit and safety question:
Why Sol review/diagnosis is insufficient:
Reproducer, expected/actual behavior, and two different attempts (or urgent risk):
Permitted files/diff and sanitized evidence paths:
Requested model/effort: gpt-6-astra / high
Actual model/effort observed:
Scope: read-only findings; no writes, cloud effects, approval or delegation
Usage before/after and units, only if exposed:
Finding IDs / owning Sol task / exact follow-up tests:
Session closed; slot consumed:
```

Record this in the dedicated section of [09](09_BUILD_STATUS.md); unavailable usage stays `NOT_OBSERVED`/null. With ChatGPT sign-in, account allowance is not the same as your API invoice. Context length, output/reasoning, account limits and modes affect consumption. The policy limits when the workflow asks for Astra; **it is not a hard vendor spend cap or a guaranteed saving**.

### Fallbacks and model selection

Use the exact model ID accepted by the installed Codex surface, not an invented suffix or label. Prefer the assigned role. If either Sol is unavailable, the other Sol/high can cover that lane with the same tests; record the effective model and reason. If both are unavailable, keep the work checkpoint and report the actual account blocker rather than silently promoting the entire build to Astra. A one-model Sol build is an acceptable compatibility mode.

If Astra is unavailable at a scheduled audit, use a genuinely separate Sol High reviewer with identical evidence/acceptance and explicitly record the substitution. No fabricated Astra trace, no waived safety finding and no automatic extra purchase. For a suspected solver blind spot, a separate sanitized Sol session can examine a minimal reproducer before any new paid service is considered.

## 2. Installed capability gate (T01)

The research baseline is Codex CLI **0.157.0, 25 September 2026**, not the older 0.154 release mentioned in the prior discussion. The app/extension need their own version observation. Inspect existing installation and configuration first; preserve personal settings. Where an update is permitted, install the official package at that explicit version, not an arbitrary third-party installer. Do not repeatedly update during the build.

Record `codex --version`, supported commands from `codex --help`, Python/Node/package manager versions, effective model and role settings, active MCP tools, project trust and sandbox/approval policy. Save observations to a local copy of [the capability template](../config/capability-probe.example.json). A command appearing in docs is not proof the installed app exposes it.

The shipped `.codex/config.toml` sets the lead, default child model and **three child threads**; the primary thread is additional. The source schema does not define `max_spawn_depth`. Do not add it. The older `max_depth` field is backend-specific, so the no-grandchildren rule is enforced by the assignment/admission workflow, not represented as a universal sandbox limit.

Custom role files are under `.codex/agents/`, and the skills are under `.agents/skills/`. A **role file's explicit model/effort can win over an explicit spawn value**. Before launching a batch, the lead checks its task card against the effective role config. For an authorized model fallback, update only the inactive project role configuration and record it before spawning, or use a supported fresh session whose effective settings match. Do not raise the effort above High without the user's explicit instruction. Do not edit a role under an active child or claim a prompt alone overrode it. Use a single-model sequential lane if the current surface cannot do this reliably.

Read-only sandbox mode restricts filesystem work, not necessarily connected tool side effects. Inspect and disable/scope unrelated inherited MCP/connectors before giving a worker a task. The database/integration/reviewer lanes do not need cloud-admin tools, source-writer secrets or operator browser credentials. Never publish private endpoints to make a build tool reach them.

## 3. One persistent objective, precise stopping condition

Where supported, establish a thread Goal with the kickoff objective:

```text
Complete Preflight's T00–T35 build and evidence plan for the permitted event:
real TrueForge/OpenAI/TrueForge local sandbox/MCP/RDS rehearsal, deterministic reports, actual
human-controlled source apply, failure/recovery/cleanup controls, and a runnable
honest submission. Stop only at observed acceptance or named external blockers;
continue all independent authorized implementation work.
```

The documented interactive commands include `/goal`, `/goal pause`, `/goal resume` and `/goal clear`. Check availability instead of inventing a shell flag. Goals are **thread-scoped**; the repository ledger remains authoritative across new chats, process failures and worktrees. A paused/budget-limited Goal does not mean the application is complete. It also never authorizes spend, approval clicks or mutations outside the operator's scope.

## 4. The lead's execution loop

Read the ledger and Git state. Select ready tasks whose prerequisites actually passed. Open only their relevant specification sections. Make the interfaces/test oracle explicit, assign one owner and launch bounded workers where independent. Meanwhile the lead implements its own unblocked shared-state/integration work. Inspect returned diffs and tests, integrate one patch at a time, run the affected shared tests, record evidence and release the next tasks. Repeat until the actual acceptance packet is complete.

Do not ask a second model to re-ideate the product or generate another 30-file plan. Clarify only true external blockers that cannot be discovered through authorized reads. For ordinary implementation decisions, choose the smallest design consistent with the specification, record any material deviation and continue.

**Early risk ordering:** T00 rules/provenance → T01 toolchain alongside T04 read-only AWS discovery → T02 interfaces → T03 runnable shell → T20 real provider/TrueForge local sandbox compatibility spike while database/cloud work proceeds. T20 is not delayed until the database engine is finished. No live source apply is part of that harmless probe.

## 5. Parallel work with actual isolation

A subagent is not automatically an isolated checkout. After T02's shared-interface commit, create ordinary Git worktrees or use the installed native worktree feature after checking its behavior. Use a fresh non-existing branch/path, preserve user changes and record the base commit. Example after the clean initial commit, from the repo root:

```bash
git worktree add .worktrees/db -b preflight/db
git worktree add .worktrees/cloud -b preflight/cloud
git worktree add .worktrees/integration -b preflight/integration
```

These are ordinary Git operations, not a claim that the folders exist in this kit. Each worker receives the explicit checkout and confirms `git rev-parse --show-toplevel`, branch and HEAD. Ensure the harness actually permits that worktree path. If native subagents cannot bind an independent working directory, use supported separate Codex sessions in those worktrees; otherwise run writers sequentially. Do not let two agents edit the same checkout and describe that as isolation.

Three useful writing lanes: DB, cloud, integration. Keep the integration lane on 5.6 Sol/high and DB/cloud on 6 Sol/high so the lead does not pay repeated context warm-up by switching each task. The reviewer uses a slot after a patch is ready; do not create a fourth unbounded lane just because a fourth role file exists. The lead owns shared schemas, service composition, storage/security policy, lockfiles and final integration. Child instructions prohibit further delegation. Close completed threads so the cap does not fill with idle agents.

Use separate disposable local databases, ports and state directories per writer/test worker. Only the lead/integration owner conducts a shared end-to-end run. A cloud task receives a run/resource lease; concurrent agents must not create multiple clones, restore a different snapshot or reset the shared synthetic source. Human approval remains human even when browser automation is available.

## 6. Dispatch and handoff contracts

A worker receives this short assignment, filled from the task index:

```text
Task: <ID and objective>; model/effort actually selected: <observed values>.
Checkout: <absolute path>; base/interface commit: <SHA>.
Allowed writes: <specific paths>. Read: <skill and relevant doc sections>.
Required behavior: <task acceptance>; tests/evidence: <exact target>.
Forbidden effects: no shared schema/lockfile changes, no unapproved external
mutations or human approval clicks, no further agents.
Return your commit, changed paths, exact tests/results, assumptions, blockers
and the smallest integration note. Do not return only a proposal.
```

Handoff is evidence, not “done.” The lead inspects each changed path and commit, checks a worker did not modify contracts/tests to hide failures, cherry-picks or merges the intended patch, then reruns the affected integration. Cherry-pick specific commits, not an unreviewed branch sweep. Keep the worker's evidence separate from the final integrated evidence. If an interface must change, the lead changes it once and communicates the new revision to every affected lane.

For an unresolved critical boundary defect, the lead may admit the scoped Astra reviewer only under section 1 and an unused A1/A2 ticket. Prefer repurposing A2 so A1 remains available for the pre-apply review. Sol retains implementation ownership and every repair receives independent recheck. Expert opinion never establishes an unknown transaction outcome without actual evidence. Do not restart or re-ideate the project.

## 7. Prompting and context discipline

The acceptance contract is strict; the path to implementation need not be micromanaged. Root instructions are a router. The four skills contain narrow descriptions and point to detailed specs. Long task/reference files are not injected into every role. No redundant full-repository searches, repeated independent research on the same upstream fact, or “read all files before every edit” ritual, no repeated exhaustive testing after a typo, no requests to output private reasoning. Ask for assumptions, decisions, evidence and concise blockers instead.

Use shell/files/API tools for structured work, then browser automation for the actual native UI, console/network checks and screenshots. Avoid token-heavy screenshot-by-screenshot interaction when an official API or DOM locator can do the same authorized read. Do not use browser automation to impersonate the human approval. Never enter provider credentials into an arbitrary third-party page or copy them into screenshots.

At task boundaries, persist the next executable task, current commit, exact passing/failing evidence and external blockers. Before compaction or switching sessions, write a short resume packet. A new session inspects files/evidence, then continues; it does not assume an unacknowledged DB write rolled back. Compaction is not a backup or proof of atomicity.

## 8. Hooks, plugins, remote and newer ergonomics

Use capabilities when they reduce risk, not to accumulate features. Native worktree/fork/resume/steering and the newer background-server behavior are optional ergonomics and version-gated. They do not supply credential access or keep an external database operation safe by themselves. Background-server recovery must read the same project/run state; a changed host process does not authorize a new migration attempt.

Hooks are optional bookkeeping only. No active hooks are installed here because their commands would point at application scripts not yet written. If added later, review/trust their exact configuration, use supported command hooks, check current event/async support and test that they cannot loop forever or claim completed work. Hooks are not a security boundary or an automatic approver.

Only add official, task-relevant documentation/browser tools after reviewing their permissions. Do not install a pile of plugins or attach cloud-admin MCP tools to every child. The new managed Agents API, additional agent frameworks, RAG/vector stores and a second frontend are not required to implement this product. TrueForge remains the submitted runtime. Remote steering can leave a concise note for the lead, but it must not race another writer or approve an irreversible action accidentally.

## 9. Task-by-task requested routing

The detailed subtasks and evidence live in [03](03_BUILD_PLAN.md). The table below is generated from the same JSON index, not a second independent backlog. “Review” means independent correctness/security review in addition to lead integration.

| Task | Owner | Requested model | Effort | Skill | Routine review |
|---|---|---|---|---|---|
| T00 | lead | gpt-6-sol | high | task routing | Lead |
| T01 | lead | gpt-6-sol | high | preflight-integration | Lead |
| T02 | lead | gpt-6-sol | high | task routing | Sol High |
| T03 | lead | gpt-6-sol | high | preflight-integration | Lead |
| T04 | cloud | gpt-6-sol | high | preflight-rds | Sol High |
| T05 | cloud | gpt-6-sol | high | preflight-rds | Sol High |
| T06 | lead | gpt-6-sol | high | task routing | Sol High |
| T07 | database | gpt-6-sol | high | preflight-db | Sol High |
| T08 | database | gpt-6-sol | high | preflight-db | Sol High |
| T09 | database | gpt-6-sol | high | preflight-db | Sol High |
| T10 | lead | gpt-6-sol | high | preflight-db | Sol High |
| T11 | integration | gpt-5.6-sol | high | preflight-integration | Lead |
| T12 | cloud | gpt-6-sol | high | preflight-rds | Lead |
| T13 | cloud | gpt-6-sol | high | preflight-rds | Lead |
| T14 | lead | gpt-6-sol | high | preflight-db | Sol High |
| T15 | lead | gpt-6-sol | high | preflight-db | Sol High |
| T16 | lead | gpt-6-sol | high | preflight-db | Sol High |
| T17 | cloud | gpt-6-sol | high | preflight-rds | Sol High |
| T18 | lead | gpt-6-sol | high | preflight-integration | Sol High |
| T19 | lead | gpt-6-sol | high | preflight-verification | Sol High |
| T20 | integration | gpt-5.6-sol | high | preflight-integration | Sol High |
| T21 | integration | gpt-5.6-sol | high | preflight-integration | Sol High |
| T22 | cloud | gpt-6-sol | high | preflight-rds | Lead |
| T23 | integration | gpt-5.6-sol | high | preflight-integration | Lead |
| T24 | integration | gpt-5.6-sol | high | preflight-integration | Lead |
| T25 | database | gpt-6-sol | high | preflight-db | Sol High |
| T26 | lead | gpt-6-sol | high | preflight-verification | Sol High |
| T27 | reviewer | gpt-6-sol | high | preflight-verification | Sol High |
| T28 | integration | gpt-5.6-sol | high | preflight-integration | Lead |
| T29 | cloud | gpt-6-sol | high | preflight-rds | Sol High |
| T30 | lead | gpt-6-sol | high | task routing | Sol High |
| T31 | lead | gpt-6-sol | high | preflight-verification | Sol High |
| T32 | integration | gpt-5.6-sol | high | preflight-verification | Lead |
| T33 | integration | gpt-5.6-sol | high | preflight-verification | Lead |
| T34 | lead | gpt-6-sol | high | preflight-verification | Sol High |
| T35 | cloud | gpt-6-sol | high | preflight-rds | Lead |

A1 at T27 and conditional A2 at T34 are separate bounded read-only reviews, **not** alternate primary task assignments. See section 1. T24 depends on accepted T27; the source-apply gate must not be tested live before that review.

## 10. Completion and escalation

The actual final acceptance packet, not token count or number of agents, controls completion. All live evidence is labeled with its backend/commit. The engineering team must understand the source-approval path, report hash, source/clone distinction and unknown-outcome policy well enough to explain them without reading a model transcript.

If external access is missing, finish all independent code, tests, documentation and read-only checks; mark the connected gates BLOCKED_EXTERNAL/NOT_RUN and provide the precise next authorized action. Do not silently substitute local PostgreSQL for RDS or a local process for TrueForge local sandbox. No workflow or model assignment guarantees a hackathon result, but nothing in this plan permits dropping the defining product behavior merely because it is difficult.

Operator amendment D26 replaces the original Daytona runtime with the installed native local Linux sandbox; historical upstream research and the immutable PRD retain their original scope. D27 authorizes a USD100 continuation ceiling, not a fabricated instantaneous provider spending stop.
