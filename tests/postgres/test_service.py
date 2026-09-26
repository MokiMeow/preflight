"""Full service causal chain on real disposable PG; never AWS/human-gate proof."""

import base64
import os
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql

from preflight.artifacts import sha256
from preflight.config import Settings
from preflight.models import PreflightError
from preflight.service import RehearsalService


class LocalRuntime:
    local_test_only = True

    def __init__(self, source, clone, port):
        self.source, self.clone, self.port = source, clone, port
        self.writer_count = 0
        self.backup_available = True

    def verify_resources(self, run, require_backup=False):
        if require_backup and not self.backup_available:
            raise PreflightError("BACKUP_UNAVAILABLE")
        if run["source_instance_id"] == run["clone_instance_id"]:
            raise PreflightError("SOURCE_CLONE_COLLISION")

    @contextmanager
    def connection(self, run, mode):
        if mode == "source_write":
            self.writer_count += 1
        database = self.source if mode.startswith("source") else self.clone
        con = psycopg.connect(
            host="127.0.0.1",
            port=self.port,
            dbname=database,
            user="preflight_test_owner",
            autocommit=True,
        )
        try:
            yield con
        finally:
            con.close()


@pytest.fixture
def service_pair(tmp_path):
    port = os.environ.get("PREFLIGHT_TEST_PG_PORT")
    if not port:
        pytest.fail("Real PostgreSQL18 port required")
    admin = psycopg.connect(
        host="127.0.0.1", port=port, dbname="postgres", user="postgres", autocommit=True
    )
    assert admin.info.server_version // 10000 == 18
    if not admin.execute(
        "SELECT 1 FROM pg_catalog.pg_roles WHERE rolname='preflight_test_owner'"
    ).fetchone():
        admin.execute("CREATE ROLE preflight_test_owner LOGIN NOSUPERUSER")
    databases = ["preflight_service_" + uuid4().hex for _ in range(2)]
    for database in databases:
        admin.execute(
            sql.SQL("CREATE DATABASE {} OWNER preflight_test_owner").format(
                sql.Identifier(database)
            )
        )
        with psycopg.connect(
            host="127.0.0.1",
            port=port,
            dbname=database,
            user="preflight_test_owner",
            autocommit=True,
        ) as con:
            con.execute(
                "CREATE TABLE public.customers(id integer PRIMARY KEY,email text NOT NULL,created_at timestamptz NOT NULL)"
            )
            con.execute(
                "INSERT INTO public.customers SELECT i,'customer-'||i::text||'@example.invalid',timestamptz '2026-01-01 00:00:00+00'+i*interval '1 second' FROM generate_series(1,1000) i"
            )
    runtime = LocalRuntime(*databases, port)
    settings = Settings(
        state_dir=tmp_path,
        evidence_backend="local_postgres_test",
        source_instance_id="local-source",
        source_allowlist=["local-source"],
    )
    service = RehearsalService(settings, runtime)
    try:
        yield service, runtime
    finally:
        service.executor.shutdown(wait=True)
        for database in databases:
            admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(database)))
        admin.close()


def call(service, tool, **args):
    result = service.call(tool, {"request_id": str(uuid4()), **args})
    assert result["ok"], result
    return result["data"]


def register(service, filename, contract, **args):
    raw = Path(filename).read_bytes()
    return call(
        service,
        "register_candidate",
        sql_utf8_b64=base64.b64encode(raw).decode(),
        expected_migration_sha256=sha256(raw),
        contract=contract.model_dump(mode="json"),
        operator_id="test-operator",
        **args,
    )


def ready_run(service, candidate):
    run_id = str(uuid4())
    service.store.create_run(
        {
            "run_id": run_id,
            "candidate_id": candidate["candidate_id"],
            "source_instance_id": "local-source",
            "clone_instance_id": "local-clone",
            "snapshot_id": "local-snapshot",
            "database_name": "preflight_demo",
        }
    )
    for old, new in [
        ("REGISTERED", "SNAPSHOTTING"),
        ("SNAPSHOTTING", "RESTORING"),
        ("RESTORING", "READY"),
    ]:
        service.store.transition(run_id, old, new)
    return run_id


def pass_rehearsal(service, contract):
    candidate = register(service, "fixtures/good.sql", contract)
    run_id = ready_run(service, candidate)
    call(service, "capture_baseline", run_id=run_id)
    result = call(service, "apply_to_clone", run_id=run_id, candidate_id=candidate["candidate_id"])
    assert result["transaction"]["outcome"] == "committed"
    report = call(service, "validate_rehearsal", run_id=run_id)
    assert report["verdict"] == "PASS", report
    return run_id, candidate, report


def test_bad_rollback_revision_good_pass_exact_report_and_disabled_source(service_pair, contract):
    service, runtime = service_pair
    bad = register(service, "fixtures/bad.sql", contract)
    run_id = ready_run(service, bad)
    baseline = call(service, "capture_baseline", run_id=run_id)
    assert baseline["baseline"]["tables"][0]["row_count"] == 1000
    failed = call(service, "apply_to_clone", run_id=run_id, candidate_id=bad["candidate_id"])
    assert failed["transaction"]["outcome"] == "rolled_back"
    assert failed["baseline_unchanged"] is True
    blocked = call(service, "validate_rehearsal", run_id=run_id)
    assert blocked["verdict"] == "BLOCK"
    good = register(
        service,
        "fixtures/good.sql",
        contract,
        run_id=run_id,
        parent_candidate_id=bad["candidate_id"],
    )
    call(service, "apply_to_clone", run_id=run_id, candidate_id=good["candidate_id"])
    passed = call(service, "validate_rehearsal", run_id=run_id)
    assert passed["verdict"] == "PASS", passed
    old = call(service, "get_report", run_id=run_id, candidate_id=bad["candidate_id"])
    new = call(service, "get_report", run_id=run_id)
    assert old["report_sha256"] == blocked["report_sha256"]
    assert new["payload"]["evidence_backend"] == "local_postgres_test"
    assert service.store.get_run(run_id)["phase"] == "AWAITING_APPROVAL"
    denied = service.call(
        "apply_to_demo_source",
        {
            "request_id": str(uuid4()),
            "run_id": run_id,
            "candidate_id": good["candidate_id"],
            "migration_sha256": good["migration_sha256"],
            "report_sha256": passed["report_sha256"],
            "source_instance_id": "local-source",
        },
    )
    assert denied["error_code"] == "SOURCE_APPLY_DISABLED"
    assert runtime.writer_count == 0


def test_committed_wrong_data_blocks_and_revision_refused(service_pair, contract):
    service, _ = service_pair
    candidate = register(service, "fixtures/wrong_data.sql", contract)
    run_id = ready_run(service, candidate)
    call(service, "capture_baseline", run_id=run_id)
    outcome = call(service, "apply_to_clone", run_id=run_id, candidate_id=candidate["candidate_id"])
    assert outcome["transaction"]["outcome"] == "committed"
    report = call(service, "validate_rehearsal", run_id=run_id)
    assert report["verdict"] == "BLOCK"
    raw = Path("fixtures/good.sql").read_bytes()
    refused = service.call(
        "register_candidate",
        {
            "request_id": str(uuid4()),
            "run_id": run_id,
            "parent_candidate_id": candidate["candidate_id"],
            "sql_utf8_b64": base64.b64encode(raw).decode(),
            "expected_migration_sha256": sha256(raw),
            "contract": contract.model_dump(mode="json"),
            "operator_id": "test-operator",
        },
    )
    assert refused["error_code"] == "FRESH_REHEARSAL_REQUIRED"


def source_request(run_id, candidate, report):
    return {
        "request_id": str(uuid4()),
        "run_id": run_id,
        "candidate_id": candidate["candidate_id"],
        "migration_sha256": candidate["migration_sha256"],
        "report_sha256": report["report_sha256"],
        "source_instance_id": "local-source",
    }


def test_source_service_guarded_apply_and_replay_receipt_local_only(service_pair, contract):
    service, runtime = service_pair
    service._test_source_apply = True  # test-only fixture runtime, never runtime request input
    run_id, candidate, report = pass_rehearsal(service, contract)
    result = service.call("apply_to_demo_source", source_request(run_id, candidate, report))
    assert result["ok"], result
    assert result["data"]["state"] == "APPLIED", result
    assert runtime.writer_count == 1
    replay = service.call("apply_to_demo_source", source_request(run_id, candidate, report))
    assert replay["error_code"] == "SOURCE_APPLY_REPLAY_REJECTED"
    assert runtime.writer_count == 1
    assert call(service, "get_report", run_id=run_id)["report_sha256"] == report["report_sha256"]


def test_source_locked_drift_refused_and_backup_before_writer(service_pair, contract):
    service, runtime = service_pair
    service._test_source_apply = True
    run_id, candidate, report = pass_rehearsal(service, contract)
    runtime.backup_available = False
    result = service.call("apply_to_demo_source", source_request(run_id, candidate, report))
    assert result["error_code"] == "BACKUP_UNAVAILABLE"
    assert runtime.writer_count == 0
    runtime.backup_available = True
    with runtime.connection(service.store.get_run(run_id), "source_read") as con:
        con.execute("UPDATE public.customers SET email='drift@example.invalid' WHERE id=1")
    result = service.call("apply_to_demo_source", source_request(run_id, candidate, report))
    assert result["ok"], result
    assert result["data"]["state"] == "STALE", result
    assert result["data"]["transaction"]["outcome"] == "rolled_back"
