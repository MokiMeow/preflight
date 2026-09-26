"""Remaining P11/P12,D09/D10,V28 clauses against disposable loopback PG18."""

import time
import traceback
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from psycopg.pq import TransactionStatus

from preflight.db import execute_migration, validate_catalog
from preflight.evidence import capture_evidence, compare_evidence
from preflight.models import Contract, PreflightError
from preflight.sql_policy import inspect_sql

pytestmark = pytest.mark.postgres


@pytest.fixture
def admin(db):
    with psycopg.connect(
        host="127.0.0.1",
        port=db.info.port,
        dbname=db.info.dbname,
        user="postgres",
        autocommit=True,
        connect_timeout=5,
    ) as connection:
        yield connection


@pytest.mark.parametrize(
    "mutation,code",
    [
        ("ALTER TABLE public.customers SET UNLOGGED", "UNSUPPORTED_TABLE"),
        (
            "ALTER TABLE public.customers ENABLE ROW LEVEL SECURITY; ALTER TABLE public.customers FORCE ROW LEVEL SECURITY",
            "UNSUPPORTED_TABLE",
        ),
        (
            "DROP TABLE public.customers; CREATE TABLE public.customers (id integer PRIMARY KEY,email text,created_at timestamptz) PARTITION BY RANGE(id)",
            "UNSUPPORTED_TABLE",
        ),
        (
            "DROP TABLE public.customers; CREATE VIEW public.customers AS SELECT 1 AS id",
            "UNSUPPORTED_TABLE",
        ),
        (
            "DROP TABLE public.customers; CREATE TABLE public.partition_parent(id integer PRIMARY KEY,email text,created_at timestamptz) PARTITION BY RANGE(id); CREATE TABLE public.customers PARTITION OF public.partition_parent FOR VALUES FROM (1) TO (2000)",
            "UNSUPPORTED_TABLE",
        ),
        (
            "DROP TABLE public.customers; CREATE MATERIALIZED VIEW public.customers AS SELECT 1 AS id",
            "UNSUPPORTED_TABLE",
        ),
        (
            "DROP TABLE public.customers; CREATE FOREIGN DATA WRAPPER fixture_fdw; CREATE SERVER fixture_server FOREIGN DATA WRAPPER fixture_fdw; CREATE FOREIGN TABLE public.customers(id integer) SERVER fixture_server",
            "UNSUPPORTED_TABLE",
        ),
        (
            "ALTER TABLE public.customers ADD COLUMN notes text GENERATED ALWAYS AS(email) STORED",
            "UNSUPPORTED_COLUMN",
        ),
        (
            "ALTER TABLE public.customers ADD COLUMN serial_hint integer GENERATED ALWAYS AS IDENTITY",
            "UNSUPPORTED_COLUMN",
        ),
        (
            "CREATE DOMAIN public.text AS pg_catalog.text; ALTER TABLE public.customers ADD COLUMN notes public.text",
            "UNSUPPORTED_COLUMN",
        ),
        (
            'CREATE COLLATION public.fixture_collation FROM pg_catalog."C"; ALTER TABLE public.customers ADD COLUMN notes text COLLATE public.fixture_collation',
            "UNSUPPORTED_COLLATION",
        ),
        (
            "ALTER TABLE public.customers ADD CONSTRAINT exclusion_hint EXCLUDE USING btree(id WITH =)",
            "UNSUPPORTED_OBJECT_CAPABILITY",
        ),
        (
            "CREATE TABLE public.references_fixture (id integer REFERENCES public.customers(id) ON UPDATE CASCADE ON DELETE CASCADE)",
            "UNSUPPORTED_OBJECT_CAPABILITY",
        ),
        (
            "CREATE TABLE public.referenced_fixture(id integer PRIMARY KEY); INSERT INTO public.referenced_fixture SELECT id FROM public.customers; ALTER TABLE public.customers ADD CONSTRAINT outbound_fk FOREIGN KEY(id) REFERENCES public.referenced_fixture(id) ON UPDATE CASCADE",
            "UNSUPPORTED_OBJECT_CAPABILITY",
        ),
    ],
)
def test_p11_p12_unsupported_catalog_capability_never_returns_evidence(
    db, admin, contract, mutation, code
):
    admin.execute(mutation)
    with pytest.raises(PreflightError, match=code):
        capture_evidence(db, contract)
    assert db.info.transaction_status == TransactionStatus.IDLE


def test_p11_enabled_event_trigger_rejected_without_firing_it(db, admin, contract):
    admin.execute(
        "CREATE FUNCTION public.fixture_event() RETURNS event_trigger LANGUAGE plpgsql AS $$ BEGIN RETURN; END $$"
    )
    admin.execute(
        "CREATE EVENT TRIGGER fixture_event ON ddl_command_end WHEN TAG IN ('ALTER TABLE') EXECUTE FUNCTION public.fixture_event()"
    )
    with pytest.raises(PreflightError, match="UNSUPPORTED_EVENT_TRIGGER"):
        capture_evidence(db, contract)


def test_p12_user_defined_operator_class_rejected(db, admin, contract):
    admin.execute("""CREATE OPERATOR CLASS public.fixture_int_ops FOR TYPE integer USING btree AS
      OPERATOR 1 < (integer,integer), OPERATOR 2 <= (integer,integer),
      OPERATOR 3 = (integer,integer), OPERATOR 4 >= (integer,integer),
      OPERATOR 5 > (integer,integer), FUNCTION 1 pg_catalog.btint4cmp(integer,integer)""")
    admin.execute("CREATE UNIQUE INDEX custom_ops ON public.customers(id public.fixture_int_ops)")
    with pytest.raises(PreflightError, match="UNSUPPORTED_INDEX"):
        capture_evidence(db, contract)


@pytest.mark.parametrize(
    "mutation,code",
    [
        ("DROP TABLE public.customers", "TABLE_MISSING"),
        ("ALTER TABLE public.customers DROP CONSTRAINT customers_pkey", "PRIMARY_KEY_MISMATCH"),
        ("ALTER TABLE public.customers DROP COLUMN email", "PRESERVED_COLUMN_MISSING"),
    ],
)
def test_d09_missing_table_primary_key_or_preserved_column_is_specific(
    db, contract, mutation, code
):
    db.execute(mutation)
    with pytest.raises(PreflightError, match=code):
        capture_evidence(db, contract)


def test_d09_inaccessible_catalog_does_not_fabricate_metadata(db, admin, contract):
    admin.execute("REVOKE SELECT ON pg_catalog.pg_attribute FROM PUBLIC")
    try:
        with pytest.raises(PreflightError, match="CATALOG_INSPECTION_FAILED"):
            validate_catalog(db, contract)
    finally:
        admin.execute("GRANT SELECT ON pg_catalog.pg_attribute TO PUBLIC")


def test_d09_inaccessible_rows_do_not_become_zero_count(db, admin, contract):
    role = "preflight_denied_" + uuid4().hex[:16]
    admin.execute(sql.SQL("CREATE ROLE {} LOGIN").format(sql.Identifier(role)))
    try:
        with psycopg.connect(
            host="127.0.0.1",
            port=db.info.port,
            dbname=db.info.dbname,
            user=role,
            autocommit=True,
            connect_timeout=5,
        ) as denied:
            with pytest.raises(PreflightError, match="EVIDENCE_CAPTURE_FAILED"):
                capture_evidence(denied, contract)
            assert denied.info.transaction_status == TransactionStatus.IDLE
    finally:
        admin.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(role)))


def test_d09_missing_full_baseline_column_is_not_silently_omitted(db, contract):
    with pytest.raises(PreflightError, match="BASELINE_COLUMNS_MISSING"):
        capture_evidence(db, contract, existing_columns={"public.customers": ["id", "absent"]})


def test_d10_serialized_budget_excludes_escape_expansion_overrun(db, contract):
    db.execute("UPDATE public.customers SET email=repeat(chr(1),32)")
    # Raw datum bytes fit, but canonical JSON escapes control characters sixfold.
    limits = contract.model_copy(update={"max_bytes_per_table": 100000})
    assert (
        db.execute(
            "SELECT sum(octet_length(email)+octet_length(id::text)+octet_length(created_at::text)) FROM public.customers"
        ).fetchone()[0]
        < limits.max_bytes_per_table
    )
    with pytest.raises(PreflightError, match="SCAN_BUDGET_EXCEEDED"):
        capture_evidence(db, limits)


@pytest.mark.parametrize("delay_kind", ["row_processing", "fetch_batches"])
@pytest.mark.parametrize("caller_owned_transaction", [False, True])
def test_d10_whole_capture_deadline_includes_row_processing(
    db, contract, delay_kind, caller_owned_transaction
):
    class SlowScan:
        def __init__(self, cursor):
            self.cursor = cursor

        def __getattr__(self, name):
            return getattr(self.cursor, name)

        @property
        def itersize(self):
            return self.cursor.itersize

        @itersize.setter
        def itersize(self, value):
            self.cursor.itersize = value

        def __enter__(self):
            self.cursor.__enter__()
            return self

        def __exit__(self, *args):
            return self.cursor.__exit__(*args)

        def __iter__(self):
            # Real catalog/count/FETCH reads still execute on PostgreSQL. This
            # models bounded local CPU/scheduling delay after a completed fetch.
            for index, row in enumerate(self.cursor):
                if delay_kind == "row_processing" and index == 0:
                    time.sleep(1.15)
                elif delay_kind == "fetch_batches" and index % self.cursor.itersize == 0:
                    time.sleep(0.18)
                yield row

    class SlowCapture:
        def __getattr__(self, name):
            return getattr(db, name)

        def cursor(self, *args, **kwargs):
            cursor = db.cursor(*args, **kwargs)
            return SlowScan(cursor) if kwargs.get("name") else cursor

    limits = contract.model_copy(update={"max_migration_seconds": 1})
    if caller_owned_transaction:
        db.execute("BEGIN ISOLATION LEVEL READ COMMITTED")
    started = time.monotonic()
    try:
        with pytest.raises(PreflightError, match="SCAN_DEADLINE_EXCEEDED"):
            capture_evidence(SlowCapture(), limits, in_transaction=caller_owned_transaction)
        if caller_owned_transaction:
            assert db.info.transaction_status != TransactionStatus.IDLE
    finally:
        if caller_owned_transaction:
            db.execute("ROLLBACK")
    assert time.monotonic() - started < 3
    assert db.info.transaction_status == TransactionStatus.IDLE
    assert db.execute("SELECT count(*) FROM public.customers").fetchone()[0] == 1000


def test_d10_whole_capture_deadline_includes_catalog_processing(db, contract, monkeypatch):
    import preflight.evidence as evidence

    original = evidence.validate_catalog

    def slow_catalog(connection, limits):
        result = original(connection, limits)
        time.sleep(1.15)
        return result

    monkeypatch.setattr(evidence, "validate_catalog", slow_catalog)
    limits = contract.model_copy(update={"max_migration_seconds": 1})
    with pytest.raises(PreflightError, match="SCAN_DEADLINE_EXCEEDED"):
        capture_evidence(db, limits)
    assert db.info.transaction_status == TransactionStatus.IDLE


def test_d10_deadline_error_suppresses_private_underlying_exception(db, contract, monkeypatch):
    import preflight.evidence as evidence

    original = evidence.validate_catalog

    def delayed_failure(connection, limits):
        original(connection, limits)
        time.sleep(1.15)
        raise RuntimeError("PRIVATE_ERROR_SENTINEL")

    monkeypatch.setattr(evidence, "validate_catalog", delayed_failure)
    limits = contract.model_copy(update={"max_migration_seconds": 1})
    with pytest.raises(PreflightError, match="SCAN_DEADLINE_EXCEEDED") as error:
        capture_evidence(db, limits)
    assert "PRIVATE_ERROR_SENTINEL" not in "".join(traceback.format_exception(error.value))
    assert db.info.transaction_status == TransactionStatus.IDLE


def test_d10_baseline_query_timeout_cannot_return_partial_evidence(db, admin, contract):
    limits = contract.model_copy(update={"max_migration_seconds": 1})
    admin.execute("BEGIN")
    admin.execute("LOCK TABLE public.customers IN ACCESS EXCLUSIVE MODE")
    started = time.monotonic()
    try:
        with pytest.raises(PreflightError, match="SCAN_DEADLINE_EXCEEDED"):
            capture_evidence(db, limits)
        assert time.monotonic() - started < 4
        assert db.info.transaction_status == TransactionStatus.IDLE
    finally:
        admin.execute("ROLLBACK")


@pytest.mark.parametrize("literal,expected", [("NULL", "pass"), ("'null'", "fail"), ("''", "fail")])
def test_v28_all_equal_null_requires_actual_null_values(db, contract, literal, expected):
    db.execute("ALTER TABLE public.customers ADD COLUMN notes text")
    data = contract.model_dump(mode="json")
    data["tables"][0]["expected_schema"]["added_columns"] = []
    data["tables"][0]["checks"] = [{"type": "all_equal", "column": "notes", "value": None}]
    nullable = Contract.model_validate(data)
    before = capture_evidence(db, nullable)
    raw = ("UPDATE public.customers SET notes=" + literal).encode()
    plan = inspect_sql(raw, nullable)
    assert execute_migration(db, raw, plan, nullable).outcome == "committed"
    results = compare_evidence(before, capture_evidence(db, nullable), nullable, plan)
    assert next(r.status for r in results.checks if r.category == "all_equal") == expected


def test_v28_empty_table_missing_null_asserted_column_is_not_vacuously_passing(db, contract):
    db.execute("DELETE FROM public.customers")
    data = contract.model_dump(mode="json")
    data["tables"][0]["expected_schema"]["added_columns"][0]["nullable"] = True
    data["tables"][0]["checks"] = [{"type": "all_equal", "column": "account_tier", "value": None}]
    nullable = Contract.model_validate(data)
    before = capture_evidence(db, nullable)
    plan = inspect_sql(b"UPDATE public.customers SET account_tier=NULL", nullable)
    checks = compare_evidence(before, capture_evidence(db, nullable), nullable, plan)
    assert next(r.status for r in checks.checks if r.category == "all_equal") == "fail"
    assert next(r.status for r in checks.checks if r.category == "schema_expected") == "fail"
