# 08 — Research, change log and evidence limits

**Research snapshot: 25 September 2026.** This is an implementation-oriented audit of current primary documentation, version-tagged source and the supplied PRD. It is not a claim that every page on the internet was read or that any account integration has already passed.

## V3 changes and what was actually rechecked

The current user preference supersedes V2's Astra-heavy model allocation: **all primary build tasks and ordinary reviews use Sol High**, with a two-session admission policy for exceptional Astra reviews. No API price is treated as an estimate of the user's subscription allowance. The task/role defaults, fallbacks, runtime prompt, ledger and tests were changed together; this is not a cosmetic kickoff change.

| Area examined | Result in V3 | Evidence/remaining uncertainty |
|---|---|---|
| Original idea and all V2 specifications/configuration | Original PRD bytes and full real-system architecture retained | User source plus archive inspection; not a claim of implemented features |
| Event fit and value | Preserve actual harness, generated sandbox code and human stop; clarify differentiation | Fresh official indexed organizer rubric; canonical HackCulture body still not fully recovered |
| Builder models and allowance | 6 Sol/high lead/DB/cloud; 5.6 Sol/high integration; Sol routine review; bounded expert tickets | Official model/usage docs; no user-account model call, allowance or billing observation |
| Subagents/configuration | Match actual role precedence, cap children, close reviewers and isolate writers | Current docs and pinned schema section; effective installed behavior still T01 |
| TrueForge/Daytona orchestration | Keep tested Responses route and same ten tools; no runtime Astra; bounded Code Mode observations | Pinned Code Mode source freshly re-read; package installation/API route remains a live probe |
| SQL and data correctness | Add column-level acceptance coverage and requirement-result linkage; strengthen per-capture consistency | New design derived from inspection; PostgreSQL isolation/lock/RLS docs rechecked; real regressions still required |
| Source apply/recovery/cleanup | Retain exact bytes, fresh locked drift check, intent journal and unknown-outcome block; review precedes live apply | Existing detailed contracts plus V3 dependency change; no AWS/source action performed |
| Artifact integrity | Add offline verifier and independently supplied digest option with explicit unanchored limitations | New project design, not a vendor-provided feature; tamper tests are specified, NOT_RUN |
| Comparable tools | Acknowledge Atlas migration assertions and Flyway SQL dry-run previews | Fresh primary vendor documentation; no universal novelty/best-tool claim |
| Model/tool behavior | Add a concrete trace-based evaluation plan and no mutation in polling loops | New project test plan; no simulated result called connected proof |
| Toolchain/security/deployment | Preserve existing version-pair, TLS, private-network, IAM, secret, telemetry and license checks | Sources not freshly re-opened are left as inherited evidence; install/account compatibility remains pending |
| Demo/submission | Keep one complete causal chain plus prepared wrong-data/coverage/tamper proof; avoid feature sprawl | Rubric-informed design decision, not a predicted win or a score |

This review does not prove that no further improvement is possible. It does identify concrete correctness, cost-control and presentation changes and their tests. Source entries retain their original evidence levels; a `v3_recheck` annotation means only the named item was retrieved again. Neither this register nor the archive validation substitutes for runtime testing.

## Retained V2 research and changes

| Finding | Concrete kit change | Verification still required |
|---|---|---|
| Codex CLI 0.157.0 is the currently retrieved dated release, not 0.154 | Exact research baseline; schema-compatible agent settings; model/task map | Installed binary and effective model/permissions |
| Current model APIs differ in tool-call transport | Early T20 route probe; Astra Responses-only tools; Sol/high Responses preferred | Gateway entitlement, endpoint, stream/tool/result behavior |
| TrueForge adapter source distinguishes Responses from compatible chat | Use actual provider adapter, model resource and base URL; no blind custom-provider model swap | Installed UI/API shape and actual Gateway route |
| Native subagent settings can override spawn requests | Verify effective model/effort; three children, explicit worktrees and narrow ownership | Current surface's actual spawning/isolation support |
| New prompting guidance discourages universal prompt bloat | Small AGENTS router, four on-demand skills, detailed specs retained | Whether the installed harness discovers those files |
| Native Goals are thread-scoped | Goal plus durable task/evidence ledger | Feature availability and actual resumption behavior |
| Official event text became accessible through indexed organizer pages | Rubric, provisional agenda, pitch and public-repo/disclosure checks | Canonical/final invitation or on-site overrides |
| Gateway descriptions conflicted | Prefer Gateway, do not falsely declare it mandatory; disclose permitted fallback | Final organizer rule and account route |
| MCP v2/source and package-page caches need distinction | Source-tag verification, explicit v2 migration/telemetry checks | Registry resolution and TrueForge wire interoperability |
| Restore readiness does not imply warmed storage | Storage/network/TLS checks and honest clone timing labels | Live source/clone observations |
| Distribution has non-MIT third-party code | License/integrity inventory including pglast metadata | Operator's project license/public distribution decision |

## Evidence vocabulary

`PINNED_SOURCE_READ` means the named tagged/committed file was read. `OFFICIAL_DOC_READ` means official page content was retrieved. `OFFICIAL_INDEXED_CURRENT/TEXT` means the official site's indexed content was available even when a direct fetch was stale or failed. `BASELINE_DOCUMENTATION` and `PRD_AND_BASELINE_REFERENCE` identify inherited sources not falsely presented as newly revalidated end-to-end. `FETCH_INCOMPLETE` is not evidence of a page's unseen content.

None of these statuses means `INSTALLED_TESTED`, `ACCOUNT_AUTHORIZED` or `CONNECTED_VERIFIED`. Those states are generated by the build's actual probes. The machine-readable companion is [research-index.json](../config/research-index.json).

## Current version policy

Use [runtime-version-plan.json](../config/runtime-version-plan.json) as a **candidate plan, not a lockfile**. T01 resolves one stable compatible environment; T20 proves provider/protocol behavior; T30 freezes exact versions and integrities after integration. Keep the tested set through the demo. A newer tag is not automatically better for an already-working integration, and a package's latest-page cache is not installation proof.

No package keys, source account IDs, credential entitlement, sponsor credits, cloud cost or successful runtime outcome were inferred. New model/harness announcements were filtered for project impact; this kit does not add unrelated APIs, frameworks or features merely because they were announced.

## Primary source register

### S01 — Original user PRD

[Source](../reference/Preflight-PRD.md) · **USER_SOURCE_PRESERVED**

Product/problem, ten tools, real RDS rehearsal, safety boundaries and original source links. Kept byte-for-byte; changes are explicit kit amendments.

### S02 — Canonical HackCulture event page

[Source](https://hackculture.io/hackathons/agents-that-act) · **FETCH_INCOMPLETE**

Repeated canonical-page retrieval did not establish the full body. Do not present it as a fully recovered page. Final invitation/on-site rules remain the authority.

### S03 — Official organizer event page, Portuguese path

[Source](https://www.truefoundry.com/pt/truefoundry-hackathon) · **OFFICIAL_INDEXED_TEXT**

Indexed official English event text supplies provisional agenda, team/repo/disclosure/pitch rules, scoring weights and an explicit statement that Gateway is optional. Direct page fetch was inconsistent; cache may differ from final instructions.

### S04 — Official organizer event page, Spanish path

[Source](https://www.truefoundry.com/es/truefoundry-hackathon) · **OFFICIAL_INDEXED_TEXT**

Additional official event description. Localized paths/cached revisions can differ. Do not convert general emphasis on Gateway into an invented mandatory rule.

### S05 — Codex release changelog

[Source](https://learn.chatgpt.com/docs/changelog) · **OFFICIAL_INDEXED_CURRENT**

Current indexed entry names CLI 0.157.0 on 25 September, GPT-6 Sol/Luna support and new session ergonomics. An opened copy was stale; the newer dated indexed entry and tagged source govern the researched baseline.

### S06 — Codex 0.157 configuration schema

[Source](https://github.com/openai/codex/blob/rust-v0.157.0/codex-rs/core/config.schema.json) · **PINNED_SOURCE_READ**

Agents schema confirms enabled, max_concurrent_threads_per_session, default_subagent_model and default_subagent_reasoning_effort. max_depth is backend-specific; max_spawn_depth is not defined. Installed parsing still needs T01.

### S07 — Codex custom subagents

[Source](https://learn.chatgpt.com/docs/agent-configuration/subagents) · **OFFICIAL_DOC_READ**

Standalone role files require name, description and developer_instructions. Role model/effort can override spawn values; child-count limit excludes the primary. Older model examples on the page do not supersede current model releases.

### S08 — Codex repository instructions

[Source](https://learn.chatgpt.com/docs/agent-configuration/agents-md) · **BASELINE_DOCUMENTATION**

Repository instruction routing/scoping reference inherited from the first audit. V2 uses a small router; effective loaded instructions are checked in the actual harness.

### S09 — Codex skills

[Source](https://developers.openai.com/codex/skills) · **OFFICIAL_DOC_READ**

Repository .agents/skills discovery and SKILL.md guidance. Four narrow routers are the kit design, not a claim more skills improve performance.

### S10 — Goals in Codex

[Source](https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex) · **OFFICIAL_DOC_READ**

Documented persistent thread Goal and interactive management commands. Thread scope/budget/pause behavior means the repository ledger remains necessary.

### S11 — Rethinking skills and prompts for Astra

[Source](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra) · **OFFICIAL_INDEXED_CURRENT**

11 September article favors small task-relevant skill descriptions, progressive disclosure and explicit completion instead of excessive universal instructions. Detailed product contracts remain on-demand.

### S12 — Codex hooks

[Source](https://learn.chatgpt.com/docs/hooks) · **OFFICIAL_DOC_READ**

Lifecycle configuration requires review/trust and supported command behavior. Hooks are not a security boundary. This kit ships no active hook that calls nonexistent application scripts.

### S13 — Codex worktrees

[Source](https://learn.chatgpt.com/docs/environments/git-worktrees) · **BASELINE_DOCUMENTATION**

Reference for separate checkouts. T01 verifies native feature availability; ordinary Git worktrees and explicit cwd verification provide the planned fallback.

### S14 — OpenAI model catalog

[Source](https://developers.openai.com/api/docs/models) · **OFFICIAL_INDEXED_CURRENT**

Current catalog names Astra for difficult reasoning/coding, Sol for balanced work and Luna for focused efficiency. The exact task assignments are our recommendation, not a comparative benchmark.

### S15 — GPT-6 Astra model

[Source](https://developers.openai.com/api/docs/models/gpt-6-astra) · **OFFICIAL_INDEXED_CURRENT**

Current model identity and effort options verified through indexed official content after a direct-fetch error. Availability in this operator account is not established.

### S16 — GPT-6 Sol model

[Source](https://developers.openai.com/api/docs/models/gpt-6-sol) · **OFFICIAL_INDEXED_CURRENT**

Sol supports reasoning/tool work via Responses; Chat Completions functions require none. This is an API constraint, not a Codex setting or Gateway entitlement.

### S17 — GPT-6 Luna model

[Source](https://developers.openai.com/api/docs/models/gpt-6-luna) · **OFFICIAL_INDEXED_CURRENT**

Focused-task model and current tool/effort constraints. Optional clerical assignment only; not an additional product dependency.

### S18 — OpenAI API changelog

[Source](https://developers.openai.com/api/docs/changelog) · **OFFICIAL_INDEXED_CURRENT**

22 September entry verifies Sol/Luna release. New API/harness features were considered, but the event product remains TrueForge rather than being replaced by a managed coding harness.

### S19 — OpenAI deployment checklist

[Source](https://developers.openai.com/api/docs/guides/deployment-checklist) · **OFFICIAL_INDEXED_CURRENT**

Critical current constraints: Astra tools require Responses; Sol/Luna Chat Completions tools require none; unsupported sampling/log-probability parameters must be removed. Representative project probes precede migration.

### S20 — OpenAI code-generation guidance

[Source](https://developers.openai.com/api/docs/guides/code-generation) · **OFFICIAL_INDEXED_CURRENT**

Current general-purpose coding guidance supports Astra for complex end-to-end work. Does not prove every task needs the highest effort or every account has access.

### S21 — TrueForge package metadata at PRD commit

[Source](https://github.com/truefoundry/trueforge/blob/de68a1643f4aafbefc80c6cbfe4bfda361459b29/packages/trueforge/package.json) · **PINNED_SOURCE_READ**

Version 0.2.1 and Node >=22.14 source metadata verified. Package installation/integrity and all runtime integrations remain untested in this kit.

### S22 — TrueForge README at PRD commit

[Source](https://github.com/truefoundry/trueforge/blob/de68a1643f4aafbefc80c6cbfe4bfda361459b29/README.md) · **PINNED_SOURCE_READ**

Harness/tool/sandbox/UI separation and private local-mode warning. Preserve the real runtime, not a separate invented dashboard.

### S23 — TrueForge model configuration at PRD commit

[Source](https://github.com/truefoundry/trueforge/blob/de68a1643f4aafbefc80c6cbfe4bfda361459b29/docs/models.mdx) · **PINNED_SOURCE_READ**

Custom endpoints and stored model resources; automatic per-turn model selection is described as planned. Do not advertise implicit runtime model routing.

### S24 — TrueForge saved-agent and approval reference

[Source](https://github.com/truefoundry/trueforge/blob/de68a1643f4aafbefc80c6cbfe4bfda361459b29/docs/create-agent/overview.mdx) · **PRD_AND_BASELINE_REFERENCE**

Literal approval configuration is part of the original verified design. Final effective config and Code Mode gating must be observed in the installed package.

### S25 — TrueForge sandbox reference

[Source](https://github.com/truefoundry/trueforge/blob/de68a1643f4aafbefc80c6cbfe4bfda361459b29/docs/sandbox.mdx) · **PRD_AND_BASELINE_REFERENCE**

Daytona setup and sandbox/snapshot permissions. Provider quota/scopes and a real execution ID are T20 checks; do not assume the local model process is Daytona.

### S26 — TrueForge Code Mode reference

[Source](https://github.com/truefoundry/trueforge/blob/de68a1643f4aafbefc80c6cbfe4bfda361459b29/docs/key-features/code-mode.mdx) · **PRD_AND_BASELINE_REFERENCE**

Generated code calls tools through the harness bridge. Do not copy Python-client return wrappers into Code Mode without observing its actual shape.

### S27 — TrueForge MCP setup reference

[Source](https://github.com/truefoundry/trueforge/blob/de68a1643f4aafbefc80c6cbfe4bfda361459b29/docs/mcp-servers.mdx) · **PRD_AND_BASELINE_REFERENCE**

Private connector setup reference. Its discovery/schema and streamable transport still need a live compatibility probe.

### S28 — TrueForge model adapter implementation

[Source](https://github.com/truefoundry/trueforge/blob/de68a1643f4aafbefc80c6cbfe4bfda361459b29/packages/trueforge-core/src/core/llm/VercelAILLM.ts) · **PINNED_SOURCE_READ**

The openai adapter calls client.responses; custom/truefoundry route to an OpenAI-compatible model adapter. Provider base URL/schema details must match the installed build and authorized Gateway.

### S29 — Gateway quickstart

[Source](https://www.truefoundry.com/docs/ai-gateway/quick-start) · **OFFICIAL_DOC_READ**

Copy real Playground base URL, key scope and model ID. Do not append guessed API prefixes or confuse saved TrueForge resource names with upstream provider IDs.

### S30 — Gateway Chat Completions

[Source](https://www.truefoundry.com/docs/ai-gateway/chat-completions-overview) · **OFFICIAL_DOC_READ**

Gateway provider-account/model identifiers and chat request shape. Compatible chat availability alone does not establish Responses or reasoning-tool support for a model.

### S31 — OpenAI latest-model migration guidance

[Source](https://developers.openai.com/api/docs/guides/latest-model) · **OFFICIAL_INDEXED_CURRENT**

Endpoint/effort migration and unsupported request fields. Use with the pinned adapter and actual Gateway test, not model-string replacement alone.

### S32 — Gateway request logging

[Source](https://www.truefoundry.com/docs/ai-gateway/request-logging) · **OFFICIAL_DOC_READ**

Review request/response logging and trace exposure; collect only actual permitted metadata. Logging is not permission to transmit DB rows or secrets.

### S33 — September 23 Gateway catalog announcement

[Source](https://www.truefoundry.com/de/blog/claude-opus-5-5-gpt-6-sol-and-gpt-6-luna-are-now-live-on-truefoundry-ai-gateway) · **OFFICIAL_INDEXED_CURRENT**

Publisher reports Sol/Luna catalog availability. This does not prove team access, the selected API route or the behavior of a cached/older provider configuration.

### S34 — Python MCP v2.2.0 package source

[Source](https://github.com/modelcontextprotocol/python-sdk/blob/v2.2.0/pyproject.toml) · **PINNED_SOURCE_READ**

Tag and Python requirement verified. A cached PyPI latest page showed an older snapshot, so fresh registry resolution/install must not be claimed complete.

### S35 — MCP Python v2 migration guide

[Source](https://py.sdk.modelcontextprotocol.io/migration/) · **OFFICIAL_DOC_READ**

Major API/lifecycle/transport/result changes and telemetry behavior need deliberate handling. Wire compatibility is tested against the actual TrueForge client, not inferred from matching SDK majors.

### S36 — pglast 8.4 metadata

[Source](https://pypi.org/project/pglast/8.4/) · **PACKAGE_PAGE_READ**

Version-specific metadata and GPL-3.0-or-later inventory note. No source upgrade or distribution-license decision is made by this kit.

### S37 — pglast maintainer version mapping

[Source](https://pglast.readthedocs.io/en/latest/changes.html) · **BASELINE_DOCUMENTATION**

The inherited pairing is v8/PostgreSQL18 and v7/PostgreSQL17. Revalidate the exact available parser distribution and actual engine at T01.

### S38 — AWS RDS snapshot restore

[Source](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_RestoreFromSnapshot.html) · **OFFICIAL_DOC_READ**

New instance restore, lazy loading and current storage restrictions. Actual source/clone identity, storage, network and encryption are independently checked before readiness.

### S39 — AWS RDS snapshot creation

[Source](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_CreateSnapshot.html) · **PRD_AND_BASELINE_REFERENCE**

Snapshot is an instance-level AWS operation, not a single-database export. Observe the real asynchronous job and provenance.

### S40 — RDS PostgreSQL SSL

[Source](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/PostgreSQL.Concepts.General.SSL.html) · **OFFICIAL_DOC_READ**

Encryption and endpoint/CA verification must be treated separately. Negative CA/hostname tests are our deployment acceptance requirement.

### S41 — EC2 IAM roles

[Source](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/iam-roles-for-amazon-ec2.html) · **PRD_AND_BASELINE_REFERENCE**

Instance-role runtime credentials rather than static AWS secrets. Account-specific policies and grants remain operator-authorized implementation work.

### S42 — Boto3 snapshot restore API

[Source](https://docs.aws.amazon.com/boto3/latest/reference/services/rds/client/restore_db_instance_from_db_snapshot.html) · **BASELINE_DOCUMENTATION**

Target request fields must be verified against the installed compatible boto3/botocore pair. Do not assume IAM/KMS/engine/class choices are universally valid.

### S43 — PostgreSQL explicit locking

[Source](https://www.postgresql.org/docs/current/explicit-locking.html) · **BASELINE_DOCUMENTATION**

Locks motivate the conservative static-source recheck/write design. That design is not a claim of an online migration strategy for live production traffic.

### S44 — PostgreSQL 18 ALTER TABLE

[Source](https://www.postgresql.org/docs/18/sql-altertable.html) · **BASELINE_DOCUMENTATION**

Constraint/locking reference. Exact allowed subcommands and nested-expression policy are defined by this product, not delegated to the model.

### S45 — Psycopg transactions

[Source](https://www.psycopg.org/psycopg3/docs/basic/transactions.html) · **OFFICIAL_DOC_READ**

Explicit transaction behavior reference. The retrieved docs advertised a development version; no development version is asserted as the installed stable release.

### S46 — Psycopg multiple statements

[Source](https://www.psycopg.org/psycopg3/docs/basic/from_pg2.html#multiple-results-returned-from-multiple-statements) · **PRD_AND_BASELINE_REFERENCE**

Exact-script execution needs actual multi-result/error/rollback tests. Do not assume a later-statement error is handled because the first result succeeded.

### S47 — RDS recovery reference

[Source](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_PIT.html) · **PRD_AND_BASELINE_REFERENCE**

A recovery restore is not an automatic SQL undo. Retention and unknown-outcome rules remain explicit; no live recovery drill was performed by this kit.


### S48 — GPT-5.6 Sol model reference

[Source](https://developers.openai.com/api/docs/models/gpt-5.6-sol) · **OFFICIAL_DOC_READ** · V3, 25 September 2026

Exact model family/ID and tool interfaces support the requested Sol alternative. API prices are not converted into a promised Codex allowance saving; account access/effective High still require T01.

### S49 — ChatGPT Work and Codex allowance

[Source](https://help.openai.com/en/articles/20001275-chatgpt-work-and-codex) · **OFFICIAL_DOC_READ** · V3, 25 September 2026

Astra can consume Work/Codex allowance faster; consumption depends on workload/settings and sign-in/billing route. Supports bounded expert use, not a universal savings percentage.

### S50 — PostgreSQL 18 transaction isolation

[Source](https://www.postgresql.org/docs/18/transaction-iso.html) · **OFFICIAL_DOC_READ** · V3, 25 September 2026

Supports consistent baseline captures and the distinct locked READ COMMITTED source apply procedure. V3 coverage and offline-verifier logic are our design, not a PostgreSQL feature claim.

### S51 — Atlas migration tests

[Source](https://atlasgo.io/testing/migrate) · **OFFICIAL_INDEXED_CURRENT** · V3, 25 September 2026

Documents executing migrations and assertions on a development database. Establishes that migration testing already exists; not an exhaustive competitive comparison.

### S52 — Flyway dry-run tutorial

[Source](https://documentation.red-gate.com/flyway/reference/tutorials/tutorial-dry-runs) · **OFFICIAL_DOC_READ** · V3, 25 September 2026

Official tutorial updated 24 September 2026 describes read-only assessment and generated SQL for review. Distinguish SQL preview from Preflight's proposed executed clone evidence without claiming all other Flyway capabilities absent.

### S53 — OpenAI reasoning guidance

[Source](https://developers.openai.com/api/docs/guides/reasoning) · **OFFICIAL_INDEXED_CURRENT** · V3, 25 September 2026

Reasoning/effort and service choices have model-specific support. V3 defaults to High and avoids automatic premium escalation; test actual provider requests.

### S54 — PostgreSQL 18 row security

[Source](https://www.postgresql.org/docs/18/ddl-rowsecurity.html) · **OFFICIAL_INDEXED_CURRENT** · V3, 25 September 2026

Role-dependent row visibility reinforces the existing fail-closed unsupported-RLS policy. No new claim of general RLS-safe migration support.

## Open checks and deterministic responses

At T00 confirm final event coding start/submission/rules. At T01 confirm actual stable distributions, model access, native capabilities and effective permissions. At T20 confirm Gateway/Responses/tool streaming, actual TrueForge MCP interoperability and Daytona code execution. At T22/T24 prove the actual RDS clone and human-controlled apply. At T30/T34 freeze/check reproducibility, notices, source state and resources.

If a source is unavailable, record the exact missing fact and use an authorized primary alternative; do not invent API fields or say an entire page was read. If an external capability is missing, continue independent work and mark its connected gate unverified. The reviewed docs describe possibilities; only observed artifacts justify the final demo claims.
