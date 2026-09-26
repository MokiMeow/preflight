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
