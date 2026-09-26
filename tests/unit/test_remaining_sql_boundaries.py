"""P03–09 negative candidate boundaries; no database or network connections."""

import json
from pathlib import Path

import pytest

from preflight.models import Contract, PreflightError
from preflight.sql_policy import inspect_sql, resolve_coverage


@pytest.fixture
def contract():
    return Contract.model_validate_json(Path("config/contract.example.json").read_text())


@pytest.mark.parametrize(
    "sql",
    [
        r"\i migration.sql",
        r"\copy public.customers TO STDOUT",
        "SAVEPOINT hidden",
        "SET TRANSACTION READ ONLY",
        "PREPARE hidden AS UPDATE public.customers SET email='x'",
        "CALL public.hidden()",
        "INSERT INTO public.customers(id) VALUES(2001)",
        "TRUNCATE public.customers",
        "GRANT SELECT ON public.customers TO PUBLIC",
        "DROP TABLE public.customers",
        "ALTER TABLE public.customers ALTER COLUMN email SET DEFAULT 'x'",
        "ALTER TABLE public.customers ENABLE TRIGGER ALL",
        "ALTER TABLE public.customers RENAME COLUMN email TO address",
        "ALTER TABLE public.customers ADD COLUMN account_tier text GENERATED ALWAYS AS(email) STORED",
        "ALTER TABLE public.customers ADD COLUMN account_tier integer GENERATED ALWAYS AS IDENTITY",
        "ALTER TABLE public.customers ADD COLUMN account_tier public.text",
        "ALTER TABLE public.customers ADD COLUMN account_tier text[]",
        "UPDATE public.customers SET email = email || 'x'",
        "UPDATE public.customers SET email = ARRAY['x']",
        "UPDATE public.customers SET email = CASE WHEN id=1 THEN 'x' ELSE email END",
        "UPDATE public.customers SET email = 'x' WHERE EXISTS(SELECT 1)",
        "UPDATE public.customers SET email = 'x' WHERE id IN (1,2)",
        "UPDATE public.customers SET email = 'x' WHERE email LIKE '%x'",
        "UPDATE public.customers SET email = 'x' WHERE email COLLATE \"C\" = 'x'",
        "UPDATE public.customers SET email = 'x'::public.text",
        "UPDATE ONLY public.customers SET email = 'x'",
        "UPDATE pg_catalog.customers SET email = 'x'",
        "UPDATE public.customers SET email[1] = 'x'",
        "UPDATE public.customers SET (email,created_at) = ('x',NULL)",
        "ALTER TABLE public.customers ADD COLUMN unrelated text",
    ],
)
def test_p03_through_p08_unsupported_candidate_is_rejected(contract, sql):
    with pytest.raises(PreflightError) as error:
        inspect_sql(sql.encode(), contract)
    assert error.value.code in {"SQL_PARSE_REJECTED", "SQL_POLICY_REJECTED"}


@pytest.mark.parametrize(
    "forbidden",
    ["CALL public.hidden()", "TRUNCATE public.customers", "DROP TABLE public.customers"],
)
def test_p09_forbidden_later_statement_rejects_entire_candidate(contract, forbidden):
    candidate = b"UPDATE public.customers SET email='synthetic'; " + forbidden.encode()
    with pytest.raises(PreflightError, match="SQL_POLICY_REJECTED"):
        inspect_sql(candidate, contract)


@pytest.mark.parametrize(
    "sql",
    [
        b"UPDATE public.customers SET absent='x'",
        b"UPDATE public.customers SET email=absent",
        b"UPDATE public.customers SET email='x' WHERE absent IS NULL",
    ],
)
def test_p08_unknown_target_read_or_predicate_column_refused_at_metadata(contract, sql):
    plan = inspect_sql(sql, contract)
    with pytest.raises(PreflightError, match="UNKNOWN_COLUMN"):
        resolve_coverage(plan, contract, {"public.customers": ["id", "email", "created_at"]})


def test_p07_custom_builtin_lookalike_does_not_expand_grammar(contract):
    # Declaring an intended column cannot turn a user-defined type into a builtin.
    data = json.loads(contract.model_dump_json())
    assert data["tables"][0]["expected_schema"]["added_columns"][0]["name"] == "account_tier"
    with pytest.raises(PreflightError, match="SQL_POLICY_REJECTED"):
        inspect_sql(b"ALTER TABLE public.customers ADD COLUMN account_tier public.text", contract)
