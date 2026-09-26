import os
from pathlib import Path

import psycopg
import pytest
from psycopg import sql

from preflight.db import connect_database, execute_migration, validate_catalog
from preflight.evidence import baseline_matches, capture_evidence, compare_evidence
from preflight.models import Contract, PreflightError
from preflight.sql_policy import inspect_sql

pytestmark = pytest.mark.postgres


def statuses(checks):
    return {c.id: c.status for c in checks.checks}


def script(name):
    return Path("fixtures/" + name + ".sql").read_bytes()


def test_bad_rolls_back_complete_baseline(db, contract):
    before = capture_evidence(db, contract)
    raw = script("bad")
    out = execute_migration(db, raw, inspect_sql(raw, contract), contract)
    assert out.outcome == "rolled_back"
    assert out.sqlstate == "23502"
    assert baseline_matches(before, capture_evidence(db, contract))


def test_good_commits_real_notnull(db, contract):
    before = capture_evidence(db, contract)
    raw = script("good")
    plan = inspect_sql(raw, contract)
    assert execute_migration(db, raw, plan, contract).outcome == "committed"
    after = capture_evidence(db, contract, existing_columns=before.existing_columns)
    checks = compare_evidence(before, after, contract, plan)
    assert all(c.status == "pass" for c in checks.checks)
    assert before.public.tables[0].full_sha256 == after.public.tables[0].full_sha256
    assert not next(
        c for c in after.public.tables[0].schema_summary if c["name"] == "account_tier"
    )["nullable"]
    assert len(checks.checks) == len(checks.requirements)


def test_wrong_data_committed_then_block(db, contract):
    before = capture_evidence(db, contract)
    raw = script("wrong_data")
    plan = inspect_sql(raw, contract)
    assert execute_migration(db, raw, plan, contract).outcome == "committed"
    checks = compare_evidence(
        before, capture_evidence(db, contract, before.existing_columns), contract, plan
    )
    assert statuses(checks)["invariant:preserved_values_unchanged"] == "fail"
    assert statuses(checks)["declared:public.customers:0:row_count_unchanged"] == "pass"


def test_source_precommit_wrong_data_rolls_back(db, contract):
    before = capture_evidence(db, contract)
    raw = script("wrong_data")
    plan = inspect_sql(raw, contract)

    def check(conn):
        return compare_evidence(
            before,
            capture_evidence(conn, contract, before.existing_columns, in_transaction=True),
            contract,
            plan,
        )

    out = execute_migration(db, raw, plan, contract, checks_before_commit=check)
    assert out.outcome == "rolled_back"
    assert out.reason_code == "PRECOMMIT_CHECK_FAILED"
    assert baseline_matches(before, capture_evidence(db, contract))


def test_multiple_statement_failure_rolls_back_first(db, contract):
    before = capture_evidence(db, contract)
    raw = b"UPDATE public.customers SET email='private-error-sentinel' WHERE id=1; ALTER TABLE public.customers ADD COLUMN account_tier text NOT NULL;"
    out = execute_migration(db, raw, inspect_sql(raw, contract), contract)
    assert out.outcome == "rolled_back"
    assert "private-error-sentinel" not in out.model_dump_json()
    assert baseline_matches(before, capture_evidence(db, contract))


def test_unasserted_existing_column_and_explicit_control(db, contract):
    db.execute("ALTER TABLE public.customers ADD COLUMN notes text")
    db.execute("UPDATE public.customers SET notes='old'")
    data = contract.model_dump()
    data["tables"][0]["expected_schema"]["added_columns"] = []
    data["tables"][0]["checks"] = [
        {"type": "row_count_unchanged"},
        {"type": "no_nulls", "column": "notes"},
        {"type": "unique_non_null", "column": "email"},
    ]
    weak = Contract.model_validate(data)
    before = capture_evidence(db, weak)
    raw = b"UPDATE public.customers SET notes='new'"
    plan = inspect_sql(raw, weak)
    assert execute_migration(db, raw, plan, weak).outcome == "committed"
    after = capture_evidence(db, weak, before.existing_columns)
    assert (
        statuses(compare_evidence(before, after, weak, plan))["invariant:coverage_complete"]
        == "not_run"
    )
    data["tables"][0]["checks"].append({"type": "all_equal", "column": "notes", "value": "new"})
    strong = Contract.model_validate(data)
    assert all(c.status == "pass" for c in compare_evidence(before, after, strong, plan).checks)
    assert not baseline_matches(before, after)  # Full drift includes unpreserved values.


def test_new_column_null_assertion(db, contract):
    data = contract.model_dump()
    data["tables"][0]["expected_schema"]["added_columns"][0]["nullable"] = True
    data["tables"][0]["checks"] = [
        {"type": "row_count_unchanged"},
        {"type": "all_equal", "column": "account_tier", "value": None},
    ]
    nullable = Contract.model_validate(data)
    before = capture_evidence(db, nullable)
    raw = b"ALTER TABLE public.customers ADD COLUMN account_tier text"
    plan = inspect_sql(raw, nullable)
    assert execute_migration(db, raw, plan, nullable).outcome == "committed"
    assert all(
        c.status == "pass"
        for c in compare_evidence(
            before, capture_evidence(db, nullable, before.existing_columns), nullable, plan
        ).checks
    )


def test_zero_nulls_is_not_notnull(db, contract):
    before = capture_evidence(db, contract)
    raw = b"ALTER TABLE public.customers ADD COLUMN account_tier text; UPDATE public.customers SET account_tier='standard'"
    plan = inspect_sql(raw, contract)
    assert execute_migration(db, raw, plan, contract).outcome == "committed"
    checks = compare_evidence(
        before, capture_evidence(db, contract, before.existing_columns), contract, plan
    )
    s = statuses(checks)
    assert s["declared:public.customers:1:no_nulls"] == "pass"
    assert s["declared:public.customers:3:column_not_null"] == "fail"
    assert s["invariant:schema_expected"] == "fail"


@pytest.mark.parametrize(
    "mutation",
    [
        "ALTER TABLE public.customers ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE public.customers ADD CONSTRAINT unsafe CHECK (id>0)",
        "CREATE INDEX unsafe ON public.customers ((lower(email)))",
        "CREATE UNIQUE INDEX unsafe ON public.customers (email) WHERE id>0",
        "ALTER TABLE public.customers ALTER COLUMN email SET DEFAULT 'x'",
        "ALTER TABLE public.customers ADD COLUMN unsafe jsonb",
        'ALTER TABLE public.customers ALTER COLUMN email TYPE text COLLATE "C"',
        "CREATE RULE unsafe AS ON UPDATE TO public.customers DO ALSO NOTIFY unsafe",
        "CREATE TABLE public.other (id integer PRIMARY KEY); ALTER TABLE public.customers ADD FOREIGN KEY (id) REFERENCES public.other(id) NOT VALID",
    ],
)
def test_semantic_unsafe_objects(db, contract, mutation):
    db.execute(mutation)
    with pytest.raises(PreflightError):
        validate_catalog(db, contract)


def test_changed_keys_and_order_and_full_drift(db, contract):
    before = capture_evidence(db, contract)
    db.execute("CLUSTER public.customers USING customers_pkey")
    assert baseline_matches(before, capture_evidence(db, contract))
    db.execute("UPDATE public.customers SET id=1001 WHERE id=1")
    after = capture_evidence(db, contract)
    plan = inspect_sql(b"UPDATE public.customers SET email=email", contract)
    assert (
        statuses(compare_evidence(before, after, contract, plan))["invariant:pk_set_unchanged"]
        == "fail"
    )


def test_scan_budget_and_huge_cell(db, contract):
    low = contract.model_copy(update={"max_rows_per_table": 999})
    with pytest.raises(PreflightError, match="SCAN_BUDGET_EXCEEDED"):
        capture_evidence(db, low)
    db.execute("UPDATE public.customers SET email=repeat('x',11000000) WHERE id=1")
    with pytest.raises(PreflightError, match="SCAN_BUDGET_EXCEEDED"):
        capture_evidence(db, contract)


def test_lock_timeout_and_no_leak(db, contract):
    other = psycopg.connect(
        host="127.0.0.1",
        port=db.info.port,
        dbname=db.info.dbname,
        user=db.info.user,
        autocommit=True,
    )
    try:
        other.execute("BEGIN")
        other.execute("LOCK TABLE public.customers IN ACCESS EXCLUSIVE MODE")
        limits = contract.model_copy(update={"max_migration_seconds": 3})
        raw = b"UPDATE public.customers SET email=email"
        plan = inspect_sql(raw, limits)
        out = execute_migration(db, raw, plan, limits)
        assert out.outcome == "rolled_back"
        assert out.sqlstate == "55P03"
    finally:
        other.execute("ROLLBACK")
        other.close()


def test_whole_deadline_precommit(db, contract):
    before = capture_evidence(db, contract)
    limits = contract.model_copy(update={"max_migration_seconds": 1})
    raw = b"UPDATE public.customers SET email=email"
    plan = inspect_sql(raw, limits)

    def slow(conn):
        # Each query is under statement timeout, total callback exceeds the operation budget.
        for _ in range(6):
            conn.execute("SELECT pg_catalog.pg_sleep(0.25)")
        return True

    out = execute_migration(db, raw, plan, limits, checks_before_commit=slow)
    assert out.outcome == "rolled_back"
    assert out.elapsed_ms < 2500
    assert baseline_matches(before, capture_evidence(db, contract))


def test_tls_hostname_ca_major_and_role(db):
    cert = Path(os.environ["PREFLIGHT_TEST_PG_CA"])

    def connect(host="localhost", ca=cert, user=db.info.user, major=18):
        return connect_database(host, db.info.port, db.info.dbname, user, None, str(ca), major)

    conn = connect()
    assert conn.pgconn.ssl_in_use
    conn.close()
    with pytest.raises(PreflightError, match="DATABASE_CONNECTION_FAILED"):
        connect(host="127.0.0.1")
    with pytest.raises(PreflightError, match="DATABASE_CONNECTION_FAILED"):
        connect(ca=cert.with_name("unrelated-ca.crt"))
    with pytest.raises(PreflightError, match="DATABASE_MAJOR_MISMATCH"):
        connect(major=17)
    with pytest.raises(PreflightError, match="DATABASE_SESSION_UNSAFE"):
        connect(user="postgres")


def test_repeatable_read_snapshot_survives_concurrent_writer(db, contract, monkeypatch):
    import preflight.evidence as engine

    before = capture_evidence(db, contract)
    original = engine.validate_catalog

    def metadata_then_write(conn, con):
        result = original(conn, con)
        other = psycopg.connect(
            host="127.0.0.1",
            port=db.info.port,
            dbname=db.info.dbname,
            user=db.info.user,
            autocommit=True,
        )
        try:
            other.execute(
                "UPDATE public.customers SET email='concurrent@example.invalid' WHERE id=1"
            )
        finally:
            other.close()
        return result

    monkeypatch.setattr(engine, "validate_catalog", metadata_then_write)
    simultaneous = capture_evidence(db, contract)
    assert baseline_matches(before, simultaneous)
    monkeypatch.setattr(engine, "validate_catalog", original)
    assert not baseline_matches(before, capture_evidence(db, contract))


def test_commit_response_loss_is_unknown_not_rollback(db, contract):
    class LostCommitCursor:
        def __init__(self, cur):
            self.cur = cur

        def __enter__(self):
            self.cur.__enter__()
            return self

        def __exit__(self, *args):
            return self.cur.__exit__(*args)

        def __getattr__(self, key):
            return getattr(self.cur, key)

        def execute(self, query, *args, **kwargs):
            result = self.cur.execute(query, *args, **kwargs)
            if query == "COMMIT":
                raise psycopg.OperationalError("private driver error sentinel")
            return result

    class LostCommitConnection:
        def __getattr__(self, key):
            return getattr(db, key)

        def cursor(self, *args, **kwargs):
            return LostCommitCursor(db.cursor(*args, **kwargs))

        def execute(self, query, *args, **kwargs):
            assert query != "ROLLBACK", "Uncertain commit must never be described as rollback"
            return db.execute(query, *args, **kwargs)

    raw = script("good")
    plan = inspect_sql(raw, contract)
    out = execute_migration(LostCommitConnection(), raw, plan, contract)
    assert out.outcome == "unknown"
    assert "private driver error sentinel" not in out.model_dump_json()
    after = capture_evidence(db, contract)
    assert any(c["name"] == "account_tier" for c in after.public.tables[0].schema_summary)


def test_connection_loss_before_commit_is_unknown(db, contract):
    before = capture_evidence(db, contract)
    raw = script("good")
    plan = inspect_sql(raw, contract)
    port, database, user = db.info.port, db.info.dbname, db.info.user

    def disconnect(conn):
        killer = psycopg.connect(
            host="127.0.0.1", port=port, dbname="postgres", user="postgres", autocommit=True
        )
        killer.execute("SELECT pg_catalog.pg_terminate_backend(%s)", (conn.info.backend_pid,))
        killer.close()
        conn.execute("SELECT 1")

    out = execute_migration(db, raw, plan, contract, checks_before_commit=disconnect)
    assert out.outcome == "unknown"
    independent = psycopg.connect(
        host="127.0.0.1", port=port, dbname=database, user=user, autocommit=True
    )
    try:
        assert baseline_matches(before, capture_evidence(independent, contract))
    finally:
        independent.close()


def test_legacy_missing_schema_is_incomplete(db, contract):
    data = contract.model_dump()
    data["schema_version"] = "1"
    data["tables"][0]["expected_schema"] = None
    data["tables"][0]["checks"] = [{"type": "row_count_unchanged"}]
    legacy = Contract.model_validate(data)
    before = capture_evidence(db, legacy)
    raw = b"UPDATE public.customers SET email=email"
    plan = inspect_sql(raw, legacy)
    assert execute_migration(db, raw, plan, legacy).outcome == "committed"
    checks = compare_evidence(before, capture_evidence(db, legacy), legacy, plan)
    assert statuses(checks)["invariant:schema_expected"] == "not_run"
    assert not any(c.status == "fail" for c in checks.checks)


def test_whole_script_deadline_across_quick_updates(db, contract):
    db.execute(
        "INSERT INTO public.customers SELECT i,'customer-'||i::text||'@example.invalid',timestamptz '2026-01-01 00:00:00+00'+i*interval '1 second' FROM generate_series(1001,10000) i"
    )
    baseline_limits = contract.model_copy(update={"max_rows_per_table": 10000})
    before = capture_evidence(db, baseline_limits)
    limits = baseline_limits.model_copy(update={"max_migration_seconds": 1})
    raw = b"UPDATE public.customers SET email=email;" * 128
    plan = inspect_sql(raw, limits)
    outcome = execute_migration(db, raw, plan, limits)
    assert outcome.outcome == "rolled_back"
    assert outcome.elapsed_ms < 2500
    assert baseline_matches(before, capture_evidence(db, baseline_limits))


def test_separate_readonly_role_cannot_migrate(db, contract):
    admin = psycopg.connect(
        host="127.0.0.1", port=db.info.port, dbname=db.info.dbname, user="postgres", autocommit=True
    )
    role = "preflight_test_reader"
    if not admin.execute("SELECT 1 FROM pg_catalog.pg_roles WHERE rolname=%s", (role,)).fetchone():
        admin.execute(
            sql.SQL("CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE").format(
                sql.Identifier(role)
            )
        )
        admin.execute(
            sql.SQL("ALTER ROLE {} SET default_transaction_read_only=on").format(
                sql.Identifier(role)
            )
        )
    admin.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(role)))
    admin.execute(sql.SQL("GRANT SELECT ON public.customers TO {}").format(sql.Identifier(role)))
    reader = psycopg.connect(
        host="127.0.0.1", port=db.info.port, dbname=db.info.dbname, user=role, autocommit=True
    )
    try:
        assert baseline_matches(capture_evidence(db, contract), capture_evidence(reader, contract))
        raw = b"UPDATE public.customers SET email=email"
        outcome = execute_migration(reader, raw, inspect_sql(raw, contract), contract)
        assert outcome.outcome == "rolled_back"
        assert outcome.sqlstate == "25006"
    finally:
        reader.close()
        admin.close()


@pytest.mark.parametrize(
    "mutation",
    [
        "CREATE FUNCTION public.unsafe_trigger() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RETURN NEW; END $$; CREATE TRIGGER unsafe BEFORE UPDATE ON public.customers FOR EACH ROW EXECUTE FUNCTION public.unsafe_trigger()",
        "CREATE TABLE public.child () INHERITS (public.customers)",
    ],
)
def test_trigger_and_inheritance_rejected(db, contract, mutation):
    db.execute(mutation)
    with pytest.raises(PreflightError, match="UNSUPPORTED_OBJECT_CAPABILITY"):
        validate_catalog(db, contract)


def test_exact_utf8_bytes_and_string_semantics(db, contract):
    raw = "-- Unicode é; inert COMMIT\r\nUPDATE public.customers SET email='exact\\text;é' WHERE id=1;\r\n".encode(
        "utf-8"
    )
    plan = inspect_sql(raw, contract)
    observed = []

    class RecordingCursor:
        def __init__(self, cursor):
            self.cursor = cursor

        def __enter__(self):
            self.cursor.__enter__()
            return self

        def __exit__(self, *args):
            return self.cursor.__exit__(*args)

        def __getattr__(self, name):
            return getattr(self.cursor, name)

        def execute(self, query, *args, **kwargs):
            if isinstance(query, str) and query.startswith("-- Unicode"):
                observed.append(query.encode("utf-8"))
                assert kwargs == {"prepare": False}
                assert not args
            return self.cursor.execute(query, *args, **kwargs)

    class RecordingConnection:
        def __getattr__(self, name):
            return getattr(db, name)

        def cursor(self, *args, **kwargs):
            return RecordingCursor(db.cursor(*args, **kwargs))

    db.execute("SET standard_conforming_strings=off")
    outcome = execute_migration(RecordingConnection(), raw, plan, contract)
    assert outcome.outcome == "committed"
    assert observed == [raw]
    assert db.execute(
        "SELECT email=%s FROM public.customers WHERE id=1", ("exact\\text;é",)
    ).fetchone()[0]


def test_non_utf8_session_rejected_before_execution(db, contract):
    raw = b"UPDATE public.customers SET email=email"
    db.execute("SET client_encoding='LATIN1'")
    try:
        with pytest.raises(PreflightError, match="DATABASE_ENCODING_UNSUPPORTED"):
            execute_migration(db, raw, inspect_sql(raw, contract), contract)
    finally:
        db.execute("SET client_encoding='UTF8'")
