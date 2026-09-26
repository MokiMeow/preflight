import pytest
from test_rds import cloud as cloud_fixture

from preflight.aws_rds import CleanupPolicy
from preflight.models import PreflightError

cloud = cloud_fixture


def test_snapshot_deletion_exact_owned_resource(cloud):
    cloud.source()
    cloud.snap_read()
    cloud.identity()
    cloud.rds.add_response(
        "delete_db_snapshot",
        {"DBSnapshot": cloud.snapshot(Status="deleting")},
        {"DBSnapshotIdentifier": cloud.intent.snapshot_id},
    )
    selected = CleanupPolicy(
        True, "PASS", True, delete_snapshot=True, snapshot_id=cloud.intent.snapshot_id
    )
    assert cloud.adapter.cleanup(cloud.intent, selected) == {"snapshot": "DELETING"}


def test_lost_snapshot_response_reconciles_no_duplicate(cloud, monkeypatch):
    from botocore.exceptions import EndpointConnectionError

    cloud.source()
    cloud.absent_snapshot()
    cloud.identity()
    calls = []

    def uncertain(**kwargs):
        calls.append(kwargs)
        raise EndpointConnectionError(endpoint_url="https://unit-fixture.invalid")

    monkeypatch.setattr(cloud.adapter.rds, "create_db_snapshot", uncertain)
    with pytest.raises(PreflightError, match="AWS_OUTCOME_UNCERTAIN"):
        cloud.adapter.ensure_snapshot(cloud.intent)
    cloud.source()
    cloud.snap_read()
    assert cloud.adapter.ensure_snapshot(cloud.intent).status == "available"
    assert len(calls) == 1


def test_throttle_is_sanitized_retryable(cloud):
    cloud.identity()
    cloud.rds.add_client_error(
        "describe_db_instances",
        "ThrottlingException",
        "secret-password-raw-row",
        expected_params={"DBInstanceIdentifier": cloud.policy.source_instance_id},
    )
    with pytest.raises(PreflightError, match="AWS_RETRYABLE"):
        cloud.adapter.inspect_source()


def test_cleanup_observation_frees_only_proven_absence(cloud):
    cloud.source()
    cloud.absent_clone()
    cloud.snap_read(Status="deleting")
    assert cloud.adapter.observe_cleanup(cloud.intent) == {
        "clone": "ABSENT",
        "snapshot": "DELETING",
    }
    row = cloud.store.get(cloud.intent.run_id)
    assert row["clone_reserved"] == 0
    assert row["snapshot_reserved"] == 1
    with pytest.raises(PreflightError, match="RESOURCE_NOT_RESERVED"):
        cloud.adapter.ensure_clone(cloud.intent)
    cloud.source()
    cloud.absent_clone()
    cloud.absent_snapshot()
    assert cloud.adapter.observe_cleanup(cloud.intent) == {"clone": "ABSENT", "snapshot": "ABSENT"}
    assert cloud.store.get(cloud.intent.run_id)["snapshot_reserved"] == 0


def test_missing_source_is_not_absent_clone(cloud):
    cloud.identity()
    cloud.rds.add_client_error(
        "describe_db_instances",
        "DBInstanceNotFound",
        expected_params={"DBInstanceIdentifier": cloud.policy.source_instance_id},
    )
    with pytest.raises(PreflightError, match="AWS_SOURCE_ABSENT"):
        cloud.adapter.observe_cleanup(cloud.intent)
    assert cloud.store.get(cloud.intent.run_id)["clone_reserved"] == 1
