import time
from dataclasses import replace
from uuid import uuid4

import pytest

from preflight.aws_rds import ResourceObservation
from preflight.jobs import JobStore, ResourceIntent, tick_job
from preflight.models import PreflightError


def enqueue(store, request=None, intent=None):
    intent = intent or ResourceIntent.for_run(uuid4(), "owner", "2026-09-28T00:00:00Z")
    request = request or uuid4()
    return (
        store.enqueue(request, intent, deadline=time.time() + 600, max_clones=1, max_snapshots=3),
        intent,
        request,
    )


def test_restart_durable_request_and_caps(tmp_path):
    path = tmp_path / "cloud.sqlite"
    row, intent, request = enqueue(JobStore(path))
    store = JobStore(path)
    assert enqueue(store, request, intent)[0]["run_id"] == row["run_id"]
    with pytest.raises(PreflightError, match="REQUEST_ID_CONFLICT"):
        enqueue(store, request, replace(intent, owner="other"))
    store.update(intent.run_id, phase="ERROR", aws_status="creating")
    with pytest.raises(PreflightError, match="RESOURCE_CAP_REACHED"):
        enqueue(store)
    assert store.get(intent.run_id)["clone_reserved"] == 1


def test_single_mutation_lease(tmp_path):
    first = JobStore(tmp_path / "cloud.sqlite")
    second = JobStore(tmp_path / "cloud.sqlite")
    with (
        first.mutation_lease("run-one"),
        pytest.raises(PreflightError, match="CLOUD_MUTATION_BUSY"),
        second.mutation_lease("run-two"),
    ):
        pytest.fail("second lease admitted")
    with second.mutation_lease("run-two"):
        pass


class UnitAdapter:
    """Pure job scheduling fixture; not an RDS backend or migration runner."""

    def __init__(self):
        self.snapshot_calls = 0
        self.clone_calls = 0

    def ensure_snapshot(self, intent):
        self.snapshot_calls += 1
        return ResourceObservation(intent.snapshot_id, "unit-fixture", "available", "18.1")

    def ensure_clone(self, intent):
        self.clone_calls += 1
        return ResourceObservation(intent.clone_instance_id, "unit-fixture", "available", "18.1")


def test_tick_available_is_not_database_ready_and_poll_is_read_only(tmp_path):
    path = tmp_path / "cloud.sqlite"
    store = JobStore(path)
    row, intent, _ = enqueue(store)
    adapter = UnitAdapter()
    now = time.time()
    row = tick_job(store, adapter, intent.run_id, now=now)
    assert row["phase"] == "RESTORING"
    assert tick_job(store, adapter, intent.run_id, now=now)["phase"] == "RESTORING"
    assert adapter.clone_calls == 0
    row = tick_job(JobStore(path), adapter, intent.run_id, now=now + 5)
    assert row["phase"] == "AVAILABLE"
    assert row["phase"] != "READY"
    assert adapter.clone_calls == 1
    tick_job(store, adapter, intent.run_id, now=now + 10)
    assert adapter.clone_calls == 1


@pytest.mark.parametrize("code", ["AWS_RETRYABLE", "AWS_OUTCOME_UNCERTAIN"])
def test_ambiguous_or_throttled_keep_same_intent(tmp_path, code):
    store = JobStore(tmp_path / "cloud.sqlite")
    row, intent, _ = enqueue(store)

    class Denied:
        def ensure_snapshot(self, same):
            assert same == intent
            raise PreflightError(code)

    now = time.time()
    result = tick_job(store, Denied(), intent.run_id, now=now)
    assert result["phase"] == "SNAPSHOTTING"
    assert result["error_code"] == code
    assert result["intent"] == row["intent"]
    assert result["next_poll"] > now
    expired = tick_job(store, Denied(), intent.run_id, now=row["deadline"] + 1)
    assert expired["phase"] == "ERROR"
    assert expired["intent"] == row["intent"]
    assert expired["error_code"] == "CLOUD_DEADLINE_EXCEEDED"


def test_job_failure_retains_exact_cleanup_names(tmp_path):
    store = JobStore(tmp_path / "cloud.sqlite")
    row, intent, _ = enqueue(store)

    class Denied:
        def ensure_snapshot(self, same):
            raise PreflightError("AWS_REQUEST_DENIED")

    result = tick_job(store, Denied(), intent.run_id)
    assert result["phase"] == "ERROR"
    assert result["intent"] == row["intent"]
