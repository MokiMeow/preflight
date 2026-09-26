# Three-minute Preflight walkthrough

This is the recording script for the current evidence. It must be updated with exact run, resource, candidate and report IDs only after those values are observed. Never fill a missing beat with a fixture, an old local report or a narrated claim. The operator performs any literal approval action; the coding agent does not click `apply_to_demo_source` or `cleanup_run`.

## Before recording

Open the saved `preflight` TrueForge agent, the current run status, the sanitized evidence directory and a terminal with the offline verifier ready. Confirm the deployed commit, source ID, source schema, whether a clone and snapshot actually exist, and whether source apply has occurred. Hide credentials, endpoints containing tokens, raw rows, private addresses and provider exports. Keep the exact full hashes available, even if the narration uses short prefixes.

Current proof that may be stated now:

- The native saved agent and approved Gateway route are real.
- A model-generated Python/MCP step ran inside the patched TrueForge local Linux sandbox after correcting an initial bare-Python shell mistake. The successful shell execution observed 1,000 rows and three columns, but the referenced business run was `ERROR` with `cleanup_state=NOT_REQUESTED`; this is not a successful rehearsal.
- The connected sandbox canary verified the bounded filesystem, process/environment, network, per-session socket, launcher-environment and timeout checks recorded in the sanitized receipt.
- The frozen local suite passed 636 tests with zero failures, errors or skips; local tests are not RDS execution evidence.
- At the time this script was written, no live run-owned snapshot/clone, bad-to-good RDS result, source SQL apply, human denial/allowance or cleanup decision was available for the recording.

## Timed script

### 0:00–0:25 — The problem and boundary

**Show:** the TrueForge saved agent and the exact candidate-intake screen or artifact hash, without exposing SQL comments as instructions.

**Say:** “A migration can execute and still change the wrong data. Preflight rehearses exact SQL bytes against an isolated copy, measures schema and protected-value changes, and stops for an engineer before it can touch the owned synthetic source.”

Add: “This is evidence for this source and snapshot, not a guarantee of production safety or zero downtime.”

### 0:25–0:55 — A real agent and real sandbox

**Show:** the sanitized saved-agent session/turn and Code Mode execution receipt, then the local-sandbox verification receipt.

**Say:** “This is the saved product agent using the real model route, private Preflight MCP service and TrueForge’s local Linux sandbox. The first attempt incorrectly sent Python directly to a shell and exited 2. The model corrected it with an explicit Python script; the shell exited 0. We still treat the business result separately: that trace found 1,000 rows and three columns, but its run was ERROR and cleanup was not requested. A zero shell exit is not a PASS.”

Point to the canary summary: own-session socket allowed, foreign socket denied, host bytes/metadata unchanged, private/metadata network denied, launcher injection refused and timed-out child absent. Do not claim that these bounded checks prove universal containment.

### 0:55–1:25 — Exact candidate and deterministic evidence

**Show:** the actual registered candidate hash and current `get_run`/`get_source_status` envelopes. Read only `data.phase`, `data.cleanup_state`, and `data.evidence.tables[].row_count/schema_summary` after `ok=true`.

**Say:** “The model explains the result, but deterministic service checks decide it. Exact SQL bytes, the contract, baseline, primary keys, protected values, schema and coverage must all agree. Missing fields are a schema mismatch, never an excuse to print N/A or infer success.”

If the live RDS run is still unavailable, say exactly: “The live snapshot/clone and RDS migration outcomes are not available yet, so I am not showing a PASS.” Then show only the current persisted state and move to the limitation beat below.

### 1:25–2:05 — Live RDS result, only if observed

**When real connected evidence exists, show:** source ID, run-owned snapshot and distinct private clone IDs, actual restore state, bad candidate hash and BLOCK report, corrected candidate hash and PASS-awaiting-approval report. Show the evidence table with 1,000 rows retained, unchanged primary keys/protected hashes, the new column schema and intended values. State whether the restore finished before recording.

**Say:** “The bad migration failed on the populated clone and rolled back; the source remained unchanged. The corrected candidate is a new exact artifact. It passed the complete declared checks on this restored clone and is awaiting a human decision.”

**If any part is unavailable:** keep this section visibly labeled **NOT RUN** or **PENDING** and say which exact state is known. Do not substitute the 636-test local gate, an old report or the earlier ERROR agent turn.

### 2:05–2:35 — Human control

**Show:** the exact eligible candidate/report target and the TrueForge approval panel only if it is genuinely present.

**Say:** “A PASS is historical rehearsal evidence, not permission. Source apply is a separate literal human gate, and the service still rechecks exact hashes, current source drift and eligibility.”

For a denial recording, the designated engineer selects **Deny**, then show the source unchanged. For an allowed recording, T27 must already be accepted and the designated engineer explicitly selects **Allow** for the exact target; then show the separate receipt and read-only source check. Do not combine denial and allowance by silently resetting the source. If neither action has happened, say: “The human gate has not been exercised; source apply remains false.”

Cleanup is a second literal gate. Do not click it during this beat or imply that absent resources equal approved cleanup.

### 2:35–3:00 — Integrity, limitations and handoff

**Show:** the sealed report hash and offline verifier result when a genuine report exists. If there is no connected sealed report, show the verifier only as clearly labeled local capability evidence.

**Say:** “The sealed artifact records what was observed, and an independently retained expected digest detects replacement. It does not prove current source eligibility. Unknown commit outcomes are never retried automatically. Resource retention and cleanup remain explicit operator decisions.”

Close with the exact current state: run phase, source applied true/false, cleanup state, retained snapshot/clone IDs or `NONE`, and the next safe action. If the live RDS flow is incomplete, close with: “The native agent and sandbox are connected; the live RDS outcome and human gates remain unavailable, so this walkthrough stops here rather than inventing the result.”

## Recording acceptance checklist

- The displayed commit and connected evidence hashes match the final packet.
- Every AWS/model/sandbox/database claim names its backend and actual observation.
- The bad and corrected candidates have distinct exact hashes.
- A PASS is shown only with a complete connected requirement manifest and evidence.
- The first exit-2 sandbox attempt and corrected exit-0 attempt are described honestly if that trace is used.
- Deny, Allow and cleanup appear only when performed by the human operator and recorded as separate actions.
- No credentials, raw rows, private connection strings, hidden error details or unreviewed provider logs are visible.
- Any unavailable snapshot, clone, RDS outcome, apply receipt, replay refusal or cleanup receipt is labeled `NOT_RUN`, `PENDING` or `UNAVAILABLE`.
- The final sentence states the actual source-apply and cleanup state.
