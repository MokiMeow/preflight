"""Fresh synthetic source setup against disposable local PostgreSQL only."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql

from preflight.evidence import capture_evidence
from preflight.models import Contract, PreflightError

spec = importlib.util.spec_from_file_location("seed_demo", Path("fixtures/seed_demo.py"))
seed = importlib.util.module_from_spec(spec)
spec.loader.exec_module(seed)
pytestmark = pytest.mark.postgres


def test_intent_is_fsynced_and_never_replaced(monkeypatch, tmp_path):
    real_fsync = seed.os.fsync
    calls = []

    def sync(fd):
        calls.append(fd)
        real_fsync(fd)

    monkeypatch.setattr(seed.os, "fsync", sync)
    intent = tmp_path / "new" / "state" / "intent.json"
    seed._write_once(intent, {"status": "ATTEMPTED"})
    assert calls
    original = intent.read_bytes()
    with pytest.raises(FileExistsError):
        seed._write_once(intent, {"status": "RETRY"})
    assert intent.read_bytes() == original


@pytest.fixture
def fresh():
    port = os.environ.get("PREFLIGHT_TEST_PG_PORT")
    if port is None:
        pytest.fail("Explicit disposable loopback PG18 port required")
    admin = psycopg.connect(
        host="127.0.0.1", port=port, dbname="postgres", user="postgres", autocommit=True
    )
    name = "preflight_seed_" + uuid4().hex
    reader, writer = "preflight_r_" + uuid4().hex[:16], "preflight_w_" + uuid4().hex[:16]
    admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    conn = psycopg.connect(
        host="127.0.0.1", port=port, dbname=name, user="postgres", autocommit=True
    )
    try:
        yield conn, reader, writer
    finally:
        conn.close()
        admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))
        for role in [reader, writer]:
            admin.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(role)))
        admin.close()


def execute(fresh):
    conn, reader, writer = fresh
    return seed.seed_fresh(
        conn,
        writer_role=writer,
        reader_role=reader,
        writer_password="private-writer-password-sentinel",
        reader_password="private-reader-password-sentinel",
        expected_database=conn.info.dbname,
    )


def test_fresh_fixture_roles_and_runtime_evidence(fresh):
    conn, reader, writer = fresh
    result = execute(fresh)
    assert result["row_count"] == 1000 and result["outcome"] == "committed"
    assert "password-sentinel" not in json.dumps(result)
    role = conn.execute(
        "SELECT r.rolname FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace JOIN pg_catalog.pg_roles r ON r.oid=c.relowner WHERE n.nspname='public' AND c.relname='customers'"
    ).fetchone()[0]
    assert role == writer
    assert (
        conn.execute(
            "SELECT count(*) FROM public.customers WHERE email='customer-'||id::text||'@example.invalid' AND created_at=timestamptz '2026-01-01 00:00:00+00'+id*interval '1 second'"
        ).fetchone()[0]
        == 1000
    )
    for name in [reader, writer]:
        assert (
            conn.execute(
                "SELECT rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls FROM pg_catalog.pg_roles WHERE rolname=%s",
                (name,),
            ).fetchone()[0]
            is False
        )
        assert conn.execute(
            "SELECT pg_catalog.has_schema_privilege(%s,'public','CREATE'), pg_catalog.has_database_privilege(%s,current_database(),'CREATE')",
            (name, name),
        ).fetchone() == (False, False)
    data = json.loads(Path("config/contract.example.json").read_text())
    data["database"] = conn.info.dbname
    contract = Contract.model_validate(data)
    owner = psycopg.connect(
        host="127.0.0.1", port=conn.info.port, dbname=conn.info.dbname, user=writer, autocommit=True
    )
    read = psycopg.connect(
        host="127.0.0.1", port=conn.info.port, dbname=conn.info.dbname, user=reader, autocommit=True
    )
    try:
        assert capture_evidence(owner, contract).public == capture_evidence(read, contract).public
        with pytest.raises(psycopg.Error):
            read.execute("UPDATE public.customers SET email=email")
        owner.execute("ALTER TABLE public.customers ADD COLUMN account_tier text")
    finally:
        read.close()
        owner.close()


def test_second_seed_refused_unchanged(fresh):
    execute(fresh)
    conn, reader, writer = fresh
    before = conn.execute("SELECT count(*),sum(id) FROM public.customers").fetchone()
    with pytest.raises(PreflightError, match="SEED_REQUIRES_EMPTY_FRESH_DATABASE"):
        execute(fresh)
    assert before == conn.execute("SELECT count(*),sum(id) FROM public.customers").fetchone()


def test_existing_nonfixture_table_refused_without_roles(fresh):
    conn, reader, writer = fresh
    conn.execute("CREATE TABLE public.existing (id integer)")
    with pytest.raises(PreflightError, match="SEED_REQUIRES_EMPTY_FRESH_DATABASE"):
        execute(fresh)
    assert (
        conn.execute(
            "SELECT count(*) FROM pg_catalog.pg_roles WHERE rolname=ANY(%s)", ([reader, writer],)
        ).fetchone()[0]
        == 0
    )


def test_preprovisioned_narrow_roles_adopted_no_password_change(fresh):
    conn, reader, writer = fresh
    for name in [reader, writer]:
        conn.execute(
            sql.SQL("CREATE ROLE {} LOGIN PASSWORD 'existing-local-test-password'").format(
                sql.Identifier(name)
            )
        )
    before = hashlib.sha256(
        repr(
            conn.execute(
                "SELECT rolname,rolpassword FROM pg_catalog.pg_authid WHERE rolname=ANY(%s) ORDER BY rolname",
                ([reader, writer],),
            ).fetchall()
        ).encode()
    ).hexdigest()
    execute(fresh)
    after = hashlib.sha256(
        repr(
            conn.execute(
                "SELECT rolname,rolpassword FROM pg_catalog.pg_authid WHERE rolname=ANY(%s) ORDER BY rolname",
                ([reader, writer],),
            ).fetchall()
        ).encode()
    ).hexdigest()
    assert before == after


@pytest.mark.parametrize(
    "flag", ["SUPERUSER", "CREATEDB", "CREATEROLE", "REPLICATION", "BYPASSRLS"]
)
def test_existing_privileged_role_refused(fresh, flag):
    conn, reader, writer = fresh
    conn.execute(sql.SQL("CREATE ROLE {} LOGIN ").format(sql.Identifier(writer)) + sql.SQL(flag))
    with pytest.raises(PreflightError, match="SEED_RUNTIME_ROLE_UNSAFE"):
        execute(fresh)
    assert conn.execute("SELECT pg_catalog.to_regclass('public.customers') IS NULL").fetchone()[0]


def test_inherited_privilege_refused(fresh):
    conn, reader, writer = fresh
    conn.execute(sql.SQL("CREATE ROLE {} LOGIN").format(sql.Identifier(writer)))
    conn.execute(sql.SQL("GRANT pg_read_all_data TO {}").format(sql.Identifier(writer)))
    with pytest.raises(PreflightError, match="SEED_RUNTIME_ROLE_MEMBERSHIP_UNSAFE"):
        execute(fresh)


def operator():
    prefix = "arn:aws:secretsmanager:ap-south-1:123456789012:secret:"
    return {
        "operator": {"label": "test-owner"},
        "aws": {
            "account_id": "123456789012",
            "region": "ap-south-1",
            "source_instance_id": "owned-source",
            "database_name": "preflight_demo",
            "resource_owner_label": "test-owner",
            "seed_or_reset_synthetic_source_authorized": True,
            "creation_authorized": False,
            "source_read_secret_arn": prefix + "reader",
            "migration_writer_secret_arn": prefix + "writer",
        },
        "database_policy": {
            "source_allowlist": ["owned-source"],
            "table_allowlist": ["public.customers"],
        },
    }


def approved():
    inputs = operator()
    plan = seed.build_plan(
        inputs, "arn:aws:secretsmanager:ap-south-1:123456789012:secret:master", "/private/ca.pem"
    )
    envelope = seed.plan_envelope(plan)
    approval = {
        k: getattr(plan, k)
        for k in ["operation", "account_id", "region", "source_instance_id", "owner"]
    }
    approval.update(plan_sha256=envelope["plan_sha256"], seed_authorized=True)
    return inputs, envelope, approval


def test_planning_and_approval_separate_from_cloud_creation():
    inputs, envelope, approval = approved()
    assert seed.approve_plan(envelope, inputs, approval).source_seed_authorized
    inputs["aws"]["seed_or_reset_synthetic_source_authorized"] = False
    inputs["aws"]["creation_authorized"] = True
    with pytest.raises(PreflightError):
        seed.approve_plan(envelope, inputs, approval)
    offline = seed.build_plan(inputs, envelope["plan"]["admin_secret_arn"], "/private/ca.pem")
    assert offline.source_seed_authorized is False


def test_changed_approval_and_unallowlisted_secret_block():
    inputs, envelope, approval = approved()
    approval["plan_sha256"] = "0" * 64
    with pytest.raises(PreflightError, match="SOURCE_SEED_NOT_AUTHORIZED"):
        seed.approve_plan(envelope, inputs, approval)
    with pytest.raises(PreflightError, match="SEED_SECRET_REFERENCE_INVALID"):
        seed.build_plan(
            inputs,
            "arn:aws:secretsmanager:ap-south-1:999999999999:secret:master",
            "/private/ca.pem",
        )


def test_offline_cli_never_connects_or_fetches(monkeypatch, tmp_path, capsys):
    inputs, envelope, _ = approved()
    source = tmp_path / "operator.json"
    source.write_text(json.dumps(inputs))
    out = tmp_path / "plan.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "seed_demo.py",
            "plan",
            "--operator",
            str(source),
            "--admin-secret-arn",
            envelope["plan"]["admin_secret_arn"],
            "--sslrootcert",
            "/private/ca.pem",
            "--out",
            str(out),
        ],
    )
    monkeypatch.setattr(
        seed.psycopg, "connect", lambda **kw: pytest.fail("offline planning connected")
    )
    assert seed.main() == 0
    assert json.loads(capsys.readouterr().out)["status"] == "PLANNED_OFFLINE"
    assert out.exists()


def test_connected_unauthorized_stops_before_aws():
    inputs, envelope, _ = approved()
    inputs["aws"]["seed_or_reset_synthetic_source_authorized"] = False
    plan = seed.build_plan(inputs, envelope["plan"]["admin_secret_arn"], "/private/ca.pem")

    class Forbidden:
        def __getattr__(self, _):
            pytest.fail("unauthorized setup touched AWS")

    with pytest.raises(PreflightError, match="SOURCE_SEED_NOT_AUTHORIZED"):
        seed.apply_connected(plan, sts=Forbidden(), rds=Forbidden(), secrets=Forbidden())


def test_ordinary_bootstrap_admin_provisions_narrow_roles(fresh):
    conn, reader, writer = fresh
    admin_role = "preflight_boot_" + uuid4().hex[:16]
    conn.execute(
        sql.SQL("CREATE ROLE {} LOGIN CREATEROLE NOSUPERUSER").format(sql.Identifier(admin_role))
    )
    conn.execute(
        sql.SQL("ALTER DATABASE {} OWNER TO {}").format(
            sql.Identifier(conn.info.dbname), sql.Identifier(admin_role)
        )
    )
    for parameter in ["log_statement", "log_min_error_statement"]:
        conn.execute(
            sql.SQL("GRANT SET ON PARAMETER {} TO {}").format(
                sql.Identifier(parameter), sql.Identifier(admin_role)
            )
        )
    ordinary = psycopg.connect(
        host="127.0.0.1",
        port=conn.info.port,
        dbname=conn.info.dbname,
        user=admin_role,
        autocommit=True,
    )
    try:
        result = seed.seed_fresh(
            ordinary,
            writer_role=writer,
            reader_role=reader,
            writer_password="private-writer-password-sentinel",
            reader_password="private-reader-password-sentinel",
            expected_database=conn.info.dbname,
        )
        assert result["outcome"] == "committed"
        assert (
            conn.execute(
                "SELECT pg_catalog.has_schema_privilege(%s,'public','CREATE')", (writer,)
            ).fetchone()[0]
            is False
        )
    finally:
        ordinary.close()
        conn.execute(
            sql.SQL("ALTER DATABASE {} OWNER TO postgres").format(sql.Identifier(conn.info.dbname))
        )
        conn.execute(sql.SQL("DROP OWNED BY {}").format(sql.Identifier(admin_role)))
        conn.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(admin_role)))


def test_precommit_error_rolls_back_table_and_new_roles(fresh):
    conn, reader, writer = fresh

    class WrongCount:
        def fetchone(self):
            return (999,)

    class FailingSetup:
        def __getattr__(self, key):
            return getattr(conn, key)

        def execute(self, query, *args, **kwargs):
            if query == "SELECT count(*) FROM public.customers":
                return WrongCount()
            return conn.execute(query, *args, **kwargs)

    with pytest.raises(PreflightError, match="SEED_POSTCONDITION_FAILED"):
        seed.seed_fresh(
            FailingSetup(),
            writer_role=writer,
            reader_role=reader,
            writer_password="private-writer-password-sentinel",
            reader_password="private-reader-password-sentinel",
            expected_database=conn.info.dbname,
        )
    assert conn.execute("SELECT pg_catalog.to_regclass('public.customers') IS NULL").fetchone()[0]
    assert (
        conn.execute(
            "SELECT count(*) FROM pg_catalog.pg_roles WHERE rolname=ANY(%s)", ([reader, writer],)
        ).fetchone()[0]
        == 0
    )


def test_commit_response_loss_is_honest_unknown(fresh):
    conn, reader, writer = fresh

    class LostCommit:
        def __getattr__(self, key):
            return getattr(conn, key)

        def execute(self, query, *args, **kwargs):
            assert query != "ROLLBACK"
            result = conn.execute(query, *args, **kwargs)
            if query == "COMMIT":
                raise psycopg.OperationalError("credential-password-sentinel")
            return result

    with pytest.raises(PreflightError, match="SEED_OUTCOME_UNKNOWN") as error:
        seed.seed_fresh(
            LostCommit(),
            writer_role=writer,
            reader_role=reader,
            writer_password="private-writer-password-sentinel",
            reader_password="private-reader-password-sentinel",
            expected_database=conn.info.dbname,
        )
    assert "password-sentinel" not in str(error.value)
    assert conn.execute("SELECT count(*) FROM public.customers").fetchone()[0] == 1000


@pytest.mark.parametrize("identity", ["wrong-account", "wrong-owner", "public-source"])
def test_connected_identity_guards_before_secret_fetch(identity):
    _, envelope, _ = approved()
    plan = seed.SeedPlan.model_validate(envelope["plan"])

    class STS:
        def get_caller_identity(self):
            return {"Account": "999999999999" if identity == "wrong-account" else plan.account_id}

    class RDS:
        def describe_db_instances(self, **kwargs):
            assert kwargs == {"DBInstanceIdentifier": plan.source_instance_id}
            return {
                "DBInstances": [
                    {
                        "DBInstanceIdentifier": plan.source_instance_id,
                        "DBInstanceArn": f"arn:aws:rds:{plan.region}:{plan.account_id}:db:{plan.source_instance_id}",
                        "DBInstanceStatus": "available",
                        "DBName": plan.database,
                        "Engine": "postgres",
                        "EngineVersion": "18.6",
                        "PubliclyAccessible": identity == "public-source",
                        "StorageEncrypted": True,
                    }
                ]
            }

        def list_tags_for_resource(self, **kwargs):
            return {
                "TagList": [
                    {"Key": k, "Value": v}
                    for k, v in {
                        "Project": "Preflight",
                        "Owner": "wrong" if identity == "wrong-owner" else plan.owner,
                        "Purpose": "synthetic-source",
                    }.items()
                ]
            }

    class Forbidden:
        def __getattr__(self, _):
            pytest.fail("identity rejection fetched secrets")

    with pytest.raises(PreflightError):
        seed.apply_connected(plan, sts=STS(), rds=RDS(), secrets=Forbidden())


def test_attempt_intent_blocks_cli_replay(monkeypatch, tmp_path, capsys):
    inputs, envelope, approval = approved()
    for name, value in [
        ("operator.json", inputs),
        ("plan.json", envelope),
        ("approval.json", approval),
    ]:
        (tmp_path / name).write_text(json.dumps(value))
    receipt = tmp_path / "receipt.json"
    intent = tmp_path / "fixed-source.intent.json"
    intent.write_text("{}")
    monkeypatch.setattr(seed, "_intent_path", lambda plan: intent)
    monkeypatch.setattr(
        "sys.argv",
        [
            "seed_demo.py",
            "apply",
            "--operator",
            str(tmp_path / "operator.json"),
            "--plan",
            str(tmp_path / "plan.json"),
            "--approval",
            str(tmp_path / "approval.json"),
            "--receipt",
            str(receipt),
        ],
    )
    assert seed.main() == 2
    assert (
        json.loads(capsys.readouterr().out)["reason_code"]
        == "SEED_ATTEMPT_EXISTS_MANUAL_RESOLUTION_REQUIRED"
    )
