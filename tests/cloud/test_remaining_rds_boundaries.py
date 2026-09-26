"""Fault and deletion simulations against exact boto clients; no live AWS claims."""

import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest
from botocore.exceptions import ReadTimeoutError

from preflight.aws_rds import RdsAdapter
from preflight.jobs import JobStore
from preflight.models import PreflightError
from tests.cloud.test_rds import cleanup
from tests.cloud.test_rds import cloud as cloud


def test_lost_restore_ack_reopened_adapter_describes_exact_clone_without_second_restore(
    cloud, monkeypatch
):
    submitted = []

    def lost_ack(**kwargs):
        assert kwargs["DBInstanceIdentifier"] == cloud.intent.clone_instance_id
        assert kwargs["DBSnapshotIdentifier"] == cloud.intent.snapshot_id
        submitted.append(kwargs)
        raise ReadTimeoutError(endpoint_url="https://synthetic-rds.invalid")

    monkeypatch.setattr(cloud.adapter.rds, "restore_db_instance_from_db_snapshot", lost_ack)
    cloud.snap_read()
    cloud.source()
    cloud.absent_clone()
    cloud.inventory()
    cloud.identity()
    with pytest.raises(PreflightError, match="AWS_OUTCOME_UNCERTAIN"):
        cloud.adapter.ensure_clone(cloud.intent)
    restarted = RdsAdapter(
        cloud.adapter.rds,
        cloud.adapter.sts,
        cloud.policy,
        JobStore(cloud.store.path),
        tagging=cloud.adapter.tagging,
    )
    cloud.snap_read()
    cloud.source()
    cloud.clone_read(DBInstanceStatus="creating")
    observation = restarted.ensure_clone(cloud.intent)
    assert observation.resource_id == cloud.intent.clone_instance_id
    assert observation.status == "creating"
    assert len(submitted) == 1


@pytest.mark.parametrize("kind", ["clone", "snapshot"])
@pytest.mark.parametrize("mutation", ["missing_run_id", "wrong_owner", "wrong_arn"])
def test_cleanup_collision_fresh_identity_tags_refuse_before_any_delete(cloud, kind, mutation):
    cloud.source()
    cloud.identity()
    value = cloud.instance(True) if kind == "clone" else cloud.snapshot()
    arn_key = "DBInstanceArn" if kind == "clone" else "DBSnapshotArn"
    if mutation == "wrong_arn":
        value[arn_key] += "-another-run"
    method = "describe_db_instances" if kind == "clone" else "describe_db_snapshots"
    response_key = "DBInstances" if kind == "clone" else "DBSnapshots"
    identifier_key = "DBInstanceIdentifier" if kind == "clone" else "DBSnapshotIdentifier"
    identifier = cloud.intent.clone_instance_id if kind == "clone" else cloud.intent.snapshot_id
    cloud.rds.add_response(method, {response_key: [value]}, {identifier_key: identifier})
    if mutation != "wrong_arn":
        tags = cloud.intent.tags()
        if mutation == "missing_run_id":
            tags.pop("RunId")
        else:
            tags["Owner"] = "another-owner"
        cloud.tags(value[arn_key], tags)
    selection = (
        cleanup(cloud)
        if kind == "clone"
        else replace(
            cleanup(cloud),
            delete_clone=False,
            clone_instance_id=None,
            delete_snapshot=True,
            snapshot_id=cloud.intent.snapshot_id,
        )
    )
    with pytest.raises(PreflightError, match="AWS_RESOURCE_(IDENTITY|TAG)_MISMATCH"):
        cloud.adapter.cleanup(cloud.intent, selection)
    # Stubber has no deletion response. Any delete would fail instead of this
    # exact refusal; reservations remain held until real absence is observed.
    row = cloud.store.get(cloud.intent.run_id)
    assert row["clone_reserved"] == row["snapshot_reserved"] == 1


def test_distinct_processes_resume_pending_job_with_same_resource_identity(cloud):
    script = """
import json,sys,time
from preflight.aws_rds import ResourceObservation
from preflight.jobs import JobStore,tick_job
store=JobStore(sys.argv[1]);run_id=sys.argv[2];stage=sys.argv[3];calls=[]
class Adapter:
 def ensure_snapshot(self,intent):
  calls.append(['snapshot',intent.snapshot_id])
  return ResourceObservation(intent.snapshot_id,'unit-fixture',
   'creating' if stage=='snapshot-pending' else 'available','18.1')
 def ensure_clone(self,intent):
  calls.append(['clone',intent.clone_instance_id])
  return ResourceObservation(intent.clone_instance_id,'unit-fixture',
   'creating' if stage=='clone-pending' else 'available','18.1')
before=store.get(run_id)
row=tick_job(store,Adapter(),run_id,now=max(time.time(),before['next_poll']+1))
print(json.dumps({'phase':row['phase'],'intent':json.loads(row['intent']),'calls':calls}))
"""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2] / "src")
    original = json.loads(cloud.store.get(cloud.intent.run_id)["intent"])
    for stage, phase, kind in (
        ("snapshot-pending", "SNAPSHOTTING", "snapshot"),
        ("snapshot-ready", "RESTORING", "snapshot"),
        ("clone-pending", "RESTORING", "clone"),
        ("clone-ready", "AVAILABLE", "clone"),
        ("terminal-restart", "AVAILABLE", None),
    ):
        result = subprocess.run(
            [sys.executable, "-c", script, cloud.store.path, cloud.intent.run_id, stage],
            capture_output=True,
            text=True,
            env=env,
            timeout=15,
        )
        assert result.returncode == 0, result.stderr
        observation = json.loads(result.stdout)
        assert observation["phase"] == phase
        assert observation["intent"] == original
        expected_id = (
            cloud.intent.snapshot_id if kind == "snapshot" else cloud.intent.clone_instance_id
        )
        assert observation["calls"] == ([[kind, expected_id]] if kind else [])
