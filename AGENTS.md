# Preflight repository instructions

## Mission and authority
Implement and verify Preflight, not another proposal. Preserve `reference/Preflight-PRD.md` byte-for-byte. Organizer rules and explicit operator authorization constrain execution; numbered decisions in `docs/00_PRODUCT_AND_DECISIONS.md` record researched amendments; docs 02 owns tool/safety semantics, 01 architecture, and 03 task order.

## Read by task, not by ritual
Read `docs/09_BUILD_STATUS.md` when resuming. The lead uses `docs/10_CODEX_OPERATING_SYSTEM.md` for model/worker setup. Product decisions route to 00, service boundaries to 01, SQL/transactions/tools to 02, cloud to 04, TrueForge/Gateway/Daytona to 05, verification to 06, presentation to 07, and upstream evidence to 08. Load only the relevant task sections. The four `.agents/skills/` entries are narrow routers, not a requirement to read everything.

## Product invariants
- One allowlisted, owned synthetic RDS source; a separate private snapshot-restored clone. No fake RDS evidence or third-party production access.
- TrueForge bundled UI/agent, OpenAI model, Daytona Code Mode and Python MCP. Prefer the documented AI Gateway path after a real endpoint/tool probe; do not replace the required runtime with Codex, another framework or a second dashboard.
- Exact SQL bytes/hashes. Deterministic complete checks decide PASS/WARN/BLOCK. The model explains; it cannot redefine expectations or confer approval.
- Source apply only through the literally approved tool and fresh server guards; cleanup has its own human gate. The coding agent must not click either gate for the operator.
- No raw rows, AWS/DB credentials or connector secrets in prompts, sandbox output, logs, reports or Git. Private service endpoints only.
- Unknown source commit outcome is not rollback and is never an automatic SQL retry. Successful migration is not automatically reversible.

## Safe autonomy
Routine repository edits, disposable local tests, debugging and integration are authorized within the task. Continue until acceptance, not first-pass code. Do not repeatedly ask permission for these. Missing cloud access blocks connected proof, not independent work. Do not build application code before the permitted event start; do not infer cloud spend, source reset, publishing or destructive resource permissions. Respect the host's actual sandbox/approval policy. Avoid broad bypass flags.

## Sol-first model admission
The lead, DB and cloud use GPT-6 Sol/high; integration uses GPT-5.6 Sol/high; routine independent review uses Sol/high. All primary tasks stay on these models. `config/model-policy.json` governs at most two bounded Astra/high read-only sessions before further user authorization. Log the A1/A2 ticket before spawning; never use Astra as an automatic implementation, quota or runtime fallback. No default Fast, Pro, Ultra, xhigh or max. Check actual effective role settings, not only a prompt. This is a workflow rule, not a native spend-cap guarantee.

## Workers and verification
Use `config/task-index.json` and docs 10: at most three child threads plus the lead, no grandchildren by workflow, one owner per path, explicit isolated checkout, frozen shared interfaces. A custom-role model setting can override a spawn request; verify effective settings. The lead integrates commits and owns shared schemas/lockfiles. Review is read-only and cannot approve itself. A sandbox-mode setting does not by itself restrict connected MCP tool permissions.

Run affected tests after changes; full suites at integration gates, not redundantly after every trivial edit. Never weaken acceptance tests to obtain green. Distinguish NOT_RUN, FAILED, BLOCKED_EXTERNAL, LOCAL_VERIFIED and CONNECTED_VERIFIED. Record actual command, commit, backend and sanitized evidence. Update the ledger at task boundaries; a native Goal is thread-scoped, so it does not replace durable repo state. Never claim a subagent, model, cloud action or test ran without its actual trace.


V3 acceptance: every written column needs supported preservation/intended-change coverage. A missing value assertion is not solved by counting rows. Sealed reports expose a versioned requirement manifest; offline verification distinguishes trusted-digest match from unanchored consistency and never asserts current source eligibility. T27 independent boundary review must be accepted before T24's live apply demonstration. All baseline, transaction, privacy and human-approval safeguards remain mandatory.
