import hashlib
import importlib.util
import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.cloud.test_bootstrap_driver import ACCOUNT, REGION, bootstrap
from tests.cloud.test_bootstrap_driver import driver as driver_fixture

spec = importlib.util.spec_from_file_location(
    "prerequisites", Path(__file__).parents[2] / "infra/prerequisites.py"
)
guards = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guards)
driver = driver_fixture


def groups(value):
    return [
        {
            "GroupId": value.inputs["security_group_ids"][0],
            "VpcId": "vpc-0123",
            "IpPermissions": [
                {
                    "IpProtocol": "tcp",
                    "FromPort": 5432,
                    "ToPort": 5432,
                    "UserIdGroupPairs": [
                        {
                            "GroupId": value.deployment["host_security_group_ids"][0],
                            "UserId": ACCOUNT,
                        }
                    ],
                }
            ],
            "IpPermissionsEgress": [],
        },
        {
            "GroupId": value.deployment["host_security_group_ids"][0],
            "VpcId": "vpc-0123",
            "IpPermissions": [
                {
                    "IpProtocol": "tcp",
                    "FromPort": 22,
                    "ToPort": 22,
                    "IpRanges": [{"CidrIp": value.inputs["ssh_cidr"]}],
                }
            ],
        },
    ]


def document():
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "rds:DescribeDBInstances",
                    "rds:DescribeDBSnapshots",
                    "tag:GetResources",
                ],
                "Resource": "*",
            },
            {
                "Effect": "Allow",
                "Action": "rds:DeleteDBInstance",
                "Resource": f"arn:aws:rds:{REGION}:{ACCOUNT}:db:preflight-*",
            },
        ],
    }


def stub_prerequisites(value, stubs, selected_groups):
    role = {
        "Path": "/",
        "RoleName": "unit-role",
        "RoleId": "unit-fixture-id-1234",
        "Arn": f"arn:aws:iam::{ACCOUNT}:role/unit-role",
        "CreateDate": datetime(2026, 1, 1, tzinfo=UTC),
        "AssumeRolePolicyDocument": json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": "sts:AssumeRole",
                        "Principal": {"Service": "ec2.amazonaws.com"},
                    }
                ],
            }
        ),
    }
    stubs["iam"].add_response(
        "get_instance_profile",
        {
            "InstanceProfile": {
                "Path": "/",
                "InstanceProfileName": "preflight-runtime",
                "InstanceProfileId": "unit-fixture-id-1234",
                "Arn": value.deployment["instance_profile_arn"],
                "CreateDate": datetime(2026, 1, 1, tzinfo=UTC),
                "Roles": [role],
            }
        },
        {"InstanceProfileName": "preflight-runtime"},
    )
    stubs["iam"].add_response(
        "list_role_policies", {"PolicyNames": ["runtime"]}, {"RoleName": "unit-role"}
    )
    stubs["iam"].add_response(
        "list_attached_role_policies", {"AttachedPolicies": []}, {"RoleName": "unit-role"}
    )
    stubs["iam"].add_response(
        "get_role_policy",
        {
            "RoleName": "unit-role",
            "PolicyName": "runtime",
            "PolicyDocument": json.dumps(document()),
        },
        {"RoleName": "unit-role", "PolicyName": "runtime"},
    )
    value.deployment["runtime_role_policy_sha256"] = hashlib.sha256(
        json.dumps([document()], sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    for key in ("read_secret_arn", "writer_secret_arn"):
        stubs["secretsmanager"].add_response(
            "describe_secret", {"ARN": value.deployment[key]}, {"SecretId": value.deployment[key]}
        )
    stubs["rds"].add_response(
        "describe_db_subnet_groups",
        {
            "DBSubnetGroups": [
                {
                    "DBSubnetGroupName": "private-subnets",
                    "SubnetGroupStatus": "Complete",
                    "VpcId": "vpc-0123",
                    "Subnets": [
                        {
                            "SubnetIdentifier": "subnet-db-a",
                            "SubnetAvailabilityZone": {"Name": "us-east-1a"},
                        },
                        {
                            "SubnetIdentifier": "subnet-db-b",
                            "SubnetAvailabilityZone": {"Name": "us-east-1b"},
                        },
                    ],
                }
            ]
        },
        {"DBSubnetGroupName": "private-subnets"},
    )
    stubs["ec2"].add_response(
        "describe_subnets",
        {"Subnets": [{"SubnetId": value.deployment["host_subnet_id"], "VpcId": "vpc-0123"}]},
        {"SubnetIds": [value.deployment["host_subnet_id"]]},
    )
    stubs["ec2"].add_response(
        "describe_security_groups",
        {"SecurityGroups": selected_groups},
        {
            "GroupIds": sorted(
                value.inputs["security_group_ids"] + value.deployment["host_security_group_ids"]
            )
        },
    )


@pytest.mark.parametrize("port", [8000, 8790])
def test_private_host_public_service_rule_refused_before_mutation(driver, port):
    value, stubs = driver
    selected_groups = groups(value)
    selected_groups[1]["IpPermissions"].append(
        {
            "IpProtocol": "tcp",
            "FromPort": port,
            "ToPort": port,
            "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
        }
    )
    stub_prerequisites(value, stubs, selected_groups)
    with pytest.raises(bootstrap.PlanError, match="BOOTSTRAP_PRIVATE_HOST_RULE_REQUIRED"):
        value.validate_prerequisites()


def test_private_host_and_db_prerequisite_reads_pass(driver):
    value, stubs = driver
    stub_prerequisites(value, stubs, groups(value))
    stubs["ec2"].add_response(
        "describe_images",
        {
            "Images": [
                {
                    "ImageId": value.deployment["host_image_id"],
                    "OwnerId": ACCOUNT,
                    "State": "available",
                    "Architecture": "x86_64",
                }
            ]
        },
        {"ImageIds": [value.deployment["host_image_id"]]},
    )
    value.validate_prerequisites()


@pytest.mark.parametrize(
    "change,code",
    [
        ("public_db", "BOOTSTRAP_PRIVATE_DB_RULE_REQUIRED"),
        ("db_egress", "BOOTSTRAP_DB_EGRESS_FORBIDDEN"),
        ("other_host", "BOOTSTRAP_PRIVATE_DB_RULE_REQUIRED"),
        ("other_vpc", "BOOTSTRAP_SECURITY_GROUP_MISMATCH"),
    ],
)
def test_network_exact_prerequisite_guards(driver, change, code):
    value, _ = driver
    selected_groups = groups(value)
    if change == "public_db":
        selected_groups[0]["IpPermissions"][0]["IpRanges"] = [{"CidrIp": "0.0.0.0/0"}]
    elif change == "db_egress":
        selected_groups[0]["IpPermissionsEgress"] = [
            {"IpProtocol": "-1", "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}
        ]
    elif change == "other_host":
        selected_groups[0]["IpPermissions"][0]["UserIdGroupPairs"][0]["GroupId"] = "sg-unknown"
    else:
        selected_groups[0]["VpcId"] = "vpc-unknown"
    with pytest.raises(bootstrap.PlanError, match=code):
        guards.validate_security_groups(selected_groups, value.inputs, value.deployment, "vpc-0123")


@pytest.mark.parametrize(
    "action,resource",
    [
        ("rds:DeleteDBInstance", "*"),
        ("rds:DeleteDBInstance", f"arn:aws:rds:{REGION}:{ACCOUNT}:db:synthetic-source"),
        ("rds:DeleteDBInstance", f"arn:aws:rds:{REGION}:999999999999:db:preflight-*"),
        ("secretsmanager:GetSecretValue", f"arn:aws:secretsmanager:{REGION}:{ACCOUNT}:secret:*"),
        ("kms:Decrypt", "*"),
        ("iam:PassRole", "*"),
    ],
)
def test_runtime_role_cannot_have_bootstrap_or_unrelated_targets(driver, action, resource):
    value, _ = driver
    policy = deepcopy(document())
    policy["Statement"].append({"Effect": "Allow", "Action": action, "Resource": resource})
    with pytest.raises(bootstrap.PlanError):
        guards.validate_runtime_documents([policy], value.inputs, value.deployment)


def test_runtime_role_trust_cannot_admit_external_principal():
    trust = {
        "Statement": [{"Effect": "Allow", "Action": "sts:AssumeRole", "Principal": {"AWS": "*"}}]
    }
    with pytest.raises(bootstrap.PlanError, match="BOOTSTRAP_RUNTIME_TRUST_TOO_BROAD"):
        guards.validate_role_trust(trust, f"arn:aws:iam::{ACCOUNT}:role/unit-role", ACCOUNT)
