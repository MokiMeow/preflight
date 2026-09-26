# Preflight — start here

**V3 · Sol-first · researched 25 September 2026 · implementation kit, not an already-built application.**

Open this extracted folder as the repository root, including its hidden `.codex` and `.agents` directories. Do not paste all the files into one chat. The lead reads the routing files and loads each task's specification when needed.

## Start the build

At the organizer-authorized implementation start on **26 September 2026**, paste:

```text
Read AGENTS.md, docs/09_BUILD_STATUS.md, and docs/10_CODEX_OPERATING_SYSTEM.md.
You are Preflight's lead implementation agent. Execute the dependency-ordered
build in docs/03_BUILD_PLAN.md and config/task-index.json, starting at T00.
Use GPT-6 Sol/high as lead and GPT-5.6 Sol/high for its assigned workers.
Follow config/model-policy.json: Astra is not a normal implementation model.
Use only admitted bounded A1/A2 reviews or a qualifying critical-blocker ticket.
Use the verified model/role assignments, narrowly loaded skills, isolated
worktrees and integration gates. Establish a native thread Goal when supported;
otherwise use the repository ledger. Do not return another implementation plan.

Build and verify the complete original product: TrueForge + an OpenAI model,
Daytona Code Mode, the Python MCP service, a real private snapshot-restored RDS
clone, deterministic reports, actual human approval, guarded source apply,
unknown-outcome recovery and deliberate cleanup. Prefer TrueFoundry AI Gateway;
verify the model API route before choosing its adapter. Preserve every safety
invariant and the unchanged source PRD. Read detailed docs only as the task needs.

Own integration, debugging and final evidence. Continue authorized local work
without asking for each routine edit or test. Do not stop at scaffolding, mocked
integrations or unit tests. Consolidate external blockers and continue independent
work. Never infer permission to spend, expose secrets, change an AWS account,
press the product's human-approval buttons, or retry uncertain source SQL.

Finish only at the observable acceptance gates, or give the implemented work plus
precise external blockers and a resumable checkpoint. Keep the ledger truthful.
```

The default is **GPT-6 Sol / High** for the lead, database and cloud work; **GPT-5.6 Sol / High** for the integration/report lane. **All 36 primary task assignments are Sol High.** Routine independent reviews also use Sol High. Astra High is a read-only specialist with **at most two admitted sessions** before another explicit user authorization: one focused pre-apply review and one conditional safety-delta/critical-blocker review. Sol makes the fixes. The native runtime stays on a tested Sol route, not Astra.

The exact [model policy](config/model-policy.json), role settings, fallback rules, review ticket and task map are in [10](docs/10_CODEX_OPERATING_SYSTEM.md). These are assignments for this project, not benchmark rankings or a claim of a guaranteed percentage saving. The workflow cap is not a vendor-enforced monetary limit.

## Before the first task

Use the account's installed Codex surface. The retained, source-rechecked CLI baseline is **0.157.0 (25 September)**; the app and extension have their own versions. T01 checks the actual CLI, model availability and effective configuration before spawning workers. Do not install a second competing global binary, overwrite personal settings or enable permission bypasses. A coding subscription and a runtime API/Gateway account are separate.

**Timing correction:** the official organizer's indexed provisional agenda distinguishes 09:00 check-in from **12:00 building**, with submission at **19:00** and demos afterward. The canonical HackCulture page did not render reliably in this audit. The final invitation/on-site rules control; T00 resolves the actual coding start before implementation. See [00](docs/00_PRODUCT_AND_DECISIONS.md).

## What is in the folder

| Read when | File | Purpose |
|---|---|---|
| Initial orientation | [AGENTS.md](AGENTS.md) | Small routing file and permanent invariants |
| Resume / current state | [09](docs/09_BUILD_STATUS.md) | One honest task/evidence ledger |
| Lead setup or delegation | [10](docs/10_CODEX_OPERATING_SYSTEM.md) | Models, Goals, skills, worktrees, permissions and recovery |
| Product or scope decision | [00](docs/00_PRODUCT_AND_DECISIONS.md) | PRD amendments, organizer evidence and decisions |
| Implementation boundaries | [01](docs/01_ARCHITECTURE.md) · [02](docs/02_CONTRACTS_AND_SAFETY.md) | Modules, states, SQL policy and ten tool contracts |
| Next executable work | [03](docs/03_BUILD_PLAN.md) | 36 dependency-linked task cards with model/effort/skill |
| External integrations | [04](docs/04_CLOUD_RUNBOOK.md) · [05](docs/05_TRUEFORGE_AGENT.md) | AWS, TLS, Gateway/API compatibility, runtime agent |
| Proof and delivery | [06](docs/06_TEST_AND_EVIDENCE.md) · [07](docs/07_DEMO_AND_SUBMISSION.md) | Tests, real demonstration and submission |
| Version/source question | [08](docs/08_RESEARCH.md) | Dated primary sources, evidence levels and unresolved checks |
| Original proposal | [PRD](reference/Preflight-PRD.md) | Original bytes retained; amendments are not silently inserted |

There are **four small on-demand skills** and five role configurations (only one exceptional Astra role), not another duplicate documentation tree. Configuration examples contain no credentials, application implementation or claim of successful live tests.

## Operator-only inputs

[Operator template](config/operator-inputs.example.json) records the event start, permitted AWS account/region/resource budget, synthetic source/reset permission, provider access and submission settings. Discover nonsecret identifiers through authorized read-only tools before asking the operator. Keep secrets in the approved provider/secret settings, never in chat or checked-in JSON.

A blocker in one provider does not justify stopping unrelated local work. It also does not turn a simulated provider into connected evidence. The literal source-apply and cleanup decisions remain the engineer's actions in TrueForge.

## Acceptance, not a promise

The deliverable is complete when the actual connected gates in [06](docs/06_TEST_AND_EVIDENCE.md) pass, security findings are resolved and the submission is runnable. Archive validation only checks the kit's structure and consistency. It does not mean Codex, AWS, the Gateway, Daytona or the application has been run on your accounts.


## What V3 adds without changing your idea

The same full TrueForge/RDS/Daytona/MCP build is retained. V3 adds column-level acceptance coverage so an unasserted value change cannot pass; a credential-free offline report verifier; a pre-live-apply independent review dependency; a trace-based agent-behavior evaluation plan; and bounded read-only polling instead of a model turn per AWS poll. These are explicit design amendments, not claims that the application has already been implemented.

Use this V3 folder on its own. Do not mix an older Astra-default `.codex` directory into it. In an already-started repository, preserve actual code, run state and evidence; apply the specification/config changes as reviewed diffs, never overwrite a real build ledger with this initial template.
