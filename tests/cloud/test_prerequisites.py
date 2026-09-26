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
    prefix = f"arn:aws:rds:{REGION}:{ACCOUNT}:"
    source = prefix + "db:synthetic-source"
    clone = prefix + "db:preflight-*-clone"
    snapshot = prefix + "snapshot:preflight-*-snap"
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "rds:CreateDBSnapshot",
                "Resource": [source, snapshot],
            },
            {
                "Effect": "Allow",
                "Action": "rds:RestoreDBInstanceFromDBSnapshot",
                "Resource": [
                    clone,
                    snapshot,
                    prefix + "subgrp:private-subnets",
                    prefix + "og:default:postgres-18",
                    prefix + "pg:default.postgres18",
                ],
            },
            {
                "Effect": "Allow",
                "Action": "rds:ListTagsForResource",
                "Resource": [source, clone, snapshot],
            },
            {
                "Effect": "Allow",
                "Action": "rds:AddTagsToResource",
                "Resource": [clone, snapshot],
            },
            {
                "Effect": "Allow",
                "Action": "secretsmanager:GetSecretValue",
                "Resource": [
                    f"arn:aws:secretsmanager:{REGION}:{ACCOUNT}:secret:read-unit",
                    f"arn:aws:secretsmanager:{REGION}:{ACCOUNT}:secret:writer-unit",
                ],
            },
            {"Effect": "Allow", "Action": "sts:GetCallerIdentity", "Resource": "*"},
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
                "Resource": f"arn:aws:rds:{REGION}:{ACCOUNT}:db:preflight-*-clone",
                "Condition": {
                    "StringEquals": {
                        "aws:ResourceTag/Project": "Preflight",
                        "aws:ResourceTag/Owner": "unit-owner",
                    },
                    "Null": {"aws:ResourceTag/RunId": "false"},
                },
            },
        ],
    }


@pytest.mark.parametrize("mutation", ["missing", "wrong_owner", "if_exists", "missing_run_id"])
def test_runtime_delete_requires_unconditional_owner_and_run_tag_guards(driver, mutation):
    value, _ = driver
    policy = document()
    deletion = next(s for s in policy["Statement"] if s["Action"] == "rds:DeleteDBInstance")
    if mutation == "missing":
        deletion.pop("Condition")
    elif mutation == "wrong_owner":
        deletion["Condition"]["StringEquals"]["aws:ResourceTag/Owner"] = "another-owner"
    elif mutation == "if_exists":
        deletion["Condition"]["StringEqualsIfExists"] = deletion["Condition"].pop("StringEquals")
    else:
        deletion["Condition"].pop("Null")
    with pytest.raises(bootstrap.PlanError, match="BOOTSTRAP_RUNTIME_DELETE_TAG_GUARDS_REQUIRED"):
        guards.validate_runtime_documents([policy], value.inputs, value.deployment)


def test_runtime_source_prefix_collision_cannot_allow_source_delete(driver):
    value, _ = driver
    value.inputs["source_instance_id"] = "preflight-demo-source"
    policy = document()
    deletion = next(s for s in policy["Statement"] if s["Action"] == "rds:DeleteDBInstance")
    deletion["Resource"] = f"arn:aws:rds:{REGION}:{ACCOUNT}:db:preflight-*"
    with pytest.raises(bootstrap.PlanError, match="BOOTSTRAP_RUNTIME_POLICY_TARGET_TOO_BROAD"):
        guards.validate_runtime_documents([policy], value.inputs, value.deployment)


def test_runtime_policy_missing_restore_permissions_refused(driver):
    value, _ = driver
    policy = document()
    policy["Statement"] = [
        s for s in policy["Statement"] if s["Action"] != "rds:RestoreDBInstanceFromDBSnapshot"
    ]
    with pytest.raises(bootstrap.PlanError, match="BOOTSTRAP_RUNTIME_REQUIRED_PERMISSIONS_MISSING"):
        guards.validate_runtime_documents([policy], value.inputs, value.deployment)


@pytest.mark.parametrize("resource_type", ["subgrp", "og", "pg"])
def test_runtime_restore_requires_all_approved_dependency_resources(driver, resource_type):
    value, _ = driver
    policy = document()
    statement = next(
        s for s in policy["Statement"] if s["Action"] == "rds:RestoreDBInstanceFromDBSnapshot"
    )
    statement["Resource"] = [
        resource for resource in statement["Resource"] if f":{resource_type}:" not in resource
    ]
    with pytest.raises(bootstrap.PlanError, match="BOOTSTRAP_RUNTIME_REQUIRED_PERMISSIONS_MISSING"):
        guards.validate_runtime_documents([policy], value.inputs, value.deployment)


def test_runtime_restore_accepts_exact_approved_subnet_and_builtin_pg18_groups(driver):
    value, _ = driver
    guards.validate_runtime_documents([document()], value.inputs, value.deployment)


@pytest.mark.parametrize(
    "resource",
    [
        f"arn:aws:rds:{REGION}:{ACCOUNT}:subgrp:*",
        f"arn:aws:rds:{REGION}:{ACCOUNT}:subgrp:other-private-subnets",
        f"arn:aws:rds:{REGION}:{ACCOUNT}:og:*",
        f"arn:aws:rds:{REGION}:{ACCOUNT}:pg:*",
        f"arn:aws:rds:{REGION}:{ACCOUNT}:pg:default.postgres17",
        f"arn:aws:rds:{REGION}:{ACCOUNT}:og:custom-group",
        f"arn:aws:rds:{REGION}:999999999999:subgrp:private-subnets",
        f"arn:aws:rds:us-west-2:{ACCOUNT}:pg:default.postgres18",
    ],
)
def test_runtime_restore_cannot_admit_other_or_wildcard_group_resources(driver, resource):
    value, _ = driver
    policy = document()
    statement = next(
        s for s in policy["Statement"] if s["Action"] == "rds:RestoreDBInstanceFromDBSnapshot"
    )
    statement["Resource"].append(resource)
    with pytest.raises(bootstrap.PlanError, match="BOOTSTRAP_RUNTIME_POLICY_TARGET_TOO_BROAD"):
        guards.validate_runtime_documents([policy], value.inputs, value.deployment)


@pytest.mark.parametrize(
    "action", ["rds:AddTagsToResource", "rds:ListTagsForResource", "rds:DeleteDBInstance"]
)
def test_restore_group_scopes_do_not_expand_other_actions(driver, action):
    value, _ = driver
    policy = document()
    policy["Statement"].append(
        {
            "Effect": "Allow",
            "Action": action,
            "Resource": f"arn:aws:rds:{REGION}:{ACCOUNT}:subgrp:private-subnets",
        }
    )
    with pytest.raises(bootstrap.PlanError):
        guards.validate_runtime_documents([policy], value.inputs, value.deployment)


@pytest.mark.parametrize(
    "field,value",
    [
        ("subnet_group", "*"),
        ("subnet_group", "private-*"),
        ("engine_version", "17.6"),
        ("engine_version", "18*"),
    ],
)
def test_runtime_restore_group_inputs_cannot_invent_scope(driver, field, value):
    harness, _ = driver
    target = harness.inputs if field == "subnet_group" else harness.deployment
    target[field] = value
    with pytest.raises(bootstrap.PlanError, match="BOOTSTRAP_RUNTIME_RESTORE_GROUP_SCOPE_INVALID"):
        guards.validate_runtime_documents([document()], harness.inputs, harness.deployment)


def test_production_restore_template_supplies_only_exact_restore_dependencies(driver):
    from string import Template

    value, _ = driver
    raw = (Path(__file__).parents[2] / "infra/runtime-policy.template.json").read_text()
    rendered = json.loads(
        Template(raw).substitute(
            REGION=value.inputs["region"],
            ACCOUNT_ID=value.inputs["account_id"],
            DB_SUBNET_GROUP=value.inputs["subnet_group"],
        )
    )
    # This is the restore-only addendum, combined with the existing scoped
    # runtime permissions. It grants no source modification or new action.
    assert len(rendered["Statement"]) == 1
    statement = rendered["Statement"][0]
    assert statement["Action"] == "rds:RestoreDBInstanceFromDBSnapshot"
    assert len(statement["Resource"]) == 5
    assert all(":db:synthetic-source" not in resource for resource in statement["Resource"])
    existing = document()
    existing["Statement"] = [
        s for s in existing["Statement"] if s["Action"] != "rds:RestoreDBInstanceFromDBSnapshot"
    ]
    guards.validate_runtime_documents([existing, rendered], value.inputs, value.deployment)
    with pytest.raises(bootstrap.PlanError, match="BOOTSTRAP_RUNTIME_REQUIRED_PERMISSIONS_MISSING"):
        guards.validate_runtime_documents([rendered], value.inputs, value.deployment)


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
                    "RootDeviceType": "ebs",
                    "RootDeviceName": "/dev/sda1",
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


@pytest.mark.parametrize(
    "condition",
    [
        False,
        [],
        {"StringEquals": []},
        {"UnknownOperator": {}},
        {"StringEquals": {"aws:RequestedRegion": "us-west-2"}},
    ],
)
def test_runtime_unmodeled_or_malformed_grant_conditions_fail_closed(driver, condition):
    value, _ = driver
    policy = document()
    policy["Statement"][1]["Condition"] = condition
    with pytest.raises(bootstrap.PlanError):
        guards.validate_runtime_documents([policy], value.inputs, value.deployment)


def test_runtime_malformed_run_tag_is_safe_error(driver):
    value, _ = driver
    policy = document()
    policy["Statement"][-1]["Condition"]["Null"]["aws:ResourceTag/RunId"] = ["false"]
    with pytest.raises(bootstrap.PlanError):
        guards.validate_runtime_documents([policy], value.inputs, value.deployment)


def test_conditional_delete_statement_cannot_supply_required_restore_grant(driver):
    value, _ = driver
    policy = document()
    policy["Statement"][1]["Resource"] = [policy["Statement"][1]["Resource"][1]]
    policy["Statement"][-1]["Action"] = [
        "rds:DeleteDBInstance",
        "rds:RestoreDBInstanceFromDBSnapshot",
    ]
    with pytest.raises(bootstrap.PlanError, match="BOOTSTRAP_RUNTIME_POLICY_CONDITION_UNSUPPORTED"):
        guards.validate_runtime_documents([policy], value.inputs, value.deployment)
