# PREFLIGHT — REHEARSAL BLOCK

> Historical sealed rehearsal evidence. Current source eligibility is not evaluated here.

## Target and provenance

- Evidence backend: `local_postgres_test`
- Run: `9d9888e8-c244-4755-abf5-34b75609e41a`
- Candidate: `bcf582dc-c2ff-4aca-9c91-7f3775debe7d`
- Operator label: `test-operator`
- Created: `2026-09-26T06:27:12.429571Z`
- Source instance: `local-source`
- Snapshot: `local-snapshot`
- Clone instance: `local-clone`
- PostgreSQL major: `18`

## Artifact identity

- Migration SHA-256: `10101d7c639d383807f6fbe855b63bfa15b6a7f603ca44b85d9f44eaa7349c64`
- Contract SHA-256: `f4fa48668e17afa31ee04ced68c898c0428f437dc7ed8f9a387738ece62ca548`
- Report SHA-256: `687a8eabe84ff2b5c74d8a8e2bb131c055c715feaa3f1572fc1a948ea753d2f4`
- Report schema / algorithm / manifest: `1.1` / `preflight-json-1` / `1`

## Aggregate evidence

| Table | Rows before | Rows after | Schema before | Schema after | Preserved before | Preserved after | Full before | Full after |
|---|---:|---:|---|---|---|---|---|---|
| `public.customers` | `1000` | — | `6fa5c4d1b188b1e992863f778c4d795880e73b355cf2cb2c8282aa119f9e7c46` | — | `adb3ddb070ec6968e1ec28143a38f50875bf39d965095af070e0653e83df6c17` | — | `dc1744787b061fc7a96efdcc3b3b9e0dc4b2899a8d09c18bf962e4666a2bd9aa` | — |

## Mandatory checks

| Requirement | Kind | Category | Before | After | Result | Reason |
|---|---|---|---|---|---|---|
| `declared:public.customers:0:row_count_unchanged` | `row_count_unchanged` | `row_count_unchanged` | — | — | `NOT_RUN` | `MIGRATION_FAILED` |
| `declared:public.customers:1:no_nulls` | `no_nulls` | `no_nulls` | — | — | `NOT_RUN` | `MIGRATION_FAILED` |
| `declared:public.customers:2:all_equal` | `all_equal` | `all_equal` | — | — | `NOT_RUN` | `MIGRATION_FAILED` |
| `declared:public.customers:3:column_not_null` | `column_not_null` | `column_not_null` | — | — | `NOT_RUN` | `MIGRATION_FAILED` |
| `invariant:exact_candidate_bytes` | `exact_candidate_bytes` | `exact_candidate_bytes` | — | — | `NOT_RUN` | `MIGRATION_FAILED` |
| `invariant:policy_accepted` | `policy_accepted` | `policy_accepted` | — | — | `NOT_RUN` | `MIGRATION_FAILED` |
| `invariant:clone_provenance` | `clone_provenance` | `clone_provenance` | — | — | `NOT_RUN` | `MIGRATION_FAILED` |
| `invariant:baseline_present` | `baseline_present` | `baseline_present` | — | — | `NOT_RUN` | `MIGRATION_FAILED` |
| `invariant:source_matched_baseline` | `source_matched_baseline` | `source_matched_baseline` | — | — | `NOT_RUN` | `MIGRATION_FAILED` |
| `invariant:coverage_complete` | `coverage_complete` | `coverage_complete` | — | — | `NOT_RUN` | `MIGRATION_FAILED` |
| `invariant:pk_set_unchanged` | `pk_set_unchanged` | `pk_set_unchanged` | — | — | `NOT_RUN` | `MIGRATION_FAILED` |
| `invariant:preserved_values_unchanged` | `preserved_values_unchanged` | `preserved_values_unchanged` | — | — | `NOT_RUN` | `MIGRATION_FAILED` |
| `invariant:schema_expected` | `schema_expected` | `schema_expected` | — | — | `NOT_RUN` | `MIGRATION_FAILED` |
| `invariant:declared_checks_complete` | `declared_checks_complete` | `declared_checks_complete` | — | — | `NOT_RUN` | `MIGRATION_FAILED` |
| `invariant:within_budgets` | `within_budgets` | `within_budgets` | — | — | `NOT_RUN` | `MIGRATION_FAILED` |

## Impact and coverage

| Table | Column | Operation | Rule | Complete | Reason |
|---|---|---|---|---|---|
| — | — | — | — | — | — |

## Execution and recovery

- Migration outcome: `rolled_back`
- Clone migration duration (ms): `30`
- Safe SQLSTATE: `23502`
- Migration reason: `DATABASE_EXECUTION_FAILED`
- Recovery backup available at report time: `true`
- Apply eligible at report time: `false`
- Current apply eligibility: `NOT_EVALUATED`

## Dependency versions

- `boto3`: `1.43.103`
- `mcp`: `2.2.0`
- `pglast`: `8.4`
- `psycopg`: `3.3.6`

## Untested risks

- `Production traffic, application compatibility and downtime untested`
- `Historical clone proof; current source guards still required`
