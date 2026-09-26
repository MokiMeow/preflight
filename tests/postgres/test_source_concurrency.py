"""Actual disposable PG source races and outcome faults; no human approval proof."""

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from uuid import uuid4

import psycopg

from tests.postgres.test_service import pass_rehearsal, source_request
from tests.postgres.test_service import service_pair as service_pair


def test_two_concurrent_source_requests_accept_exactly_one(service_pair, contract):
    service, runtime = service_pair
    service._test_source_apply = True
    run_id, candidate, report = pass_rehearsal(service, contract)
    barrier = threading.Barrier(2)

    def apply():
        barrier.wait(timeout=5)
        return service.call("apply_to_demo_source", source_request(run_id, candidate, report))

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(apply) for _ in range(2)]
        results = [future.result(timeout=20) for future in futures]
    assert sum(result["ok"] for result in results) == 1, results
    assert (
        next(result for result in results if not result["ok"])["error_code"]
        == "SOURCE_APPLY_REPLAY_REJECTED"
    )
    assert runtime.writer_count == 1
    assert service.store.get_run(run_id)["phase"] == "APPLIED"


def test_writer_committed_before_source_locks_is_detected(service_pair, contract):
    service, runtime = service_pair
    service._test_source_apply = True
    run_id, candidate, report = pass_rehearsal(service, contract)
    with runtime.connection(service.store.get_run(run_id), "source_read") as writer:
        writer.execute("BEGIN")
        writer.execute("UPDATE public.customers SET email='race@example.invalid' WHERE id=1")
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(
                service.call, "apply_to_demo_source", source_request(run_id, candidate, report)
            )
            deadline = time.monotonic() + 5
            while runtime.writer_count == 0 and time.monotonic() < deadline:
                time.sleep(0.01)
            assert runtime.writer_count == 1
            writer.execute("COMMIT")
            result = future.result(timeout=20)
    assert result["ok"], result
    assert result["data"]["state"] == "STALE"
    assert result["data"]["precheck_status"] == "DRIFT"
    assert result["data"]["transaction"]["outcome"] == "rolled_back"
    with runtime.connection(service.store.get_run(run_id), "source_read") as con:
        assert (
            con.execute(
                "SELECT count(*) FROM information_schema.columns WHERE table_schema='public' AND table_name='customers' AND column_name='account_tier'"
            ).fetchone()[0]
            == 0
        )


def test_writer_after_source_locks_waits_until_transaction_finishes(
    service_pair, contract, monkeypatch
):
    from preflight import evidence

    service, runtime = service_pair
    service._test_source_apply = True
    run_id, candidate, report = pass_rehearsal(service, contract)
    original = evidence.capture_evidence
    observed = threading.Event()
    completed = threading.Event()
    run = service.store.get_run(run_id)
    with (
        runtime.connection(run, "source_read") as writer,
        ThreadPoolExecutor(max_workers=1) as pool,
    ):
        future = None

        def write():
            writer.execute("UPDATE public.customers SET email='later@example.invalid' WHERE id=1")
            completed.set()

        def capture(con, *args, **kwargs):
            nonlocal future
            if (
                con.info.dbname == runtime.source
                and kwargs.get("in_transaction")
                and not observed.is_set()
            ):
                future = pool.submit(write)
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    waiting = con.execute(
                        "SELECT wait_event_type FROM pg_catalog.pg_stat_activity WHERE pid=%s",
                        (writer.info.backend_pid,),
                    ).fetchone()
                    if waiting and waiting[0] == "Lock":
                        break
                    time.sleep(0.01)
                else:
                    raise AssertionError("Competing writer did not wait on actual PG lock")
                assert not completed.is_set()
                observed.set()
            return original(con, *args, **kwargs)

        monkeypatch.setattr(evidence, "capture_evidence", capture)
        result = service.call("apply_to_demo_source", source_request(run_id, candidate, report))
        assert future is not None
        future.result(timeout=10)
    assert observed.is_set() and completed.is_set()
    assert result["ok"], result
    assert result["data"]["precheck_status"] == "MATCH"
    assert result["data"]["transaction"]["outcome"] == "committed"
    # Writes after commit are outside historical proof; confirmation may detect them.
    assert result["data"]["state"] in {"APPLIED", "APPLIED_NEEDS_ATTENTION"}


def test_source_postcommit_confirmation_failure_never_retries(service_pair, contract, monkeypatch):
    service, runtime = service_pair
    service._test_source_apply = True
    run_id, candidate, report = pass_rehearsal(service, contract)
    original = runtime.connection

    @contextmanager
    def connection(run, mode):
        if mode == "source_read":
            raise psycopg.OperationalError("private-confirmation-sentinel")
        with original(run, mode) as con:
            yield con

    monkeypatch.setattr(runtime, "connection", connection)
    result = service.call("apply_to_demo_source", source_request(run_id, candidate, report))
    assert result["ok"] and result["data"]["state"] == "APPLIED_NEEDS_ATTENTION", result
    assert result["data"]["transaction"]["outcome"] == "committed"
    assert "private-confirmation-sentinel" not in str(result)
    replay = service.call("apply_to_demo_source", source_request(run_id, candidate, report))
    assert replay["error_code"] == "SOURCE_APPLY_REPLAY_REJECTED"
    assert runtime.writer_count == 1


def test_source_lost_commit_acknowledgement_remains_unknown(service_pair, contract, monkeypatch):
    service, runtime = service_pair
    service._test_source_apply = True
    run_id, candidate, report = pass_rehearsal(service, contract)
    original = runtime.connection

    class Cursor:
        def __init__(self, real):
            self.real = real

        def __getattr__(self, name):
            return getattr(self.real, name)

        def execute(self, query, *args, **kwargs):
            result = self.real.execute(query, *args, **kwargs)
            if query == "COMMIT":
                raise psycopg.OperationalError("private-commit-sentinel")
            return result

        def __iter__(self):
            return iter(self.real)

        def __enter__(self):
            self.real.__enter__()
            return self

        def __exit__(self, *args):
            return self.real.__exit__(*args)

    class Connection:
        def __init__(self, real):
            self.real = real

        def __getattr__(self, name):
            return getattr(self.real, name)

        def cursor(self, *args, **kwargs):
            return Cursor(self.real.cursor(*args, **kwargs))

    @contextmanager
    def connection(run, mode):
        with original(run, mode) as con:
            yield Connection(con) if mode == "source_write" else con

    monkeypatch.setattr(runtime, "connection", connection)
    result = service.call("apply_to_demo_source", source_request(run_id, candidate, report))
    assert result["ok"] and result["data"]["state"] == "APPLY_OUTCOME_UNKNOWN", result
    assert result["data"]["transaction"]["outcome"] == "unknown"
    assert "private-commit-sentinel" not in str(result)
    replay = service.call("apply_to_demo_source", source_request(run_id, candidate, report))
    assert replay["error_code"] == "SOURCE_APPLY_REPLAY_REJECTED"
    cleanup = service.call(
        "cleanup_run", {"request_id": str(uuid4()), "run_id": run_id, "delete_clone": True}
    )
    assert cleanup["error_code"] == "CLEANUP_UNSAFE_STATE"
    assert runtime.writer_count == 1
    with original(service.store.get_run(run_id), "source_read") as con:
        assert (
            con.execute(
                "SELECT count(*) FROM information_schema.columns WHERE table_schema='public' AND table_name='customers' AND column_name='account_tier'"
            ).fetchone()[0]
            == 1
        )
