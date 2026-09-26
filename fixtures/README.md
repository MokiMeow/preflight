These fixtures are synthetic inputs for the disposable local PostgreSQL backend.
`good.sql` backfills and makes the new text column NOT NULL. `bad.sql` fails on
the populated table. `wrong_data.sql` commits on a clone but violates protected
data preservation. The tests seed exactly 1,000 customers without defaults,
triggers or unsupported capabilities; deadline tests separately use 10,000 rows.

Use PostgreSQL 18 binaries from the official PostgreSQL Windows download route
(https://www.postgresql.org/download/windows/). The observed local backend was
EDB PostgreSQL 18.6. Do not describe this backend as AWS evidence.

`local_pg.py` creates only a **new** loopback test cluster inside the checkout.
It requires `cryptography` (observed version 50.0.1), creates short-lived local
test certificates, and refuses to replace existing data. The test owner is
non-superuser; a separate read-only role is exercised. Trust authentication is
confined to this disposable loopback cluster and is not deployment configuration.

PowerShell, with the repository Python interpreter and PostgreSQL binaries:

```powershell
python fixtures/local_pg.py --bin C:/path/to/pgsql/bin
$env:PYTHONPATH=(Join-Path (Get-Location) 'src')
$env:PREFLIGHT_TEST_PG_PORT='55438'
$env:PREFLIGHT_TEST_PG_CA=(Join-Path (Get-Location) 'var/local-postgres/data/server.crt')
python -m pytest tests/unit/test_sql_policy.py tests/unit/test_evidence.py tests/postgres -q
```

The tests refuse a remote DSN, create unique disposable databases, and drop those
databases after each test. They do not operate on RDS or simulate the human gate.
Stop this test cluster explicitly with `pg_ctl -D var/local-postgres/data stop`.
Never copy its generated private keys or server log into Git or public evidence.

`seed_demo.py` initializes a **fresh owned synthetic source**. It is separate
from cloud creation, runtime migration, source-apply approval, and cleanup.
It has no reset, drop, overwrite, or automatic retry mode. Existing customers,
other user relations, enabled event triggers, privileged runtime roles, inherited
roles, schema/database ownership and unreviewed default ACLs block initialization.

Before planning, the private operator JSON must identify the exact account,
region, source, database and owner, singleton source allowlist, and
`public.customers` table allowlist. It must contain distinct named reader/writer
secret ARNs. Cloud creation authorization does **not** authorize seeding:
`aws.seed_or_reset_synthetic_source_authorized` must be explicitly true for apply.
A false value can still produce an offline plan for review. This script never
creates Secrets Manager entries or reads secret files. Provision three separate
named entries using the approved bootstrap identity:

- Admin: the actual source master username and password, unavailable to runtime.
- Writer: `username=preflight_migrator` and a strong password of at least 16 characters.
- Reader: `username=preflight_reader` and a distinct strong password.

Secret JSON contains `username`, `password`, and optional matching `dbname`.
Never put those values in command arguments, operator JSON, saved plans or logs.
Already-provisioned ordinary logins are validated and retained; passwords are
never rotated. A writer owns only the demo table and has no remaining schema
CREATE grant; the reader has schema USAGE and table SELECT, with read-only default.
The bootstrap admin needs role creation/administration and dedicated database
setup privileges. Session statement/error logging must be suppressible before
credential DDL; inability to set those privacy controls fails and rolls back.
No superuser or `rds_superuser` privilege is granted to either runtime role.

From the checked-out project with dependencies installed and `PYTHONPATH=src`:

```text
python fixtures/seed_demo.py plan --operator config/operator-inputs.local.json --admin-secret-arn <approved-master-secret-ARN> --sslrootcert <official-RDS-CA-bundle-path> --out var/source-seed-plan.json
```

Planning performs no network, secret retrieval or database connection. Review
the saved plan and retain its digest independently. Create a separate private
approval JSON containing these exact fields from the reviewed plan:

```json
{
  "operation": "seed_fresh_synthetic_source",
  "plan_sha256": "<reviewed-plan-digest>",
  "account_id": "<approved-account>",
  "region": "<approved-region>",
  "source_instance_id": "<exact-owned-source>",
  "owner": "<approved-owner>",
  "seed_authorized": true
}
```

An authorized operator can then run:

```text
python fixtures/seed_demo.py apply --operator config/operator-inputs.local.json --plan var/source-seed-plan.json --approval var/source-seed-approval.local.json --receipt var/source-seed-receipt.json
```

Apply verifies the current operator policy, exact approved digest, AWS account,
private encrypted PostgreSQL 18 source identity and ownership tags before fetching
only those three named secrets. It uses the described RDS endpoint with
`sslmode=verify-full`; the admin connection is never the runtime connection factory.
The fresh-only transaction creates exactly 1,000 deterministic rows and the
ordinary runtime roles, then verifies their separate TLS logins. A failed login
check after commit is recorded as committed with incomplete readiness, never
rollback. The receipt contains aggregates and role names only.

A durable per-source intent under `var/source-seed-attempts/` blocks subsequent
attempts even with another receipt path or revised plan. Unknown commit outcome
requires manual read-only investigation; never delete that intent to rerun the
initializer. Preserve this state directory across restarts. Bootstrap/admin
credentials must be removed from the deployed runtime environment afterward.
Run the normal semantic catalog and full baseline checks before rehearsal; a
successful source initialization is not RDS rehearsal or human-gate proof.

The local initializer regression command is
`python -m pytest tests/postgres/test_seed_demo.py -q`, with the same explicit
loopback test-port environment above. Those tests execute real PostgreSQL setup,
freshness refusal, narrow roles, atomic rollback and uncertain commit scenarios;
injected cloud observations remain local tests and make no AWS calls.
