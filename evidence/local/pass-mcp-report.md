# PREFLIGHT — REHEARSAL PASS

> Historical sealed rehearsal evidence. Current source eligibility is not evaluated here.

## Target and provenance

- Evidence backend: `local_postgres_test`
- Run: `9d9888e8-c244-4755-abf5-34b75609e41a`
- Candidate: `965c7736-7f3f-49cb-a699-5d62a98205b9`
- Operator label: `test-operator`
- Created: `2026-09-26T06:27:12.762874Z`
- Source instance: `local-source`
- Snapshot: `local-snapshot`
- Clone instance: `local-clone`
- PostgreSQL major: `18`

## Artifact identity

- Migration SHA-256: `5060eff8b32278aaf28e2ad69fa6bfd6f59ec910ed5e22f9a46244bf314bf97b`
- Contract SHA-256: `f4fa48668e17afa31ee04ced68c898c0428f437dc7ed8f9a387738ece62ca548`
- Report SHA-256: `710e9f667906b85bf953b2656f88cd61ab639f77423036e391b2f464f805d376`
- Report schema / algorithm / manifest: `1.1` / `preflight-json-1` / `1`

## Aggregate evidence

| Table | Rows before | Rows after | Schema before | Schema after | Preserved before | Preserved after | Full before | Full after |
|---|---:|---:|---|---|---|---|---|---|
| `public.customers` | `1000` | `1000` | `6fa5c4d1b188b1e992863f778c4d795880e73b355cf2cb2c8282aa119f9e7c46` | `7bf3e63866ce53f91c12784a571bbf35e618a8d5c7e245b2a1d627e505b9d038` | `adb3ddb070ec6968e1ec28143a38f50875bf39d965095af070e0653e83df6c17` | `adb3ddb070ec6968e1ec28143a38f50875bf39d965095af070e0653e83df6c17` | `dc1744787b061fc7a96efdcc3b3b9e0dc4b2899a8d09c18bf962e4666a2bd9aa` | `dc1744787b061fc7a96efdcc3b3b9e0dc4b2899a8d09c18bf962e4666a2bd9aa` |

## Mandatory checks

| Requirement | Kind | Category | Before | After | Result | Reason |
|---|---|---|---|---|---|---|
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
- Clone migration duration (ms): `30`
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
