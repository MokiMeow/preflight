# Preflight

Preflight rehearses an exact, narrowly supported PostgreSQL migration on a separate snapshot-restored
RDS clone, verifies deterministic schema and protected-data evidence, and pauses for an engineer
before the same bytes can touch the allowlisted synthetic demo source.

This repository is an implementation in progress. The preserved source brief is
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

The integration lane was locally verified on commit ancestry beginning at
`5790a6a4f2cbeb2ef86c6918b08abdcae8568240` with:

- Python `3.12.10`, MCP `2.2.0`;
- Node `v24.11.1`, npm `11.6.2`;
- `@truefoundry/trueforge@0.2.1`, registry integrity pinned in `integration/package-lock.json`;
- TrueForge-bundled JavaScript MCP client `1.30.1` calling the Python MCP status tool over
  loopback Streamable HTTP with structured content;
- installed TrueForge OpenAPI fields for saved agents, model parameters, MCP selectors, sandbox,
  and dynamic-subagent settings;
- report/offline/config/package/MCP interoperability tests (`14 passed` in the scoped run).

The package, schema, and local MCP results are `LOCAL_VERIFIED`. Gateway/OpenAI Responses,
TrueForge model streaming, Daytona execution, private deployment, real Preflight connector traces,
and approval behavior are `BLOCKED_EXTERNAL` until credentials, quota, host, and a human operator
are available. No model response, Daytona run, AWS action, source write, cleanup, or approval was
simulated or claimed.

## Local development

Create a Python 3.12 environment and install the project:

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e .
```

On Linux/macOS, use `.venv/bin/python`. Install the exact integration package separately:

```bash
cd integration
npm ci --ignore-scripts --no-audit --no-fund
cd ..
```

Run the independent checks:

```bash
PYTHONPATH=src python -m pytest tests/unit/test_reports.py tests/trueforge -q
python -m ruff check src/preflight/report.py src/preflight/offline.py \
  scripts/probe_trueforge_config.py scripts/probe_trueforge_mcp_server.py \
  tests/unit/test_reports.py tests/trueforge
node scripts/probe_trueforge_package.mjs
python scripts/probe_trueforge_config.py config/trueforge-agent.example.json --template
```

The verifier module is directly runnable while the lead-owned top-level CLI wiring is integrated:

```bash
PYTHONPATH=src python -m preflight.offline reports/RUN/CANDIDATE.json
PYTHONPATH=src python -m preflight.offline reports/RUN/CANDIDATE.json \
  --expected-report-sha256 DIGEST_FROM_AN_INDEPENDENT_TRACE
```

Exit codes are 0 for an internally consistent historical artifact, 2 for invalid input, 3 for a
digest/anchor mismatch, 4 for unsupported schema or inconsistent requirements/evidence, and 5 for a
declared/recomputed verdict mismatch. Errors contain fixed safe codes.

## Private runtime setup

Follow [`integration/DEPLOYMENT.md`](integration/DEPLOYMENT.md). It records the observed TrueForge
CLI/listener behavior, model/provider schema boundary, locked install, private SSH access, connector
registration, config validation, local MCP probe, and exact connected evidence still required.

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

The synthetic bad and corrected migration fixtures, connected AWS setup, full demonstration commands,
actual evidence paths, team/contribution details, and retention decision must be added from observed
lead/cloud/integration results. Missing connected inputs block those claims; they do not weaken any
acceptance gate.

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
