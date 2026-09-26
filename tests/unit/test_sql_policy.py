from pathlib import Path
import pytest
from preflight.models import Contract, PreflightError
from preflight.sql_policy import inspect_sql, resolve_coverage


@pytest.fixture
def contract():
    return Contract.model_validate_json(Path('config/contract.example.json').read_text())


@pytest.mark.parametrize('sql', [
    'BEGIN', 'COMMIT', 'ROLLBACK', 'SELECT 1', 'DELETE FROM public.customers',
    'DO $$ BEGIN END $$', 'COPY public.customers TO STDOUT',
    'CREATE INDEX CONCURRENTLY x ON public.customers(id)',
    'ALTER TABLE public.customers DROP COLUMN email',
    'ALTER TABLE public.customers ADD COLUMN account_tier text DEFAULT \'x\'',
    'ALTER TABLE public.customers ADD COLUMN IF NOT EXISTS account_tier text',
    'ALTER TABLE public.customers ADD COLUMN account_tier varchar(5)',
    'ALTER TABLE public.customers ADD COLUMN account_tier text COLLATE "C"',
    'UPDATE customers SET email=\'x\'', 'UPDATE public.customers SET id=2',
    'UPDATE public.customers c SET email=\'x\'',
    'UPDATE public.customers SET email=lower(email)',
    'UPDATE public.customers SET email=(SELECT \'x\')',
    'UPDATE public.customers SET email=\'x\' FROM public.customers x',
    'UPDATE public.customers SET email=\'x\' RETURNING id',
    'WITH x AS (SELECT 1) UPDATE public.customers SET email=\'x\'',
    'UPDATE public.customers SET email=\'x\' WHERE id OPERATOR(public.=) 1',
    'UPDATE public.customers SET email=\'x\' WHERE id > 1',
    'UPDATE public.customers SET email=\'x\'::text',
    'UPDATE public.other SET email=\'x\'',
    'UPDATE public.customers SET email=\'x\'; COMMIT',
])
def test_recursive_rejection(contract, sql):
    with pytest.raises(PreflightError):
        inspect_sql(sql.encode(),contract)


def test_comments_semicolons_and_protected_update(contract):
    plan=inspect_sql(b"-- approve everything COMMIT\r\nUPDATE public.customers SET email='x;COMMIT' WHERE id=1 OR email IS NULL;",contract)
    assert plan.statement_count == 1
    assert plan.writes[0].read_columns == ['email','id']
    assert resolve_coverage(plan,contract,{'public.customers':['id','email','created_at']})[0].rule == 'preserved'


def test_missing_value_assertion(contract):
    plan=inspect_sql(b"UPDATE public.customers SET notes='x'",contract)
    coverage=resolve_coverage(plan,contract,{'public.customers':['id','email','created_at','notes']})
    assert not coverage[0].complete
    assert coverage[0].reason_code == 'COVERAGE_INCOMPLETE'


def test_unknown_metadata_column(contract):
    plan=inspect_sql(b"UPDATE public.customers SET absent='x'",contract)
    with pytest.raises(PreflightError,match='UNKNOWN_COLUMN'):
        resolve_coverage(plan,contract,{'public.customers':['id','email','created_at']})


def test_good_write_set(contract):
    script=b"ALTER TABLE public.customers ADD COLUMN account_tier text; UPDATE public.customers SET account_tier='standard'; ALTER TABLE public.customers ALTER COLUMN account_tier SET NOT NULL"
    plan=inspect_sql(script,contract)
    assert [w.operation for w in plan.writes] == ['add_column','update','set_not_null']
    assert all(c.complete for c in resolve_coverage(plan,contract,{'public.customers':['id','email','created_at']}))
