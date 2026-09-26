"""Real shared SQLite/job races and disposable PG evidence; no AWS or gates."""

import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql

from preflight.artifacts import canonical_json, sha256
from preflight.config import Settings
from preflight.evidence import baseline_matches, capture_evidence
from preflight.jobs import JobStore, ResourceIntent
from preflight.models import PreflightError
from preflight.offline import verify_report
from preflight.runtime import AwsRuntime
from preflight.service import RehearsalService
from tests.postgres.test_remaining_transaction_boundaries import failed_rehearsal, revision_request
from tests.postgres.test_service import call, pass_rehearsal, register
from tests.postgres.test_service import service_pair as service_pair


class ReservationRuntime(AwsRuntime):
    """Reuse actual resource naming/reservation; never invoke provider creation."""

    def __init__(self, settings):
        super().__init__(settings, None, JobStore(settings.state_dir / "cloud.sqlite"), None)
        self.observed_jobs = []

    def advance_jobs(self, store):
        self.observed_jobs.extend(row["run_id"] for row in store.list_runs())


def test_u06_simultaneous_service_starts_share_active_run_and_job_caps(
    tmp_path, contract, monkeypatch
):
    settings = Settings(
        state_dir=tmp_path,
        evidence_backend="local_postgres_test",
        creation_authorized=True,
        approved_budget_ceiling=10,
        source_instance_id="local-source",
        source_allowlist=["local-source"],
        account_id="123456789012",
        region="ap-south-1",
        max_run_owned_snapshots=1,
    )
    runtimes = [ReservationRuntime(settings) for _ in range(2)]
    services = [RehearsalService(settings, runtime, restart=False) for runtime in runtimes]
    barrier = threading.Barrier(2)
    candidate = register(services[0], "fixtures/good.sql", contract)
    for service in services:
        create = service.store.create_run

        def simultaneous_create(run, create=create):
            barrier.wait(timeout=3)
            return create(run)

        monkeypatch.setattr(service.store, "create_run", simultaneous_create)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(
                pool.map(
                    lambda service: service.call(
                        "start_rehearsal",
                        {
                            "request_id": str(uuid4()),
                            "candidate_id": candidate["candidate_id"],
                            "source_instance_id": "local-source",
                            "database_name": "preflight_demo",
                        },
                    ),
                    services,
                )
            )
        assert sum(r["ok"] for r in responses) == 1
        assert next(r for r in responses if not r["ok"])["error_code"] == "ACTIVE_RUN_LIMIT"
        active = services[0].store.list_runs()
        registry = runtimes[0].jobs.resource_registry()
        assert len(active) == len(registry) == 1
        intent = json.loads(registry[0]["intent"])
        assert intent["run_id"] == active[0]["run_id"]
        assert sum(r["clone_reserved"] for r in registry) == 1
        assert sum(r["snapshot_reserved"] for r in registry) == 1
        assert services[1].store.list_runs() == active
    finally:
        for service in services:
            service.executor.shutdown(wait=True)


def test_u06_simultaneous_job_reservations_enforce_retained_clone_cap(tmp_path):
    stores = [JobStore(tmp_path / "cloud.sqlite") for _ in range(2)]
    barrier = threading.Barrier(2)
    expiry = (datetime.now(UTC) + timedelta(hours=1)).isoformat()

    def reserve(store):
        intent = ResourceIntent.for_run(uuid4(), "unit-owner", expiry)
        barrier.wait(timeout=3)
        try:
            store.enqueue(uuid4(), intent, deadline=time.time() + 60, max_clones=1, max_snapshots=1)
            return intent
        except PreflightError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(reserve, stores))
    winners = [r for r in results if isinstance(r, ResourceIntent)]
    assert len(winners) == 1 and "REHEARSAL_ACTIVE" in results
    registry = stores[0].resource_registry()
    assert (
        len(registry) == 1
        and registry[0]["clone_reserved"] == registry[0]["snapshot_reserved"] == 1
    )
    stores[0].update(winners[0].run_id, phase="AVAILABLE", aws_status="available")
    with pytest.raises(PreflightError, match="RESOURCE_CAP_REACHED"):
        stores[1].enqueue(
            uuid4(),
            ResourceIntent.for_run(uuid4(), "unit-owner", expiry),
            deadline=time.time() + 60,
            max_clones=1,
            max_snapshots=1,
        )
    assert stores[1].resource_registry() == registry


def test_u08_same_parent_race_publishes_one_revision_with_unchanged_full_baseline(
    service_pair, contract, monkeypatch
):
    first, runtime = service_pair
    run_id, parent = failed_rehearsal(first, contract)
    second = RehearsalService(first.settings, runtime, restart=False)
    before = first.baselines[run_id]
    with runtime.connection(first.store.get_run(run_id), "clone_read") as con:
        second.baselines[run_id] = capture_evidence(con, contract)
    assert baseline_matches(before, second.baselines[run_id])
    initial = first.store.get_run(run_id)
    barrier = threading.Barrier(2)
    for service in [first, second]:
        publish = service.store.publish_candidate

        def simultaneous_publish(candidate, run=None, publish=publish):
            barrier.wait(timeout=3)
            return publish(candidate, run)

        monkeypatch.setattr(service.store, "publish_candidate", simultaneous_publish)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(
                pool.map(
                    lambda service: service.call(
                        "register_candidate", revision_request(run_id, parent, contract)
                    ),
                    [first, second],
                )
            )
        assert sum(r["ok"] for r in responses) == 1
        assert next(r for r in responses if not r["ok"])["error_code"] == "STATE_CONFLICT"
        winner = next(r["data"] for r in responses if r["ok"])
        current = first.store.get_run(run_id)
        assert current["phase"] == "BASELINED"
        assert current["candidate_id"] == winner["candidate_id"]
        assert current["revision"] == initial["revision"] + 1
        published = first.store.list_records("candidate")
        assert len(published) == 2
        assert sum(c["parent_candidate_id"] == parent["candidate_id"] for c in published) == 1
        with first.store.transaction() as con:
            assert (
                con.execute(
                    "SELECT count(*) FROM events WHERE run_id=? AND code='CANDIDATE_ATTACHED'",
                    (run_id,),
                ).fetchone()[0]
                == 1
            )
        with runtime.connection(current, "clone_read") as con:
            assert baseline_matches(before, capture_evidence(con, contract))
        assert runtime.writer_count == 0
    finally:
        second.executor.shutdown(wait=True)


def test_c13_actual_local_clone_deletion_retains_anchored_report_and_receipt(
    service_pair, contract, monkeypatch
):
    service, runtime = service_pair
    run_id, candidate, report = pass_rehearsal(service, contract)
    report_path = f"reports/{run_id}/{candidate['candidate_id']}.json"
    original_report = service.artifacts.read(report_path)
    trusted_report_digest = report["report_sha256"]
    admin = psycopg.connect(
        host="127.0.0.1",
        port=os.environ["PREFLIGHT_TEST_PG_PORT"],
        dbname="postgres",
        user="postgres",
        autocommit=True,
        connect_timeout=5,
    )
    deleted = False

    def cleanup(run, request, source_apply_attempted):
        nonlocal deleted
        assert request.delete_clone and not request.delete_snapshot and not source_apply_attempted
        admin.execute(
            sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(runtime.clone))
        )
        deleted = True
        assert (
            admin.execute(
                "SELECT 1 FROM pg_catalog.pg_database WHERE datname=%s", (runtime.clone,)
            ).fetchone()
            is None
        )
        return {
            "actions": {"clone": "ABSENT", "snapshot": "RETAINED"},
            "cleanup_state": "CLONE_DELETED",
        }

    monkeypatch.setattr(runtime, "cleanup", cleanup, raising=False)
    try:
        receipt = call(service, "cleanup_run", run_id=run_id, delete_clone=True)
        assert deleted and receipt["cleanup_state"] == "CLONE_DELETED"
        receipt_path = f"reports/{run_id}/{receipt['receipt_id']}.receipt.json"
        receipt_bytes = service.artifacts.read(receipt_path)
        trusted_receipt_digest = sha256(receipt_bytes)
        assert receipt_bytes == canonical_json(service.store.get("receipt", receipt["receipt_id"]))
        assert service.artifacts.read(receipt_path, trusted_receipt_digest) == receipt_bytes
        assert service.artifacts.read(report_path) == original_report
        verified = verify_report(original_report, trusted_report_digest)
        assert verified["anchor_status"] == "EXPECTED_DIGEST_MATCH"
        assert verified["current_apply_eligibility"] == "NOT_EVALUATED"
        assert call(service, "get_report", run_id=run_id)["report_sha256"] == trusted_report_digest
        assert call(service, "get_run", run_id=run_id)["apply_eligible_now"] is False
        assert runtime.writer_count == 0
    finally:
        # Restore only an empty disposable clone database for the owning fixture's teardown.
        if deleted:
            admin.execute(
                sql.SQL("CREATE DATABASE {} OWNER preflight_test_owner").format(
                    sql.Identifier(runtime.clone)
                )
            )
        admin.close()
