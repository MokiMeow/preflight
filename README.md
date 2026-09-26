# Preflight

Preflight rehearses an exact, narrowly supported PostgreSQL migration on a separate snapshot-restored
RDS clone, verifies deterministic schema and protected-data evidence, and pauses for an engineer
before the same bytes can touch the allowlisted synthetic demo source.

The preserved source brief is
`reference/Preflight-PRD.md`; numbered research-backed amendments are in
`docs/00_PRODUCT_AND_DECISIONS.md`. The actual event URL and final submission fields have not been
provided, so this README does not invent them.

## Safety and product boundary

Preflight has one native surface: the bundled TrueForge chat, tool trace, Markdown report, Code Mode,
and approval panel. Daytona is an orchestration sandbox; it is not the database clone. The private
MCP service owns credentials, allowlists, SQL policy, exact bytes, checks, state, report hashes, and
write guards.

There are ten business tools. `apply_to_demo_source` and `cleanup_run` are the two literal human
approval gates. They remain separate, and a coding agent must never click either gate for the
operator. A chat statement cannot approve a write. A model explanation cannot change a verdict.

SQL comments, database labels, external pages, and tool results are untrusted data. Raw rows,
customer values, database/AWS credentials, connector tokens, DSNs, private endpoints, and
credential-bearing traces must not enter prompts, logs, reports, Daytona, or Git.

## Architecture

```text
Engineer → private TrueForge UI → Preflight MCP service → owned synthetic RDS source (read guards)
                                  │                    └→ snapshot → separate private clone
                                  ├→ exact SQL / deterministic checks / immutable report
                                  └→ literal human gate → guarded source transaction

TrueForge Code Mode → Daytona sandbox → typed MCP bridge only (no DB or AWS credentials)
```

The report envelope is `{payload, report_sha256}`. The SHA-256 covers canonical payload bytes only.
Readable Markdown is a deterministic escaped view. Apply and cleanup receipts are separate artifacts;
they never rewrite the historical rehearsal report.

Offline verification checks strict JSON, duplicate keys, schema versions, the payload digest,
manifest/result completeness, complete aggregate evidence for PASS, and the deterministic verdict.
Without an independently retained expected digest, a valid result is
`SELF_CONSISTENT_UNANCHORED`; it is not authenticity, current source eligibility, or production
safety.

## Tested versions and local results

The implementation has been locally verified with:

- Python `3.12.10`, MCP `2.2.0`;
- Node `v24.11.1`, npm `11.6.2`;
- `@truefoundry/trueforge@0.2.1`, registry integrity pinned in `integration/package-lock.json`;
- TrueForge-bundled JavaScript MCP client `1.30.1` calling the Python MCP status tool over
  loopback Streamable HTTP with structured content;
- installed TrueForge OpenAPI fields for saved agents, model parameters, MCP selectors, sandbox,
  and dynamic-subagent settings;
- deterministic report/offline verification, strict MCP schemas, storage/restart behavior, SQL
  policy, and actual disposable PostgreSQL tests;
- installed TrueForge configuration/package probes and cross-language MCP interoperability tests.

The package, schema, and local MCP results are `LOCAL_VERIFIED`. Gateway/OpenAI Responses,
TrueForge model streaming, Daytona execution, private deployment, real Preflight connector traces,
and approval behavior are `BLOCKED_EXTERNAL` until credentials, quota, host, and a human operator
are available. No model response, Daytona run, AWS action, source write, cleanup, or approval was
simulated or claimed.

## Local development

Install the exact Python environment from `uv.lock`:

```bash
uv sync --locked
```

Install the exact integration package separately without lifecycle scripts:

```bash
cd integration
npm ci --ignore-scripts --no-audit --no-fund
cd ..
```

Create the ignored runtime settings file. The example is nonsecret and fail-closed; copying it does
not authorize cloud resources or source apply:

```powershell
Copy-Item config/settings.example.json config/settings.local.json
uv run preflight doctor --json
```

Fill `settings.local.json` only from the authorized operator/cloud handoff. It is ignored by Git.
Keep actual database/AWS credentials in the named Secrets Manager entries, not this file. The doctor
reports configuration and presence of references; it does not claim connected AWS, TLS, Gateway,
Daytona, or approval proof.

Prepare exact candidate bytes locally:

```powershell
New-Item -ItemType Directory -Force var | Out-Null
uv run preflight candidate intake --sql fixtures/good.sql --contract config/contract.example.json --output var/good-candidate.json --operator-id team-operator
```

Start the loopback MCP service after the settings are reviewed:

```bash
uv run preflight serve
```

Run local verification:

```bash
uv run pytest tests/unit tests/mcp tests/trueforge -q
uv run pytest tests/cloud -q
uv run ruff check src scripts tests infra
uv run mypy src/preflight
node scripts/probe_trueforge_package.mjs
uv run python scripts/probe_trueforge_config.py config/trueforge-agent.example.json --template
```

Bootstrap the disposable PostgreSQL 18 TLS fixture with actual PostgreSQL binaries, then run the
database suites. This creates a new loopback cluster only and refuses to replace an existing one:

```powershell
uv run python fixtures/local_pg.py --bin C:/path/to/pgsql/bin --port 55438
$env:PREFLIGHT_TEST_PG_PORT='55438'
$env:PREFLIGHT_TEST_PG_CA=(Join-Path (Get-Location) 'var/local-postgres/data/server.crt')
uv run preflight verify local
```

`preflight verify local` runs every test folder, including the PostgreSQL, cloud, MCP, and TrueForge
suites. The TrueForge suite fails explicitly when its locked npm dependencies have not been
installed; it does not turn a missing SDK into a skipped acceptance check.

Stop it explicitly with
`C:/path/to/pgsql/bin/pg_ctl -D var/local-postgres/data stop`. The fixture is
`local_postgres_test`, never AWS evidence.

Export, independently verify, and list recorded resources:

```powershell
uv run preflight evidence export RUN_UUID --output var/report.json
uv run preflight evidence verify var/report.json
uv run preflight evidence verify var/report.json --expected-report-sha256 DIGEST_FROM_AN_INDEPENDENT_TRACE
uv run preflight resources list
```

The verifier exits 0 for an internally consistent historical artifact, 2 for invalid input, 3 for
a digest/anchor mismatch, 4 for unsupported schema or inconsistent requirements/evidence, and 5 for
a declared/recomputed verdict mismatch. Without the independent digest it reports
`SELF_CONSISTENT_UNANCHORED`.

## Private runtime setup

Follow [`integration/DEPLOYMENT.md`](integration/DEPLOYMENT.md). It records the observed TrueForge
CLI/listener behavior, model/provider schema boundary, locked install, private SSH access, connector
registration, config validation, local MCP probe, and exact connected evidence still required.
Use [`integration/DEMO_RUNBOOK.md`](integration/DEMO_RUNBOOK.md) for the real bad/good rehearsal,
literal denial and separate allow request, unknown-outcome recovery, cleanup, and final handoff.

Do not commit configured agent exports containing credentials, local operator inputs, state databases,
raw logs, screenshots of settings, private keys, or `.env` files. Do not push to a public remote until
the team explicitly authorizes repository visibility.

## Candidate, report, apply, and cleanup flow

1. Register the exact SQL bytes and accepted contract with independently computed hashes.
2. Start one bounded rehearsal for the allowlisted source, then observe the persisted snapshot/restore
   job without replaying it.
3. Capture a clone baseline and a separate read-only source baseline. Require equality.
4. Apply only the stored candidate to the clone in one transaction. Unknown commit outcome blocks
   automatic retry.
5. Validate every mandatory invariant, declared check, and written-column coverage requirement.
6. Seal JSON evidence and render the native Markdown view. A committed migration can still be BLOCK
   or WARN.
7. If and only if the immutable verdict is PASS, show the exact target/hashes/backup and request the
   literal source-apply gate. The service rechecks all guards under locks.
8. Record the source result in a separate receipt. Never translate unknown outcome into rollback.
9. Cleanup requires its own literal human gate and preserves required recovery backups plus all
   reports/receipts.

Actual connected evidence paths, team/contribution details, organizer fields, video links, and the
retention decision must be added from observed results. Missing connected inputs block those claims;
they do not weaken any acceptance gate.

## Dependency and license inventory

[`integration/dependency-inventory.json`](integration/dependency-inventory.json) records the exact
packages installed by the documented Windows `uv`/npm setup, raw declared license metadata, npm
integrity values, and lockfile hashes. Regenerate and compare it with:

```bash
uv run python scripts/generate_dependency_inventory.py
uv run python scripts/generate_dependency_inventory.py --check
```

See [`integration/THIRD_PARTY_NOTICES.md`](integration/THIRD_PARTY_NOTICES.md). In particular,
`pglast 8.4` declares `GPL-3.0-or-later`. The Preflight project license is `UNDECIDED`; no repository
license should be inferred from a dependency or added without the team's decision.

## Limitations

This is a controlled synthetic demonstration, not a general PostgreSQL migration engine or a claim
of zero downtime. The SQL grammar, supported types, scan budgets, object policy, static-source
assumption, private TrueForge trust boundary, and column-level requirements are explicit. A PASS is
historical evidence for the observed clone run. It does not prove current source drift status,
application compatibility, traffic behavior, performance, authenticated human identity, or universal
rollback safety.

## AI assistance disclosure

Planning used ChatGPT with the team's supplied PRD and researched documentation. Implementation and
review use the coding assistants, models, and effort recorded in the build ledger and final evidence
packet. The runtime product uses the separately configured OpenAI Sol model through TrueForge only
after the actual route is verified. The team reviews changes and retains the commands and sanitized
integration evidence that actually ran.
