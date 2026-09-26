from pathlib import Path
import threading
import time
import psycopg
from psycopg import sql
import pytest
from preflight.db import execute_migration,validate_catalog
from preflight.evidence import capture_evidence,compare_evidence,baseline_matches
from preflight.models import Contract,PreflightError
from preflight.sql_policy import inspect_sql,resolve_coverage

pytestmark = pytest.mark.postgres


def statuses(checks):
    return {c.id:c.status for c in checks.checks}


def script(name):
    return Path('fixtures/'+name+'.sql').read_bytes()


def test_bad_rolls_back_complete_baseline(db,contract):
    before=capture_evidence(db,contract)
    raw=script('bad')
    out=execute_migration(db,raw,inspect_sql(raw,contract),contract)
    assert out.outcome == 'rolled_back'
    assert out.sqlstate == '23502'
    assert baseline_matches(before,capture_evidence(db,contract))


def test_good_commits_real_notnull(db,contract):
    before=capture_evidence(db,contract)
    raw=script('good'); plan=inspect_sql(raw,contract)
    assert execute_migration(db,raw,plan,contract).outcome == 'committed'
    after=capture_evidence(db,contract,existing_columns=before.existing_columns)
    checks=compare_evidence(before,after,contract,plan)
    assert all(c.status=='pass' for c in checks.checks)
    assert before.public.tables[0].full_sha256 == after.public.tables[0].full_sha256
    assert not next(c for c in after.public.tables[0].schema_summary if c['name']=='account_tier')['nullable']
    assert len(checks.checks)==len(checks.requirements)


def test_wrong_data_committed_then_block(db,contract):
    before=capture_evidence(db,contract)
    raw=script('wrong_data'); plan=inspect_sql(raw,contract)
    assert execute_migration(db,raw,plan,contract).outcome == 'committed'
    checks=compare_evidence(before,capture_evidence(db,contract,before.existing_columns),contract,plan)
    assert statuses(checks)['invariant:preserved_values_unchanged']=='fail'
    assert statuses(checks)['declared:public.customers:0:row_count_unchanged']=='pass'


def test_source_precommit_wrong_data_rolls_back(db,contract):
    before=capture_evidence(db,contract)
    raw=script('wrong_data'); plan=inspect_sql(raw,contract)
    def check(conn):
        return compare_evidence(before,capture_evidence(conn,contract,before.existing_columns,in_transaction=True),contract,plan)
    out=execute_migration(db,raw,plan,contract,checks_before_commit=check)
    assert out.outcome=='rolled_back'
    assert out.reason_code=='PRECOMMIT_CHECK_FAILED'
    assert baseline_matches(before,capture_evidence(db,contract))


def test_multiple_statement_failure_rolls_back_first(db,contract):
    before=capture_evidence(db,contract)
    raw=b"UPDATE public.customers SET email='private-error-sentinel' WHERE id=1; ALTER TABLE public.customers ADD COLUMN account_tier text NOT NULL;"
    out=execute_migration(db,raw,inspect_sql(raw,contract),contract)
    assert out.outcome=='rolled_back'
    assert 'private-error-sentinel' not in out.model_dump_json()
    assert baseline_matches(before,capture_evidence(db,contract))


def test_unasserted_existing_column_and_explicit_control(db,contract):
    db.execute('ALTER TABLE public.customers ADD COLUMN notes text')
    db.execute("UPDATE public.customers SET notes='old'")
    data=contract.model_dump(); data['tables'][0]['expected_schema']['added_columns']=[]
    data['tables'][0]['checks']=[{'type':'row_count_unchanged'},{'type':'no_nulls','column':'notes'},{'type':'unique_non_null','column':'email'}]
    weak=Contract.model_validate(data)
    before=capture_evidence(db,weak); raw=b"UPDATE public.customers SET notes='new'"; plan=inspect_sql(raw,weak)
    assert execute_migration(db,raw,plan,weak).outcome=='committed'
    after=capture_evidence(db,weak,before.existing_columns)
    assert statuses(compare_evidence(before,after,weak,plan))['invariant:coverage_complete']=='not_run'
    data['tables'][0]['checks'].append({'type':'all_equal','column':'notes','value':'new'})
    strong=Contract.model_validate(data)
    assert all(c.status=='pass' for c in compare_evidence(before,after,strong,plan).checks)
    assert not baseline_matches(before,after) # Full drift includes unpreserved values.


def test_new_column_null_assertion(db,contract):
    data=contract.model_dump(); data['tables'][0]['expected_schema']['added_columns'][0]['nullable']=True
    data['tables'][0]['checks']=[{'type':'row_count_unchanged'},{'type':'all_equal','column':'account_tier','value':None}]
    nullable=Contract.model_validate(data)
    before=capture_evidence(db,nullable); raw=b'ALTER TABLE public.customers ADD COLUMN account_tier text'; plan=inspect_sql(raw,nullable)
    assert execute_migration(db,raw,plan,nullable).outcome=='committed'
    assert all(c.status=='pass' for c in compare_evidence(before,capture_evidence(db,nullable,before.existing_columns),nullable,plan).checks)


def test_zero_nulls_is_not_notnull(db,contract):
    before=capture_evidence(db,contract)
    raw=b"ALTER TABLE public.customers ADD COLUMN account_tier text; UPDATE public.customers SET account_tier='standard'"; plan=inspect_sql(raw,contract)
    assert execute_migration(db,raw,plan,contract).outcome=='committed'
    checks=compare_evidence(before,capture_evidence(db,contract,before.existing_columns),contract,plan)
    s=statuses(checks)
    assert s['declared:public.customers:1:no_nulls']=='pass'
    assert s['declared:public.customers:3:column_not_null']=='fail'
    assert s['invariant:schema_expected']=='fail'


@pytest.mark.parametrize('mutation',[
    "ALTER TABLE public.customers ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE public.customers ADD CONSTRAINT unsafe CHECK (id>0)",
    "CREATE INDEX unsafe ON public.customers ((lower(email)))",
    "CREATE UNIQUE INDEX unsafe ON public.customers (email) WHERE id>0",
    "ALTER TABLE public.customers ALTER COLUMN email SET DEFAULT 'x'",
    "ALTER TABLE public.customers ADD COLUMN unsafe jsonb",
    "ALTER TABLE public.customers ALTER COLUMN email TYPE text COLLATE \"C\"",
    "CREATE RULE unsafe AS ON UPDATE TO public.customers DO ALSO NOTIFY unsafe",
    "CREATE TABLE public.other (id integer PRIMARY KEY); ALTER TABLE public.customers ADD FOREIGN KEY (id) REFERENCES public.other(id) NOT VALID",
])
def test_semantic_unsafe_objects(db,contract,mutation):
    db.execute(mutation)
    with pytest.raises(PreflightError):
        validate_catalog(db,contract)


def test_changed_keys_and_order_and_full_drift(db,contract):
    before=capture_evidence(db,contract)
    db.execute('CLUSTER public.customers USING customers_pkey')
    assert baseline_matches(before,capture_evidence(db,contract))
    db.execute('UPDATE public.customers SET id=1001 WHERE id=1')
    after=capture_evidence(db,contract)
    plan=inspect_sql(b"UPDATE public.customers SET email=email",contract)
    assert statuses(compare_evidence(before,after,contract,plan))['invariant:pk_set_unchanged']=='fail'


def test_scan_budget_and_huge_cell(db,contract):
    low=contract.model_copy(update={'max_rows_per_table':999})
    with pytest.raises(PreflightError,match='SCAN_BUDGET_EXCEEDED'):
        capture_evidence(db,low)
    db.execute("UPDATE public.customers SET email=repeat('x',11000000) WHERE id=1")
    with pytest.raises(PreflightError,match='SCAN_BUDGET_EXCEEDED'):
        capture_evidence(db,contract)


def test_lock_timeout_and_no_leak(db,contract):
    other=psycopg.connect(host='127.0.0.1',port=db.info.port,dbname=db.info.dbname,user=db.info.user,autocommit=True)
    try:
        other.execute('BEGIN'); other.execute('LOCK TABLE public.customers IN ACCESS EXCLUSIVE MODE')
        limits=contract.model_copy(update={'max_migration_seconds':3})
        raw=b"UPDATE public.customers SET email=email"; plan=inspect_sql(raw,limits)
        out=execute_migration(db,raw,plan,limits)
        assert out.outcome=='rolled_back'
        assert out.sqlstate=='55P03'
    finally:
        other.execute('ROLLBACK'); other.close()


def test_whole_deadline_precommit(db,contract):
    before=capture_evidence(db,contract)
    limits=contract.model_copy(update={'max_migration_seconds':1})
    raw=b"UPDATE public.customers SET email=email"; plan=inspect_sql(raw,limits)
    def slow(conn):
        # Each query is under statement timeout, total callback exceeds the operation budget.
        for _ in range(6):
            conn.execute('SELECT pg_catalog.pg_sleep(0.25)')
        return True
    out=execute_migration(db,raw,plan,limits,checks_before_commit=slow)
    assert out.outcome=='rolled_back'
    assert out.elapsed_ms<2500
    assert baseline_matches(before,capture_evidence(db,contract))
