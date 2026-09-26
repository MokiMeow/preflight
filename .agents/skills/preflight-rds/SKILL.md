---
name: preflight-rds
description: Implement or review Preflight RDS snapshot, private restore, IAM, TLS, lifecycle or cleanup.
---

# preflight-rds

Read the task-relevant sections of [04](../../../docs/04_CLOUD_RUNBOOK.md) · [02](../../../docs/02_CONTRACTS_AND_SAFETY.md). Paths are relative to this skill file.

Start with identity and explicit resource authorization. Plan before live mutations, use exact persisted IDs and tags, and enforce caps. Confirm engine/parser pairing, network origin, hostname-validating TLS and retained recovery resources. Availability does not imply warmed storage. Never import cloud credentials into model prompts or Daytona. Return request construction tests and separately labeled live observations; do not hide provider denial by broadening IAM.

Do not load the other skills or the whole PRD unless the assignment crosses their boundary. Use `docs/09_BUILD_STATUS.md` only for current handoff context.

Use Sol High. Bound read-only cloud polling and keep one persisted job/run identity. Pending is not failed; never create another restore or replay SQL to save a model turn.
