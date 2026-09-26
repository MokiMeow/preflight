"""Boto3 request construction and negative boundaries; no connected AWS evidence."""

from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

import boto3
import pytest
from botocore.stub import Stubber

from preflight.aws_rds import CleanupPolicy, CloudPolicy, RdsAdapter
from preflight.jobs import JobStore, ResourceIntent
from preflight.models import PreflightError

ACCOUNT = "123456789012"  # Unit fixture only; not operator authorization.
REGION = "us-east-1"
RUN = UUID("11111111-2222-4333-8444-555555555555")
NOW = datetime(2026, 9, 26, tzinfo=UTC)


@pytest.fixture
def cloud(tmp_path):
    policy = CloudPolicy(
        ACCOUNT,
        REGION,
        "synthetic-source",
        "unit-owner",
        "private-subnets",
        ("sg-0123456789abcdef0",),
        "db.t4g.micro",
        creation_authorized=True,
    )
    intent = ResourceIntent.for_run(RUN, policy.owner, "2026-09-28T00:00:00+00:00")
    store = JobStore(tmp_path / "jobs.sqlite")
    store.enqueue(uuid4(), intent, deadline=4102444800, max_clones=1, max_snapshots=3)
    session = boto3.Session(
        aws_access_key_id="unit-fixture", aws_secret_access_key="unit-fixture", region_name=REGION
    )
    rds, sts = session.client("rds"), session.client("sts")
    rs, ss = Stubber(rds), Stubber(sts)
    rs.activate()
    ss.activate()
    value = Harness(policy, intent, store, RdsAdapter(rds, sts, policy, store), rs, ss)
    yield value
    rs.assert_no_pending_responses()
    ss.assert_no_pending_responses()
    rs.deactivate()
    ss.deactivate()


class Harness:
    def __init__(self, policy, intent, store, adapter, rds, sts):
        self.policy, self.intent, self.store = policy, intent, store
        self.adapter, self.rds, self.sts = adapter, rds, sts

    def identity(self, count=1, account=ACCOUNT):
        for _ in range(count):
            self.sts.add_response(
                "get_caller_identity",
                {"Account": account, "Arn": f"arn:aws:iam::{account}:user/unit", "UserId": "unit"},
                {},
            )

    def instance(self, clone=False, **changes):
        identifier = self.intent.clone_instance_id if clone else self.policy.source_instance_id
        value = {
            "DBInstanceIdentifier": identifier,
            "DBInstanceArn": f"arn:aws:rds:{REGION}:{ACCOUNT}:db:{identifier}",
            "DBInstanceStatus": "available",
            "Engine": "postgres",
            "EngineVersion": "18.1",
            "StorageEncrypted": True,
            "PubliclyAccessible": False,
            "DBSubnetGroup": {"DBSubnetGroupName": self.policy.subnet_group},
            "VpcSecurityGroups": [
                {"VpcSecurityGroupId": s, "Status": "active"}
                for s in self.policy.security_group_ids
            ],
            "DBInstanceClass": self.policy.instance_class,
            "DeletionProtection": False,
            "KmsKeyId": f"arn:aws:kms:{REGION}:{ACCOUNT}:key/unit",
            "Endpoint": {
                "Address": f"{'clone' if clone else 'source'}.unit.{REGION}.rds.amazonaws.com",
                "Port": 5432,
            },
        }
        return value | changes

    def snapshot(self, identifier=None, **changes):
        identifier = identifier or self.intent.snapshot_id
        return {
            "DBSnapshotIdentifier": identifier,
            "DBSnapshotArn": f"arn:aws:rds:{REGION}:{ACCOUNT}:snapshot:{identifier}",
            "DBInstanceIdentifier": self.policy.source_instance_id,
            "Engine": "postgres",
            "EngineVersion": "18.1",
            "Encrypted": True,
            "KmsKeyId": f"arn:aws:kms:{REGION}:{ACCOUNT}:key/unit",
            "Status": "available",
            "SnapshotType": "manual",
            "SnapshotCreateTime": NOW,
        } | changes

    def tags(self, arn, tags):
        self.rds.add_response(
            "list_tags_for_resource",
            {"TagList": [{"Key": k, "Value": v} for k, v in tags.items()]},
            {"ResourceName": arn},
        )

    def source(self, **changes):
        self.identity()
        value = self.instance(**changes)
        self.rds.add_response(
            "describe_db_instances",
            {"DBInstances": [value]},
            {"DBInstanceIdentifier": self.policy.source_instance_id},
        )
        self.tags(
            value["DBInstanceArn"],
            {"Project": "Preflight", "Owner": self.policy.owner, "Purpose": "synthetic-source"},
        )

    def snap_read(self, **changes):
        self.identity()
        value = self.snapshot(**changes)
        self.rds.add_response(
            "describe_db_snapshots",
            {"DBSnapshots": [value]},
            {"DBSnapshotIdentifier": self.intent.snapshot_id},
        )
        self.tags(value["DBSnapshotArn"], self.intent.tags())

    def clone_read(self, **changes):
        self.identity()
        value = self.instance(True, **changes)
        self.rds.add_response(
            "describe_db_instances",
            {"DBInstances": [value]},
            {"DBInstanceIdentifier": self.intent.clone_instance_id},
        )
        self.tags(value["DBInstanceArn"], self.intent.tags())
        self.tags(
            value["DBInstanceArn"], self.intent.tags() | {"SnapshotId": self.intent.snapshot_id}
        )
        self.source()

    def absent_snapshot(self):
        self.identity()
        self.rds.add_client_error(
            "describe_db_snapshots",
            "DBSnapshotNotFound",
            expected_params={"DBSnapshotIdentifier": self.intent.snapshot_id},
        )

    def absent_clone(self):
        self.identity()
        self.rds.add_client_error(
            "describe_db_instances",
            "DBInstanceNotFound",
            expected_params={"DBInstanceIdentifier": self.intent.clone_instance_id},
        )


def cleanup(cloud, **changes):
    return CleanupPolicy(
        True,
        "PASS",
        True,
        delete_clone=True,
        clone_instance_id=cloud.intent.clone_instance_id,
        **changes,
    )


def test_source_exact_owned_private_identity(cloud):
    cloud.source()
    result = cloud.adapter.inspect_source()
    assert result.resource_id == cloud.policy.source_instance_id
    assert result.status == "available"
    assert result.endpoint.endswith("rds.amazonaws.com")


def test_wrong_account_before_resource_call(cloud):
    cloud.identity(account="999999999999")
    with pytest.raises(PreflightError, match="AWS_ACCOUNT_MISMATCH"):
        cloud.adapter.inspect_source()


@pytest.mark.parametrize(
    "changes,code",
    [
        ({"PubliclyAccessible": True}, "AWS_PRIVATE_REQUIRED"),
        ({"StorageEncrypted": False}, "AWS_ENCRYPTION_REQUIRED"),
        ({"EngineVersion": "17.6"}, "AWS_ENGINE_MISMATCH"),
        ({"VpcSecurityGroups": []}, "AWS_NETWORK_MISMATCH"),
        (
            {"DBInstanceArn": f"arn:aws:rds:{REGION}:999999999999:db:synthetic-source"},
            "AWS_RESOURCE_IDENTITY_MISMATCH",
        ),
    ],
)
def test_source_negative_before_tags(cloud, changes, code):
    cloud.identity()
    cloud.rds.add_response(
        "describe_db_instances",
        {"DBInstances": [cloud.instance(**changes)]},
        {"DBInstanceIdentifier": cloud.policy.source_instance_id},
    )
    with pytest.raises(PreflightError, match=code):
        cloud.adapter.inspect_source()


def test_creation_not_authorized_no_calls(cloud):
    cloud.adapter.policy = replace(cloud.policy, creation_authorized=False)
    with pytest.raises(PreflightError, match="CLOUD_CREATION_NOT_AUTHORIZED"):
        cloud.adapter.ensure_snapshot(cloud.intent)


def test_snapshot_create_exact_reconciled_once(cloud):
    cloud.source()
    cloud.absent_snapshot()
    cloud.identity()
    cloud.rds.add_response(
        "create_db_snapshot",
        {"DBSnapshot": cloud.snapshot(Status="creating")},
        {
            "DBInstanceIdentifier": cloud.policy.source_instance_id,
            "DBSnapshotIdentifier": cloud.intent.snapshot_id,
            "Tags": [{"Key": k, "Value": v} for k, v in cloud.intent.tags().items()],
        },
    )
    cloud.snap_read(Status="creating")
    assert cloud.adapter.ensure_snapshot(cloud.intent).status == "creating"
    cloud.source()
    cloud.snap_read()
    assert cloud.adapter.ensure_snapshot(cloud.intent).status == "available"


def test_restore_private_exact_args_then_restart_reconciles(cloud):
    cloud.snap_read()
    cloud.source()
    cloud.absent_clone()
    cloud.identity()
    tags = cloud.intent.tags() | {"SnapshotId": cloud.intent.snapshot_id}
    expected = {
        "DBInstanceIdentifier": cloud.intent.clone_instance_id,
        "DBSnapshotIdentifier": cloud.intent.snapshot_id,
        "DBInstanceClass": cloud.policy.instance_class,
        "DBSubnetGroupName": cloud.policy.subnet_group,
        "VpcSecurityGroupIds": list(cloud.policy.security_group_ids),
        "PubliclyAccessible": False,
        "DeletionProtection": False,
        "MultiAZ": False,
        "AutoMinorVersionUpgrade": False,
        "CopyTagsToSnapshot": True,
        "Tags": [{"Key": k, "Value": v} for k, v in tags.items()],
    }
    cloud.rds.add_response(
        "restore_db_instance_from_db_snapshot",
        {"DBInstance": cloud.instance(True, DBInstanceStatus="creating")},
        expected,
    )
    cloud.clone_read(DBInstanceStatus="creating")
    assert cloud.adapter.ensure_clone(cloud.intent).status == "creating"
    cloud.snap_read()
    cloud.source()
    cloud.clone_read()
    assert cloud.adapter.ensure_clone(cloud.intent).status == "available"


def test_provider_message_sanitized(cloud):
    cloud.identity()
    cloud.rds.add_client_error(
        "describe_db_instances",
        "AccessDenied",
        "secret-password-raw-row",
        expected_params={"DBInstanceIdentifier": cloud.policy.source_instance_id},
    )
    with pytest.raises(PreflightError) as caught:
        cloud.adapter.inspect_source()
    assert str(caught.value) == "AWS_REQUEST_DENIED"


def test_snapshot_collision_wrong_owner_blocks(cloud):
    cloud.identity()
    value = cloud.snapshot()
    cloud.rds.add_response(
        "describe_db_snapshots",
        {"DBSnapshots": [value]},
        {"DBSnapshotIdentifier": cloud.intent.snapshot_id},
    )
    cloud.tags(value["DBSnapshotArn"], cloud.intent.tags() | {"Owner": "other"})
    with pytest.raises(PreflightError, match="AWS_RESOURCE_TAG_MISMATCH"):
        cloud.adapter.inspect_snapshot(cloud.intent)


@pytest.mark.parametrize(
    "changes,code",
    [
        ({"literal_gate_approved": False}, "CLEANUP_APPROVAL_REQUIRED"),
        ({"reports_retained": False}, "CLEANUP_REPORT_RETENTION_REQUIRED"),
        ({"run_phase": "APPLYING"}, "CLEANUP_MUTATION_STATE_BLOCKED"),
        ({"run_phase": "APPLY_OUTCOME_UNKNOWN"}, "CLEANUP_MUTATION_STATE_BLOCKED"),
        ({"run_phase": "CLONE_OUTCOME_UNKNOWN"}, "CLEANUP_MUTATION_STATE_BLOCKED"),
        ({"run_phase": "MIGRATING"}, "CLEANUP_MUTATION_STATE_BLOCKED"),
        ({"dependent_operation_active": True}, "CLEANUP_MUTATION_STATE_BLOCKED"),
        ({"clone_instance_id": "synthetic-source"}, "CLEANUP_RESOURCE_MISMATCH"),
        ({"snapshot_id": "unrelated-snapshot"}, "CLEANUP_RESOURCE_MISMATCH"),
        ({"clone_instance_id": None}, "CLEANUP_EXACT_SELECTION_REQUIRED"),
    ],
)
def test_cleanup_static_refusals_no_aws(cloud, changes, code):
    selection = replace(cleanup(cloud), **changes)
    with pytest.raises(PreflightError, match=code):
        cloud.adapter.cleanup(cloud.intent, selection)


def test_delete_exact_clone_then_observe_absence(cloud):
    cloud.source()
    cloud.clone_read()
    cloud.identity()
    cloud.rds.add_response(
        "delete_db_instance",
        {"DBInstance": cloud.instance(True, DBInstanceStatus="deleting")},
        {
            "DBInstanceIdentifier": cloud.intent.clone_instance_id,
            "SkipFinalSnapshot": True,
            "DeleteAutomatedBackups": True,
        },
    )
    assert cloud.adapter.cleanup(cloud.intent, cleanup(cloud)) == {"clone": "DELETING"}
    cloud.source()
    cloud.absent_clone()
    assert cloud.adapter.cleanup(cloud.intent, cleanup(cloud)) == {"clone": "ABSENT"}


def test_preflight_all_selections_before_any_delete(cloud):
    cloud.source()
    cloud.clone_read()
    cloud.snap_read(Status="creating")
    with pytest.raises(PreflightError, match="CLEANUP_RESOURCE_BUSY"):
        cloud.adapter.cleanup(
            cloud.intent, cleanup(cloud, delete_snapshot=True, snapshot_id=cloud.intent.snapshot_id)
        )


def test_source_apply_attempt_retains_backup_without_independent_attestation(cloud):
    cloud.source()
    selection = CleanupPolicy(
        True,
        "APPLIED",
        True,
        source_apply_attempted=True,
        delete_snapshot=True,
        snapshot_id=cloud.intent.snapshot_id,
        recovery_backup_snapshot_id="independent-backup",
        preapply_not_after=NOW,
    )
    with pytest.raises(PreflightError, match="RECOVERY_BACKUP_INVALID"):
        cloud.adapter.cleanup(cloud.intent, selection)


def test_verified_preapply_independent_backup(cloud):
    cloud.adapter.recovery_attestation = lambda identifier, source, before: (
        identifier == "independent-backup"
        and source == cloud.policy.source_instance_id
        and before == NOW
    )
    cloud.identity()
    value = cloud.snapshot("independent-backup")
    cloud.rds.add_response(
        "describe_db_snapshots",
        {"DBSnapshots": [value]},
        {"DBSnapshotIdentifier": "independent-backup"},
    )
    cloud.tags(value["DBSnapshotArn"], {"Project": "Preflight", "Owner": cloud.policy.owner})
    assert (
        cloud.adapter.verify_recovery_snapshot(
            "independent-backup", cloud.policy.source_instance_id, NOW
        ).status
        == "available"
    )
