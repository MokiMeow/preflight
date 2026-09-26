---
name: preflight-verification
description: Review or verify Preflight acceptance, source-apply safety, privacy, demo claims or final evidence.
---

# preflight-verification

Read the task-relevant sections of [06](../../../docs/06_TEST_AND_EVIDENCE.md) · [07](../../../docs/07_DEMO_AND_SUBMISSION.md). Paths are relative to this skill file.

Read the exact revision under review and identify which evidence exists. Attack stale hashes, data changes, races, unknown outcomes, prompt injection and tool approval bypasses. A read-only reviewer returns reproducible findings; the lead runs safe tests. Never click human gates, suppress failures or relabel mocks as RDS. Reconcile the task ledger with actual final evidence and retained resource state. Return critical/high findings first, then explicit not-tested limits.

Do not load the other skills or the whole PRD unless the assignment crosses their boundary. Use `docs/09_BUILD_STATUS.md` only for current handoff context.

Routine review is Sol High. Astra/high is read-only and requires an unused A1/A2 ticket from config/model-policy.json. Review the exact safety diff, not a routine whole-repo rescan. Verify the offline trust-anchor labels and column-level coverage; T27 must be accepted before T24 live apply.
