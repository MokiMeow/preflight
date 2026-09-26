---
name: preflight-db
description: Implement or review Preflight SQL policy, transactions, source guards or row/schema evidence.
---

# preflight-db

Read the task-relevant sections of [02](../../../docs/02_CONTRACTS_AND_SAFETY.md) · [06](../../../docs/06_TEST_AND_EVIDENCE.md). Paths are relative to this skill file.

Use the assigned task card, strict contract 1.1 and database-major/parser pairing. Prove the invariant with a failing regression test before a sensitive fix. Compare exact bytes, full pre-existing source fingerprints and intended new-schema checks; keep raw row maps private. Unknown commit is a separate state, never retry permission. The lead owns shared types and verdict/service composition. Return code and real disposable-PostgreSQL evidence; mocks are not database proof.

Do not load the other skills or the whole PRD unless the assignment crosses their boundary. Use `docs/09_BUILD_STATUS.md` only for current handoff context.

Use Sol High. Resolve per-written-column preservation/intended-value coverage; counts or non-null checks alone cannot certify an unasserted UPDATE. Keep one consistent read-only snapshot per baseline capture. Read docs 02 section 11 when implementing these checks.
