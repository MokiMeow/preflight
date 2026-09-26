import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import boto3
import pytest
from botocore.stub import Stubber

INFRA = Path(__file__).parents[2] / "infra"
spec = importlib.util.spec_from_file_location("bootstrap", INFRA / "bootstrap.py")
bootstrap = importlib.util.module_from_spec(spec)
sys.modules["bootstrap"] = bootstrap
spec.loader.exec_module(bootstrap)
spec = importlib.util.spec_from_file_location("cloud_bootstrap", INFRA / "cloud_bootstrap.py")
driver_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver_module)

ACCOUNT = "123456789012"
REGION = "us-east-1"


@pytest.fixture
def driver(tmp_path):
    inputs = {
        "account_id": ACCOUNT,
        "region": REGION,
        "operator_label": "unit-owner",
        "source_instance_id": "synthetic-source",
        "source_mode": "create",
        "host_mode": "create",
        "instance_class": "db.t4g.micro",
        "allocated_storage_gib": 20,
        "host_instance_type": "t3.medium",
        "subnet_group": "private-subnets",
        "security_group_ids": ["sg-0123456789abcdef0"],
        "max_clones": 1,
        "max_snapshots": 3,
        "approved_spend_ceiling": 10,
        "currency": "USD",
        "retention_owner": "unit-owner",
        "ssh_cidr": "192.0.2.1/32",
        "deployment": {
            "database_name": "synthetic",
            "host_instance_id": "",
            "host_subnet_id": "subnet-0123",
            "host_security_group_ids": ["sg-abcdef01234567890"],
            "host_image_id": "ami-0123",
            "host_image_owner": ACCOUNT,
            "instance_profile_name": "preflight-runtime",
            "instance_profile_arn": f"arn:aws:iam::{ACCOUNT}:instance-profile/preflight-runtime",
            "ssh_key_name": "unit-key",
            "kms_key_arn": "",
            "read_secret_arn": f"arn:aws:secretsmanager:{REGION}:{ACCOUNT}:secret:read-unit",
            "writer_secret_arn": f"arn:aws:secretsmanager:{REGION}:{ACCOUNT}:secret:writer-unit",
            "engine_version": "18.1",
            "runtime_role_policy_sha256": "0" * 64,
        },
    }
    plan = bootstrap.make_plan(inputs)
    approval = {
        "plan_sha256": plan["plan_sha256"],
        "account_id": ACCOUNT,
        "region": REGION,
        "operator_label": "unit-owner",
        "approved_spend_ceiling": 10,
        "creation_authorized": True,
    }
    session = boto3.Session(
        aws_access_key_id="unit-fixture", aws_secret_access_key="unit-fixture", region_name=REGION
    )
    clients = {
        name: session.client(name) for name in ("rds", "ec2", "sts", "iam", "secretsmanager")
    }
    stubs = {name: Stubber(client) for name, client in clients.items()}
    for stub in stubs.values():
        stub.activate()
    result = driver_module.BootstrapDriver(plan, approval, clients, str(tmp_path))
    yield result, stubs
    for stub in stubs.values():
        stub.assert_no_pending_responses()
        stub.deactivate()


def identity(stubs):
    stubs["sts"].add_response(
        "get_caller_identity",
        {"Account": ACCOUNT, "Arn": f"arn:aws:iam::{ACCOUNT}:user/unit", "UserId": "unit"},
        {},
    )


def test_source_create_explicit_encrypted_private_managed_master_no_reset(driver):
    value, stubs = driver
    rds = stubs["rds"]
    source_id = value.inputs["source_instance_id"]
    rds.add_client_error(
        "describe_db_instances",
        "DBInstanceNotFound",
        expected_params={"DBInstanceIdentifier": source_id},
    )
    rds.add_response(
        "describe_db_engine_versions",
        {
            "DBEngineVersions": [
                {"Engine": "postgres", "EngineVersion": "18.1", "Status": "available"}
            ]
        },
        {"Engine": "postgres", "EngineVersion": "18.1"},
    )
    rds.add_response(
        "describe_orderable_db_instance_options",
        {"OrderableDBInstanceOptions": [{"StorageType": "gp3", "SupportsStorageEncryption": True}]},
        {
            "Engine": "postgres",
            "EngineVersion": "18.1",
            "DBInstanceClass": "db.t4g.micro",
            "Vpc": True,
        },
    )
    identity(stubs)
    expected = {
        "DBInstanceIdentifier": source_id,
        "DBName": "synthetic",
        "Engine": "postgres",
        "EngineVersion": "18.1",
        "DBInstanceClass": "db.t4g.micro",
        "AllocatedStorage": 20,
        "StorageType": "gp3",
        "StorageEncrypted": True,
        "PubliclyAccessible": False,
        "DBSubnetGroupName": "private-subnets",
        "VpcSecurityGroupIds": ["sg-0123456789abcdef0"],
        "MasterUsername": "preflight_bootstrap",
        "ManageMasterUserPassword": True,
        "BackupRetentionPeriod": 7,
        "DeletionProtection": True,
        "MultiAZ": False,
        "AutoMinorVersionUpgrade": False,
        "CopyTagsToSnapshot": True,
        "Tags": value.tags(True),
    }
    rds.add_response("create_db_instance", {}, expected)
    source = {
        "DBInstanceIdentifier": source_id,
        "DBInstanceArn": f"arn:aws:rds:{REGION}:{ACCOUNT}:db:{source_id}",
        "Engine": "postgres",
        "EngineVersion": "18.1",
        "DBName": "synthetic",
        "DBInstanceClass": "db.t4g.micro",
        "PubliclyAccessible": False,
        "StorageEncrypted": True,
        "StorageType": "gp3",
        "DBInstanceStatus": "creating",
        "AllocatedStorage": 20,
        "DBSubnetGroup": {"DBSubnetGroupName": "private-subnets"},
        "VpcSecurityGroups": [{"VpcSecurityGroupId": "sg-0123456789abcdef0"}],
    }
    for _ in range(2):
        rds.add_response(
            "describe_db_instances", {"DBInstances": [source]}, {"DBInstanceIdentifier": source_id}
        )
        rds.add_response(
            "list_tags_for_resource",
            {"TagList": value.tags(True)},
            {"ResourceName": source["DBInstanceArn"]},
        )
    assert value.source() == (source_id, "creating")
    assert value.source() == (source_id, "creating")  # restart reconciles, no second create


@pytest.mark.parametrize("mutation", ["valid", "wrong_image", "wrong_root", "oversize_disk"])
def test_host_create_single_token_imds_and_encrypted_persistent_disk(driver, mutation):
    value, stubs = driver
    ec2 = stubs["ec2"]
    filters = {"Filters": [{"Name": "client-token", "Values": [value.digest]}]}
    ec2.add_response("describe_instances", {"Reservations": []}, filters)
    ec2.add_response(
        "describe_images",
        {
            "Images": [
                {
                    "ImageId": value.deployment["host_image_id"],
                    "OwnerId": ACCOUNT,
                    "State": "available",
                    "Architecture": "x86_64",
                    "RootDeviceType": "ebs",
                    "RootDeviceName": "/dev/sda1",
                }
            ]
        },
        {"ImageIds": [value.deployment["host_image_id"]]},
    )
    identity(stubs)
    d = value.deployment
    expected = {
        "ImageId": d["host_image_id"],
        "InstanceType": "t3.medium",
        "MinCount": 1,
        "MaxCount": 1,
        "ClientToken": value.digest,
        "SubnetId": d["host_subnet_id"],
        "SecurityGroupIds": d["host_security_group_ids"],
        "KeyName": d["ssh_key_name"],
        "IamInstanceProfile": {"Arn": d["instance_profile_arn"]},
        "MetadataOptions": {"HttpTokens": "required", "HttpEndpoint": "enabled"},
        "BlockDeviceMappings": [
            {
                "DeviceName": "/dev/sda1",
                "Ebs": {
                    "Encrypted": True,
                    "VolumeType": "gp3",
                    "VolumeSize": 30,
                    "DeleteOnTermination": False,
                },
            }
        ],
        "TagSpecifications": [
            {"ResourceType": "instance", "Tags": value.tags()},
            {"ResourceType": "volume", "Tags": value.tags()},
        ],
    }
    ec2.add_response("run_instances", {}, expected)
    host = {
        "InstanceId": "i-0123",
        "ImageId": "ami-wrong" if mutation == "wrong_image" else d["host_image_id"],
        "ClientToken": value.digest,
        "SubnetId": d["host_subnet_id"],
        "IamInstanceProfile": {"Arn": d["instance_profile_arn"]},
        "SecurityGroups": [{"GroupId": s} for s in d["host_security_group_ids"]],
        "InstanceType": "t3.medium",
        "MetadataOptions": {"HttpTokens": "required"},
        "Tags": value.tags(),
        "State": {"Name": "pending"},
        "RootDeviceType": "ebs",
        "RootDeviceName": "/dev/wrong" if mutation == "wrong_root" else "/dev/sda1",
        "BlockDeviceMappings": [
            {
                "DeviceName": "/dev/sda1",
                "Ebs": {
                    "VolumeId": "vol-0123",
                    "DeleteOnTermination": False,
                },
            }
        ],
    }
    for _ in range(2 if mutation == "valid" else 1):
        ec2.add_response("describe_instances", {"Reservations": [{"Instances": [host]}]}, filters)
        if mutation in {"wrong_image", "wrong_root"}:
            continue
        ec2.add_response(
            "describe_volumes",
            {
                "Volumes": [
                    {
                        "VolumeId": "vol-0123",
                        "Encrypted": True,
                        "VolumeType": "gp3",
                        "Size": 300 if mutation == "oversize_disk" else 30,
                        "Attachments": [{"InstanceId": "i-0123"}],
                    }
                ]
            },
            {"VolumeIds": ["vol-0123"]},
        )
    if mutation == "valid":
        assert value.host() == ("i-0123", "pending")
        assert value.host() == ("i-0123", "pending")
    else:
        with pytest.raises(bootstrap.PlanError):
            value.host()


def test_missing_scope_does_not_construct_clients(tmp_path):
    with pytest.raises(bootstrap.PlanError, match="PLAN_ENVELOPE_INVALID"):
        driver_module.execute_bootstrap({}, {}, str(tmp_path))


def test_wrong_account_no_mutations(driver):
    value, stubs = driver
    stubs["sts"].add_response("get_caller_identity", {"Account": "999999999999"}, {})
    with pytest.raises(bootstrap.PlanError, match="BOOTSTRAP_ACCOUNT_MISMATCH"):
        value.run()


def test_runtime_admin_policy_refused(driver):
    value, stubs = driver
    iam = stubs["iam"]
    from datetime import UTC, datetime

    iam.add_response(
        "get_instance_profile",
        {
            "InstanceProfile": {
                "Path": "/",
                "InstanceProfileName": "preflight-runtime",
                "InstanceProfileId": "unit-fixture-id-1234",
                "Arn": value.deployment["instance_profile_arn"],
                "CreateDate": datetime(2026, 1, 1, tzinfo=UTC),
                "Roles": [
                    {
                        "Path": "/",
                        "RoleName": "unit-role",
                        "RoleId": "unit-fixture-id-1234",
                        "Arn": f"arn:aws:iam::{ACCOUNT}:role/unit-role",
                        "CreateDate": datetime(2026, 1, 1, tzinfo=UTC),
                    }
                ],
            }
        },
        {"InstanceProfileName": "preflight-runtime"},
    )
    iam.add_response("list_role_policies", {"PolicyNames": ["admin"]}, {"RoleName": "unit-role"})
    iam.add_response(
        "list_attached_role_policies", {"AttachedPolicies": []}, {"RoleName": "unit-role"}
    )
    # IAM serializes policy docs as URL-encoded strings; boto clients decode on read.
    document = {
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow", "Action": "*", "Resource": "*"}],
    }
    iam.add_response(
        "get_role_policy",
        {"RoleName": "unit-role", "PolicyName": "admin", "PolicyDocument": json.dumps(document)},
        {"RoleName": "unit-role", "PolicyName": "admin"},
    )
    value.deployment["runtime_role_policy_sha256"] = hashlib.sha256(
        json.dumps([document], sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    with pytest.raises(bootstrap.PlanError, match="BOOTSTRAP_RUNTIME_POLICY_TOO_BROAD"):
        value.validate_prerequisites()


@pytest.mark.parametrize("allocated", [None, 1000, 20])
def test_observed_source_storage_must_match_approved_plan(driver, allocated):
    value, stubs = driver
    value.inputs["source_mode"] = "reuse"
    source_id = value.inputs["source_instance_id"]
    source = {
        "DBInstanceIdentifier": source_id,
        "DBInstanceArn": f"arn:aws:rds:{REGION}:{ACCOUNT}:db:{source_id}",
        "Engine": "postgres",
        "EngineVersion": "18.1",
        "DBName": "synthetic",
        "DBInstanceClass": "db.t4g.micro",
        "PubliclyAccessible": False,
        "StorageEncrypted": True,
        "StorageType": "gp3",
        "DBInstanceStatus": "available",
        "DBSubnetGroup": {"DBSubnetGroupName": "private-subnets"},
        "VpcSecurityGroups": [{"VpcSecurityGroupId": "sg-0123456789abcdef0"}],
    }
    if allocated is not None:
        source["AllocatedStorage"] = allocated
    stubs["rds"].add_response(
        "describe_db_instances", {"DBInstances": [source]}, {"DBInstanceIdentifier": source_id}
    )
    stubs["rds"].add_response(
        "list_tags_for_resource",
        {"TagList": value.tags(True)},
        {"ResourceName": source["DBInstanceArn"]},
    )
    if allocated == 20:
        assert value.source() == (source_id, "available")
    else:
        with pytest.raises(bootstrap.PlanError, match="BOOTSTRAP_SOURCE_POLICY_MISMATCH"):
            value.source()


@pytest.mark.parametrize(
    "mutation",
    [
        "wrong_host",
        "missing_mapping",
        "ephemeral_root",
        "delete_on_termination",
        "unencrypted",
        "wrong_volume",
        "unattached",
        "wrong_storage",
        "valid",
    ],
)
def test_host_reuse_requires_exact_identity_and_observed_private_persistent_storage(
    driver, mutation
):
    value, stubs = driver
    value.inputs["host_mode"] = "reuse"
    value.deployment["host_instance_id"] = "i-approved"
    d = value.deployment
    host = {
        "InstanceId": "i-approved",
        "SubnetId": d["host_subnet_id"],
        "IamInstanceProfile": {"Arn": d["instance_profile_arn"]},
        "SecurityGroups": [{"GroupId": s} for s in d["host_security_group_ids"]],
        "InstanceType": "t3.medium",
        "MetadataOptions": {"HttpTokens": "required"},
        "Tags": value.tags(),
        "State": {"Name": "running"},
        "RootDeviceType": "ebs",
        "RootDeviceName": "/dev/sda1",
        "BlockDeviceMappings": [
            {
                "DeviceName": "/dev/sda1",
                "Ebs": {
                    "VolumeId": "vol-approved",
                    "DeleteOnTermination": False,
                },
            }
        ],
    }
    if mutation == "wrong_host":
        host["InstanceId"] = "i-different"
    elif mutation == "missing_mapping":
        host.pop("BlockDeviceMappings")
    elif mutation == "ephemeral_root":
        host["RootDeviceType"] = "instance-store"
    elif mutation == "delete_on_termination":
        host["BlockDeviceMappings"][0]["Ebs"]["DeleteOnTermination"] = True
    stubs["ec2"].add_response(
        "describe_instances",
        {"Reservations": [{"Instances": [host]}]},
        {"InstanceIds": ["i-approved"]},
    )
    if mutation in {"unencrypted", "wrong_volume", "unattached", "wrong_storage", "valid"}:
        volume = {
            "VolumeId": "vol-different" if mutation == "wrong_volume" else "vol-approved",
            "Encrypted": mutation != "unencrypted",
            "VolumeType": "gp2" if mutation == "wrong_storage" else "gp3",
            "Attachments": [] if mutation == "unattached" else [{"InstanceId": "i-approved"}],
        }
        stubs["ec2"].add_response(
            "describe_volumes", {"Volumes": [volume]}, {"VolumeIds": ["vol-approved"]}
        )
    if mutation == "valid":
        assert value.host() == ("i-approved", "running")
    else:
        with pytest.raises(bootstrap.PlanError):
            value.host()
