# PREFLIGHT — REHEARSAL BLOCK

> Historical sealed rehearsal evidence. Current source eligibility is not evaluated here.

## Target and provenance

- Evidence backend: `aws_rds`
- Run: `7f1a627e-a6d0-4c9f-a5ce-58984b38d41e`
- Candidate: `d77e7d74-7b9f-47fa-af03-5fc64cdc50d8`
- Operator label: `operator-unlimited-continuation`
- Created: `2026-09-26T11:38:54.483135Z`
- Source instance: `preflight-source`
- Snapshot: `preflight-7f1a627ea6d04c9fa5ce58984b38d41e-snap`
- Clone instance: `preflight-7f1a627ea6d04c9fa5ce58984b38d41e-clone`
- PostgreSQL major: `18`

## Artifact identity

- Migration SHA-256: `10101d7c639d383807f6fbe855b63bfa15b6a7f603ca44b85d9f44eaa7349c64`
- Contract SHA-256: `f4fa48668e17afa31ee04ced68c898c0428f437dc7ed8f9a387738ece62ca548`
- Report SHA-256: `c6332b9c508fcab0dd228f5d225654fe939575511f41e87561d492b8c0e82a61`
- Report schema / algorithm / manifest: `1.1` / `preflight-json-1` / `1`

## Aggregate evidence

| Table | Rows before | Rows after | Schema before | Schema after | Preserved before | Preserved after | Full before | Full after |
|---|---:|---:|---|---|---|---|---|---|
| `public.customers` | `1000` | — | `115c481c32ee7b021e9898e6012e0341e4926c5267b5f473d0a9a0fca1686384` | — | `adb3ddb070ec6968e1ec28143a38f50875bf39d965095af070e0653e83df6c17` | — | `dc1744787b061fc7a96efdcc3b3b9e0dc4b2899a8d09c18bf962e4666a2bd9aa` | — |

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
- Clone migration duration (ms): `33`
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
