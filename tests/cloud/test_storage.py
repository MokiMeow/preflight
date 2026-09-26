import pytest

from preflight.models import PreflightError
from tests.cloud.test_rds import cloud as cloud_fixture

cloud = cloud_fixture


@pytest.mark.parametrize("clone", [False, True])
@pytest.mark.parametrize(
    "mode,code",
    [("standard", "AWS_STORAGE_TYPE_UNSUPPORTED"), ("gp2", "AWS_STORAGE_POLICY_MISMATCH")],
)
def test_unsupported_or_unapproved_storage_refused(cloud, clone, mode, code):
    cloud.identity()
    value = cloud.instance(clone, StorageType=mode)
    cloud.rds.add_response(
        "describe_db_instances",
        {"DBInstances": [value]},
        {"DBInstanceIdentifier": value["DBInstanceIdentifier"]},
    )
    with pytest.raises(PreflightError, match=code):
        (cloud.adapter.inspect_clone(cloud.intent) if clone else cloud.adapter.inspect_source())


def test_snapshot_magnetic_storage_refused(cloud):
    cloud.identity()
    cloud.rds.add_response(
        "describe_db_snapshots",
        {"DBSnapshots": [cloud.snapshot(StorageType="standard")]},
        {"DBSnapshotIdentifier": cloud.intent.snapshot_id},
    )
    with pytest.raises(PreflightError, match="AWS_STORAGE_TYPE_UNSUPPORTED"):
        cloud.adapter.inspect_snapshot(cloud.intent)


def test_source_observation_records_real_mode(cloud):
    cloud.source()
    assert cloud.adapter.inspect_source().storage_type == "gp3"
