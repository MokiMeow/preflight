# PREFLIGHT — REHEARSAL PASS

> Historical sealed rehearsal evidence. Current source eligibility is not evaluated here.

## Target and provenance

- Evidence backend: `aws_rds`
- Run: `7f1a627e-a6d0-4c9f-a5ce-58984b38d41e`
- Candidate: `a09bf95e-30e3-4bd2-95e9-f62fa2551be7`
- Operator label: `team-operator`
- Created: `2026-09-26T11:40:58.041843Z`
- Source instance: `preflight-source`
- Snapshot: `preflight-7f1a627ea6d04c9fa5ce58984b38d41e-snap`
- Clone instance: `preflight-7f1a627ea6d04c9fa5ce58984b38d41e-clone`
- PostgreSQL major: `18`

## Artifact identity

- Migration SHA-256: `5060eff8b32278aaf28e2ad69fa6bfd6f59ec910ed5e22f9a46244bf314bf97b`
- Contract SHA-256: `f4fa48668e17afa31ee04ced68c898c0428f437dc7ed8f9a387738ece62ca548`
- Report SHA-256: `6e069069851c9af3a2f1c021a9afb9ba43ba24f586c27556faa78e3cdda562ab`
- Report schema / algorithm / manifest: `1.1` / `preflight-json-1` / `1`

## Aggregate evidence

| Table | Rows before | Rows after | Schema before | Schema after | Preserved before | Preserved after | Full before | Full after |
|---|---:|---:|---|---|---|---|---|---|
| `public.customers` | `1000` | `1000` | `115c481c32ee7b021e9898e6012e0341e4926c5267b5f473d0a9a0fca1686384` | `f00078073f299382075c8e7c5ff5c30eb595ec0529f866b8b479bef06a99f19d` | `adb3ddb070ec6968e1ec28143a38f50875bf39d965095af070e0653e83df6c17` | `adb3ddb070ec6968e1ec28143a38f50875bf39d965095af070e0653e83df6c17` | `dc1744787b061fc7a96efdcc3b3b9e0dc4b2899a8d09c18bf962e4666a2bd9aa` | `dc1744787b061fc7a96efdcc3b3b9e0dc4b2899a8d09c18bf962e4666a2bd9aa` |

## Mandatory checks

| Requirement | Kind | Category | Before | After | Result | Reason |
|---|---|---|---|---|---|---|
| `coverage:public.customers:missing_keys` | `missing_keys` | `missing_keys` | `0` | `0` | `PASS` | — |
| `coverage:public.customers:extra_keys` | `extra_keys` | `extra_keys` | `0` | `0` | `PASS` | — |
| `coverage:public.customers:changed_preserved_rows` | `changed_preserved_rows` | `changed_preserved_rows` | `0` | `0` | `PASS` | — |
| `declared:public.customers:0:row_count_unchanged` | `row_count_unchanged` | `row_count_unchanged` | — | `true` | `PASS` | — |
| `declared:public.customers:1:no_nulls` | `no_nulls` | `no_nulls` | — | `true` | `PASS` | — |
| `declared:public.customers:2:all_equal` | `all_equal` | `all_equal` | — | `true` | `PASS` | — |
| `declared:public.customers:3:column_not_null` | `column_not_null` | `column_not_null` | — | `true` | `PASS` | — |
| `invariant:pk_set_unchanged` | `pk_set_unchanged` | `pk_set_unchanged` | — | `true` | `PASS` | — |
| `invariant:preserved_values_unchanged` | `preserved_values_unchanged` | `preserved_values_unchanged` | — | `true` | `PASS` | — |
| `invariant:schema_expected` | `schema_expected` | `schema_expected` | — | `true` | `PASS` | — |
| `invariant:coverage_complete` | `coverage_complete` | `coverage_complete` | — | `true` | `PASS` | — |
| `invariant:within_budgets` | `within_budgets` | `within_budgets` | — | `true` | `PASS` | — |
| `invariant:declared_checks_complete` | `declared_checks_complete` | `declared_checks_complete` | — | `true` | `PASS` | — |
| `invariant:exact_candidate_bytes` | `exact_candidate_bytes` | `exact_candidate_bytes` | — | — | `PASS` | — |
| `invariant:policy_accepted` | `policy_accepted` | `policy_accepted` | — | — | `PASS` | — |
| `invariant:clone_provenance` | `clone_provenance` | `clone_provenance` | — | — | `PASS` | — |
| `invariant:baseline_present` | `baseline_present` | `baseline_present` | — | — | `PASS` | — |
| `invariant:source_matched_baseline` | `source_matched_baseline` | `source_matched_baseline` | — | — | `PASS` | — |

## Impact and coverage

| Table | Column | Operation | Rule | Complete | Reason |
|---|---|---|---|---|---|
| `public.customers` | `account_tier` | `add_column` | `all_equal` | `true` | — |
| `public.customers` | `account_tier` | `update` | `all_equal` | `true` | — |
| `public.customers` | `account_tier` | `set_not_null` | `schema` | `true` | — |

## Execution and recovery

- Migration outcome: `committed`
- Clone migration duration (ms): `35`
- Safe SQLSTATE: —
- Migration reason: —
- Recovery backup available at report time: `true`
- Apply eligible at report time: `true`
- Current apply eligibility: `NOT_EVALUATED`

## Dependency versions

- `boto3`: `1.43.103`
- `mcp`: `2.2.0`
- `pglast`: `8.4`
- `psycopg`: `3.3.6`

## Untested risks

- `Production traffic, application compatibility and downtime untested`
- `Historical clone proof; current source guards still required`
