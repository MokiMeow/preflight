"""Only owned metadata is discovered; unknown cloud state never grants capacity."""

import json
import time
from uuid import uuid4

import pytest
from test_rds import ACCOUNT, REGION
from test_rds import cloud as cloud_fixture

from preflight.jobs import JobStore, ResourceIntent
from preflight.models import PreflightError

cloud = cloud_fixture


def mapping(identifier, kind, tags):
    return {
        "ResourceARN": f"arn:aws:rds:{REGION}:{ACCOUNT}:{kind}:{identifier}",
        "Tags": [{"Key": k, "Value": v} for k, v in tags.items()],
    }


def snapshot_read(cloud, identifier, tags, **changes):
    value = cloud.snapshot(identifier, **changes)
    cloud.rds.add_response(
        "describe_db_snapshots", {"DBSnapshots": [value]}, {"DBSnapshotIdentifier": identifier}
    )
    cloud.tags(value["DBSnapshotArn"], tags)


def test_inventory_pages_fresh_safe_ids_and_unknown_doctor(cloud):
    tags = {"Project": "Preflight", "Owner": cloud.policy.owner, "RunId": str(uuid4())}
    cloud.inventory(
        [mapping(cloud.intent.snapshot_id, "snapshot", cloud.intent.tags())], next_token="page2"
    )
    cloud.inventory([mapping("preflight-unknown-snap", "snapshot", tags)], token="page2")
    snapshot_read(cloud, cloud.intent.snapshot_id, cloud.intent.tags())
    snapshot_read(cloud, "preflight-unknown-snap", tags, Status="creating")
    result = cloud.adapter.owned_resource_inventory()
    assert result["counts"] == {"clone": 0, "snapshot": 2}
    assert result["unknown_owned_ids"] == ["preflight-unknown-snap"]
    assert result["resources"][1]["tracked"] is False
    assert result["complete"] is True
    assert "Endpoint" not in json.dumps(result)
    assert "KmsKeyId" not in json.dumps(result)
    assert "arn:" not in json.dumps(result)
    assert "Password" not in json.dumps(result)


def test_new_database_cannot_create_with_unknown_owned_snapshot_below_cap(cloud):
    cloud.adapter.store = JobStore(cloud.store.path + ".new")
    cloud.adapter.store.enqueue(
        uuid4(), cloud.intent, deadline=time.time() + 600, max_clones=1, max_snapshots=3
    )
    cloud.source()
    cloud.absent_snapshot()
    tags = {"Project": "Preflight", "Owner": cloud.policy.owner, "RunId": str(uuid4())}
    cloud.inventory([mapping("preflight-prior-snap", "snapshot", tags)])
    snapshot_read(cloud, "preflight-prior-snap", tags)
    with pytest.raises(PreflightError, match="AWS_OWNED_RESOURCES_UNTRACKED"):
        cloud.adapter.ensure_snapshot(cloud.intent)


def test_unknown_owned_clone_refuses_restore(cloud):
    cloud.snap_read()
    cloud.source()
    cloud.absent_clone()
    tags = {"Project": "Preflight", "Owner": cloud.policy.owner, "RunId": str(uuid4())}
    value = cloud.instance(
        True,
        DBInstanceIdentifier="preflight-prior-clone",
        DBInstanceArn=f"arn:aws:rds:{REGION}:{ACCOUNT}:db:preflight-prior-clone",
    )
    cloud.inventory([mapping("preflight-prior-clone", "db", tags)])
    cloud.rds.add_response(
        "describe_db_instances",
        {"DBInstances": [value]},
        {"DBInstanceIdentifier": "preflight-prior-clone"},
    )
    cloud.tags(value["DBInstanceArn"], tags)
    with pytest.raises(PreflightError, match="AWS_OWNED_RESOURCES_UNTRACKED"):
        cloud.adapter.ensure_clone(cloud.intent)


def test_snapshot_notfound_but_inventory_present_reconcile_no_create(cloud):
    cloud.source()
    cloud.absent_snapshot()
    cloud.inventory([mapping(cloud.intent.snapshot_id, "snapshot", cloud.intent.tags())])
    snapshot_read(cloud, cloud.intent.snapshot_id, cloud.intent.tags(), Status="creating")
    with pytest.raises(PreflightError, match="AWS_RETRYABLE"):
        cloud.adapter.ensure_snapshot(cloud.intent)


def test_stale_tag_index_absence_not_counted_or_adopted(cloud):
    tags = {"Project": "Preflight", "Owner": cloud.policy.owner}
    cloud.inventory([mapping("preflight-deleted-snap", "snapshot", tags)])
    cloud.rds.add_client_error(
        "describe_db_snapshots",
        "DBSnapshotNotFound",
        expected_params={"DBSnapshotIdentifier": "preflight-deleted-snap"},
    )
    assert cloud.adapter.owned_resource_inventory()["counts"] == {"clone": 0, "snapshot": 0}


def test_incomplete_or_cyclic_pagination_refuses(cloud):
    cloud.inventory(next_token="repeat")
    cloud.inventory(token="repeat", next_token="repeat")
    with pytest.raises(PreflightError, match="AWS_INVENTORY_INCOMPLETE"):
        cloud.adapter.owned_resource_inventory()


def test_cross_account_mapping_never_described(cloud):
    tags = {"Project": "Preflight", "Owner": cloud.policy.owner}
    item = mapping("preflight-other-snap", "snapshot", tags)
    item["ResourceARN"] = item["ResourceARN"].replace(ACCOUNT, "999999999999")
    cloud.inventory([item])
    with pytest.raises(PreflightError, match="AWS_RESOURCE_IDENTITY_MISMATCH"):
        cloud.adapter.owned_resource_inventory()


def test_released_reservation_live_resource_refuses_creation(cloud):
    old = cloud.intent
    cloud.store.update(old.run_id, phase="AVAILABLE", aws_status="available")
    cloud.store.release_reservation(old, clone_absent=True, snapshot_absent=True)
    new = ResourceIntent.for_run(uuid4(), cloud.policy.owner, old.expires_at)
    cloud.store.enqueue(uuid4(), new, deadline=time.time() + 600, max_clones=1, max_snapshots=3)
    cloud.intent = new
    cloud.source()
    cloud.absent_snapshot()
    cloud.inventory([mapping(old.snapshot_id, "snapshot", old.tags())])
    snapshot_read(cloud, old.snapshot_id, old.tags())
    with pytest.raises(PreflightError, match="AWS_RESOURCE_RESERVATION_LOST"):
        cloud.adapter.ensure_snapshot(new)


def test_missing_tagging_client_refuses_creation(cloud):
    cloud.adapter.tagging = None
    cloud.source()
    cloud.absent_snapshot()
    with pytest.raises(PreflightError, match="AWS_INVENTORY_CLIENT_REQUIRED"):
        cloud.adapter.ensure_snapshot(cloud.intent)


def test_read_only_cleanup_keeps_retained_snapshot_reservation_for_new_run(cloud):
    old = cloud.intent
    cloud.store.update(old.run_id, phase="AVAILABLE", aws_status="available")
    cloud.source()
    cloud.absent_clone()
    cloud.snap_read()
    assert cloud.adapter.observe_cleanup(old) == {"clone": "ABSENT", "snapshot": "AVAILABLE"}
    new = ResourceIntent.for_run(uuid4(), cloud.policy.owner, old.expires_at)
    cloud.store.enqueue(uuid4(), new, deadline=time.time() + 600, max_clones=1, max_snapshots=3)
    rows = cloud.store.resource_registry()
    assert sum(row["clone_reserved"] for row in rows) == 1
    assert sum(row["snapshot_reserved"] for row in rows) == 2
    assert cloud.store.get(old.run_id)["snapshot_reserved"] == 1


def test_expired_job_retains_counts_does_not_delete(cloud):
    cloud.store.update(
        cloud.intent.run_id,
        phase="ERROR",
        aws_status="creating",
        error_code="CLOUD_DEADLINE_EXCEEDED",
    )
    row = cloud.store.get(cloud.intent.run_id)
    assert row["clone_reserved"] == 1 and row["snapshot_reserved"] == 1
    with pytest.raises(PreflightError, match="RESOURCE_CAP_REACHED"):
        cloud.store.enqueue(
            uuid4(),
            ResourceIntent.for_run(uuid4(), cloud.policy.owner, cloud.intent.expires_at),
            deadline=time.time() + 600,
            max_clones=1,
            max_snapshots=3,
        )
