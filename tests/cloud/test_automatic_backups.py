"""AWS automatic source backups are observations, never disposable run capacity."""

import pytest

from preflight.models import PreflightError
from tests.cloud.test_inventory import mapping, snapshot_read
from tests.cloud.test_rds import ACCOUNT, REGION
from tests.cloud.test_rds import cloud as cloud


def automatic(cloud, **changes):
    identifier = "rds:" + cloud.policy.source_instance_id + "-2026-09-26-08-09"
    tags = {"Project": "Preflight", "Owner": cloud.policy.owner}
    value = cloud.snapshot(identifier, SnapshotType="automated")
    value["TagList"] = [{"Key": k, "Value": v} for k, v in tags.items()]
    value.update(changes)
    return identifier, tags, value


def describe(cloud, identifier, value):
    cloud.rds.add_response(
        "describe_db_snapshots",
        {"DBSnapshots": [value]},
        {"DBSnapshotIdentifier": identifier, "SnapshotType": "automated"},
    )


def test_automatic_source_backup_separate_from_disposable_inventory(cloud):
    identifier, tags, value = automatic(cloud)
    cloud.inventory([mapping(identifier, "snapshot", tags)])
    describe(cloud, identifier, value)
    result = cloud.adapter.owned_resource_inventory()
    assert result["counts"] == {"clone": 0, "snapshot": 0}
    assert result["unknown_owned_ids"] == []
    assert result["resources"] == []
    assert result["automatic_source_backups"] == [
        {
            "resource_id": identifier,
            "kind": "source_automatic_backup",
            "status": "available",
            "managed_by": "aws_rds",
        }
    ]


@pytest.mark.parametrize(
    "mutation", ["source", "type", "identity", "owner", "missing_tags", "run_tag", "encryption"]
)
def test_automatic_source_backup_fresh_boundary_checks(cloud, mutation):
    identifier, tags, value = automatic(cloud)
    if mutation == "source":
        value["DBInstanceIdentifier"] = "another-source"
    elif mutation == "type":
        value["SnapshotType"] = "manual"
    elif mutation == "identity":
        value["DBSnapshotArn"] += "-wrong"
    elif mutation == "owner":
        value["TagList"][1]["Value"] = "another-owner"
    elif mutation == "missing_tags":
        value.pop("TagList")
    elif mutation == "run_tag":
        value["TagList"].append({"Key": "RunId", "Value": "untracked"})
    else:
        value["Encrypted"] = False
    cloud.inventory([mapping(identifier, "snapshot", tags)])
    describe(cloud, identifier, value)
    with pytest.raises(PreflightError):
        cloud.adapter.owned_resource_inventory()


def test_other_source_automatic_identifier_refused_before_describe(cloud):
    _, tags, _ = automatic(cloud)
    cloud.inventory([mapping("rds:other-source-2026-09-26-08-09", "snapshot", tags)])
    with pytest.raises(PreflightError, match="AWS_INVENTORY_RESOURCE_INVALID"):
        cloud.adapter.owned_resource_inventory()


def test_unknown_manual_resource_still_blocks_with_automatic_backup(cloud):
    identifier, tags, value = automatic(cloud)
    cloud.source()
    cloud.absent_snapshot()
    cloud.inventory(
        [mapping(identifier, "snapshot", tags), mapping("untracked-manual", "snapshot", tags)]
    )
    describe(cloud, identifier, value)
    snapshot_read(cloud, "untracked-manual", tags)
    with pytest.raises(PreflightError, match="AWS_OWNED_RESOURCES_UNTRACKED"):
        cloud.adapter.ensure_snapshot(cloud.intent)


def test_unknown_clone_still_blocks_with_automatic_backup(cloud):
    identifier, tags, value = automatic(cloud)
    cloud.snap_read()
    cloud.source()
    cloud.absent_clone()
    clone_id = "preflight-untracked-clone"
    clone = cloud.instance(
        True,
        DBInstanceIdentifier=clone_id,
        DBInstanceArn=f"arn:aws:rds:{REGION}:{ACCOUNT}:db:{clone_id}",
    )
    cloud.inventory([mapping(identifier, "snapshot", tags), mapping(clone_id, "db", tags)])
    describe(cloud, identifier, value)
    cloud.rds.add_response(
        "describe_db_instances", {"DBInstances": [clone]}, {"DBInstanceIdentifier": clone_id}
    )
    cloud.tags(clone["DBInstanceArn"], tags)
    with pytest.raises(PreflightError, match="AWS_OWNED_RESOURCES_UNTRACKED"):
        cloud.adapter.ensure_clone(cloud.intent)


def test_automatic_backup_does_not_exempt_tracked_manual_capacity(cloud):
    identifier, tags, value = automatic(cloud)
    cloud.inventory(
        [
            mapping(identifier, "snapshot", tags),
            mapping(cloud.intent.snapshot_id, "snapshot", cloud.intent.tags()),
        ]
    )
    describe(cloud, identifier, value)
    snapshot_read(cloud, cloud.intent.snapshot_id, cloud.intent.tags())
    result = cloud.adapter.owned_resource_inventory()
    assert result["counts"]["snapshot"] == 1
    assert result["resources"][0]["resource_id"] == cloud.intent.snapshot_id
    assert result["resources"][0]["tracked"] is True
    assert len(result["automatic_source_backups"]) == 1
