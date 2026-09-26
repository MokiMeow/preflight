# Evidence-led demonstration checklist

This checklist prepares and records an actual run. A checked box means the named command, trace, or
human action was observed for the recorded commit and run. Do not pre-check connected items from
fixtures, source code, or an earlier unrelated session.

## Before the session

- [ ] Record `git rev-parse HEAD`; require a clean tracked checkout.
- [ ] Run `uv sync --locked` and `npm ci --ignore-scripts --no-audit --no-fund` in `integration/`.
- [ ] Copy `config/settings.example.json` to ignored `config/settings.local.json`; fill only the
  authorized account, region, allowlisted synthetic source, network IDs, budget, certificate, and
  Secrets Manager ARN references. Keep `enable_demo_source_apply` false until the authorized apply
  demonstration.
- [ ] Run `uv run preflight doctor --json`. Record its honest `NOT_RUN`/`NOT_OBSERVED` fields; do
  not turn them into green claims.
- [ ] Run the local suites, including the PostgreSQL 18 fixture commands in the README.
- [ ] Confirm T27 independent boundary review is accepted before any live source apply.
- [ ] Verify the recovery snapshot, source schema, current candidate, run, clone, immutable report
  digest, and separately retained expected report digest.
- [ ] Verify the saved TrueForge agent still has exactly ten enabled tools and two literal approval
  selectors: `apply_to_demo_source` and `cleanup_run`.
- [ ] Verify the actual Sol/high Responses route, Daytona execution, MCP connector, and private SSH
  access. If any is unavailable, mark it `BLOCKED_EXTERNAL` and use only clearly dated prior real
  evidence; do not call a fixture live.

## Candidate preparation

Create the output directory and intake files without connecting to a database:

```powershell
New-Item -ItemType Directory -Force var | Out-Null
uv run preflight candidate intake --sql fixtures/bad.sql --contract config/contract.example.json --output var/bad-candidate.json --operator-id team-operator
uv run preflight candidate intake --sql fixtures/good.sql --contract config/contract.example.json --output var/good-candidate.json --operator-id team-operator
```

- [ ] Retain the emitted migration, canonical contract, and raw contract SHA-256 values.
- [ ] Confirm the generated payloads contain exact base64 SQL bytes and no credentials.
- [ ] Start `uv run preflight serve` on the private host and `npx trueforge --port 8790` from
  `integration/`; use the documented SSH tunnel.

## Rehearsal proof

1. Show the allowlisted source ID, database, exact bad candidate hash, and planned coverage.
2. Register and start one run. Observe the same run through snapshot/restore; do not restart it on a
   poll timeout.
3. Capture the baseline, apply the bad migration to the clone, and show confirmed rollback/BLOCK.
4. Register the corrected candidate. Reuse the clone only if the service's revision guards permit
   it; otherwise start a fresh rehearsal.
5. Apply the corrected bytes to the clone, validate, and show the sealed report. Read expected,
   observed, and missing columns aloud. A successful transaction is not enough for PASS.
6. Export and independently verify the artifact:

   ```powershell
   uv run preflight evidence export RUN_UUID --output var/report.json
   uv run preflight evidence verify var/report.json --expected-report-sha256 EXPECTED_DIGEST_FROM_SEPARATE_TRACE
   uv run preflight resources list
   ```

7. Show `EXPECTED_DIGEST_MATCH`, historical verdict, backend label, and
   `current_apply_eligibility: NOT_EVALUATED`. Do not call this authenticated human approval or a
   current source guard.

## Literal denial, then a separate allow request

- [ ] Keep the source-apply feature flag and service guards visible.
- [ ] Ask TrueForge to invoke `apply_to_demo_source` for the exact source, candidate, migration hash,
  and report hash. Confirm the UI pauses on that literal tool.
- [ ] The human operator clicks **Deny**. The coding agent does not click either choice.
- [ ] Confirm there is no backend apply call/attempt for the denied request. Call the read-only
  `get_source_status` and show that the source remains unchanged.
- [ ] Do not immediately reprompt. When the operator explicitly requests the second demonstration,
  create a new source-apply request with the same reviewed identities.
- [ ] The human operator clicks **Allow**. The service must still recheck current source identity,
  report/candidate hashes, backup, tags, metadata policy, drift, lock acquisition, and prior-attempt
  state. A refused server guard stays refused after UI approval.
- [ ] Show the separate apply receipt and read-only post-commit confirmation. Never rewrite the
  rehearsal report to APPLIED.
- [ ] Replay the source apply request and show deterministic refusal without executing SQL again.

## Unknown outcome and recovery proof

Run the real local fault tests before the demo:

```powershell
uv run pytest tests/postgres/test_database.py::test_commit_response_loss_is_unknown_not_rollback tests/postgres/test_database.py::test_connection_loss_before_commit_is_unknown tests/unit/test_storage.py::test_restart_unknown_and_never_replay -q
```

- [ ] Explain that a lost commit acknowledgement is `APPLY_OUTCOME_UNKNOWN`, not rollback.
- [ ] Demonstrate persisted intent/restart reconciliation and replay refusal using the test trace or
  an authorized disposable scenario. Never inject a connection fault into the live source merely
  for presentation.
- [ ] Perform only read-only investigation until a human resolves the outcome.
- [ ] Block automated cleanup while the source outcome is unknown.

## Cleanup and closeout

- [ ] Show exact selected clone/snapshot IDs and recovery-retention consequence.
- [ ] Request `cleanup_run`; the human makes this second literal approval decision.
- [ ] Preserve required recovery backup, reports, receipts, and the separately retained report
  digest. Observe deletion/retention state instead of announcing completion early.
- [ ] Record `uv run preflight resources list`, current source schema, final run phase, retained
  resources, cost owner, and the next safe action.
- [ ] Inspect the evidence packet for secrets and raw rows before sharing. Do not publish the repo,
  video, or community post without explicit team authorization.
